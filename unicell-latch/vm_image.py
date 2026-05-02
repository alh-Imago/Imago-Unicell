"""
vm_image.py — Native VM Image

Serialises the entire running system to a single file and restores it.

What gets saved
===============

  Array cell maps     — gate states, input/output bus addresses for every
                        loaded region (the actual NOR gate configuration)
  Controller regions  — region names, cell address lists, run statistics
  Shore registry      — all Pond/tile/device registrations, connections,
                        extended address translations
  Companion state     — key registry, region allocations, escalation log
  SearchIndex state   — all SearchPonds with their entries (terms + paths)
  Ward states         — last known health state per Pond

What does NOT get saved
=======================

  Keyboard/network buffers — transient I/O, not meaningful to restore
  AI model weights         — too large; bridge is re-attached at boot
  Host file contents       — the native FS holds those; we just save paths
  In-flight bus packets    — the array is halted before save

Image format
============

The image is a single JSON file (or optionally gzip-compressed JSON).
JSON was chosen over pickle for portability and human-readability —
you can inspect or hand-edit a VM image with any text editor.

  {
    "version":     2,
    "saved_at":    1234567890.0,
    "system_id":   "shore_0",
    "array": {
      "cell_count":  5000,
      "regions": [ ... ]
    },
    "shore": { ... },
    "companion": { ... },
    "search_index": { ... }
  }

Usage
=====

    from vm_image import VMImage

    # Save
    img = VMImage(controller, shore, companion, search_index=idx)
    img.save("my_system.img")

    # Restore
    arr2, ctrl2, shore2, comp2, idx2 = VMImage.load("my_system.img",
                                                      cell_count=5000)
"""

from __future__ import annotations

import json
import gzip
import time
import os
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller    import ImagoController
    from shore_v2      import ShoreV2
    from companion     import Companion
    from fs_search     import SearchIndex

IMAGE_VERSION = 5   # v5: PTT bridge registration, BridgeLog, sentry cells, Claudette v1.3
GATE_STATE_BITS = 32   # current architecture
GATE_STATE_BITS_LEGACY = 11   # v1/v2 images


# ── VMImage ───────────────────────────────────────────────────────────────────

class VMImage:
    """
    Snapshot and restore a complete Imago system instance.

    Components captured:
      controller  — array cell maps and region metadata
      shore       — address book, connections, extended translations
      companion   — keys, regions, escalation log
      search_index — all SearchPonds with their term→file entries (optional)

    save(path)  — serialise to JSON (or .gz for compressed)
    load(path)  — class method; restores and returns live components
    """

    def __init__(self,
                 controller:   "ImagoController",
                 shore:        "ShoreV2",
                 companion:    "Companion",
                 search_index: Optional["SearchIndex"] = None,
                 pond_manager: Optional[object] = None):
        self._ctrl   = controller
        self._shore  = shore
        self._comp   = companion
        self._search = search_index
        self._ponds  = pond_manager

    # ── Save ─────────────────────────────────────────────────────────────────

    def save(self, path: str) -> dict:
        """
        Serialise the system to a file.

        path: destination file. Use .img or .img.gz.
              .gz suffix triggers gzip compression automatically.

        Returns the image dict (also written to file).
        """
        print(f"[VM_IMAGE] Saving system image to '{path}'...")
        t0 = time.time()

        image = {
            "version":        IMAGE_VERSION,
            "gate_state_bits": GATE_STATE_BITS,
            "os_name":         "Claudette",
            "os_version":      "1.3",
            "saved_at":  time.time(),
            "system_id": self._shore._shore_id
                         if hasattr(self._shore, '_shore_id') else "unknown",
            "array":     self._serialise_controller(),
            "shore":     self._serialise_shore(),
            "companion": self._serialise_companion(),
        }

        if self._search is not None:
            image["search_index"] = self._serialise_search()

        if self._ponds is not None:
            image["pond_manager"] = self._serialise_ponds()

        data = json.dumps(image, indent=2, default=str)

        if path.endswith('.gz'):
            with gzip.open(path, 'wt', encoding='utf-8') as f:
                f.write(data)
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data)

        size_kb = os.path.getsize(path) / 1024
        elapsed = time.time() - t0
        regions = len(image["array"]["regions"])
        entries = image["shore"]["registry_entries"]
        print(f"[VM_IMAGE] Saved: {size_kb:.1f} KB, "
              f"{regions} regions, {entries} Shore entries "
              f"in {elapsed:.3f}s")
        return image

    def _serialise_ponds(self) -> dict:
        """Capture PTT snapshots for all Ponds in the PondManager."""
        mgr = self._ponds
        ponds_out = {}
        pond_dict = getattr(mgr, '_ponds', {})
        for pond_id, pond in pond_dict.items():
            bridges_out = []
            for bridge in getattr(pond, 'bridges', []):
                bridges_out.append({
                    "role":             bridge.role,
                    "cell_addresses":   bridge.cell_addresses,
                    "lane_width":       bridge.lane_width,
                    "access_mask":      getattr(bridge, 'access_mask', 0xFFFFFFFF),
                    "packets_passed":   bridge.packets_passed,
                    "packets_rejected": bridge.packets_rejected,
                    "anomaly_count":    getattr(bridge, 'routing_anomaly_count', 0),
                })
            ptt_summary = None
            if hasattr(pond, '_ptt_summary'):
                try:
                    ptt_summary = pond._ptt_summary()
                except Exception:
                    pass
            ponds_out[pond_id] = {
                "pond_id":        pond.pond_id,
                "name":           pond.name,
                "owner_id":       pond.owner_id,
                "pond_type":      pond.pond_type,
                "security_level": pond.security_level,
                "base_address":   pond.base_address,
                "region_size":    pond.region_size,
                "created_at":     pond.created_at,
                "bridges":        bridges_out,
                "pool_cells":     list(getattr(pond, '_pool_cells', [])),
                "restart_count":  getattr(pond, '_restart_count', 0),
                "last_restart":   getattr(pond, '_last_restart', None),
                "ptt_summary":    ptt_summary,
            }
        return {"pond_count": len(ponds_out), "ponds": ponds_out}

    def _serialise_controller(self) -> dict:
        """Capture all loaded regions and their cell configurations."""
        ctrl = self._ctrl
        regions_out = []

        for rid, region in ctrl._regions.items():
            cells_out = []
            for cell_addr in region.cell_addresses:
                cell = ctrl.array.cells.get(cell_addr)
                if cell is None:
                    continue
                cells_out.append({
                    "addr":       cell_addr,
                    "gs":         int(cell.gate_state),
                    "in":         cell.input_address,
                    "out":        cell.output_address,
                    "out_alt":    getattr(cell, "output_address_alt", None),
                    "stored":     int(cell._stored_value) if cell._stored_value is not None else 0,
                    "seg":        getattr(cell, "segment_id", 0),
                })

            regions_out.append({
                "region_id":    rid,
                "image_name":   region.image_name,
                "cell_count":   len(cells_out),
                "cycles_run":   region.cycles_run,
                "state":        region.state,
                "cells":        cells_out,
            })

        return {
            "cell_count":  ctrl.array._cell_count,
            "total_cycles": ctrl.total_cycles,
            "regions":     regions_out,
        }

    def _serialise_shore(self) -> dict:
        """Capture Shore registry, connections, and extended translations."""
        shore = self._shore
        registry_out = {}
        for name, entry in shore._registry.items():
            registry_out[name] = {
                "name":          entry.name,
                "resource_type": entry.resource_type,
                "local_address": entry.local_address,
                "base_address":  entry.base_address,
                "offset":        entry.offset,
                "pond_id":       entry.pond_id,
                "ward_state":    entry.ward_state,
                "view_mask":     entry.view_mask,
                "is_escalated":  entry.is_escalated,
                "capabilities_word": entry.capabilities_word,
                "last_seen":     entry.last_seen,
            }

        connections_out = {}
        for key, conn in shore._connections.items():
            connections_out[str(key)] = {
                "source":      conn.source,
                "destination": conn.destination,
                "state":       conn.state,
                "created_at":  conn.created_at,
            }

        translations_out = {}
        for key, tile in shore._translation.items():
            translations_out[str(key)] = {
                "real_addr":    tile.real_addr  if hasattr(tile, 'real_addr') else tile,
                "proxy_name":   tile.proxy_name if hasattr(tile, 'proxy_name') else "",
            }

        return {
            "shore_id":          shore._shore_id
                                 if hasattr(shore, '_shore_id') else "",
            "base_address":      shore._base_address
                                 if hasattr(shore, '_base_address') else 0,
            "registry_entries":  len(registry_out),
            "registry":          registry_out,
            "connections":       connections_out,
            "translations":      translations_out,
        }

    def _serialise_companion(self) -> dict:
        """Capture Companion keys, regions, and escalation log."""
        comp = self._comp
        if comp is None:
            return {"keys": {}, "key_count": 0, "booted_at": None, "ready": False}
        keys_out = {}
        for kid, key in comp._keys.items():
            keys_out[kid] = {
                "key_id":    key.key_id,
                "key_type":  key.key_type,
                "holder_id": key.holder_id,
                "resource":  getattr(key, 'resource', ''),
                "issued_at": getattr(key, 'issued_at', 0.0),
                "revoked":   key.revoked,
            }

        regions_out = []
        for rec in comp._regions:
            regions_out.append({
                "base":     rec.base,
                "size":     rec.size,
                "owner_id": rec.owner_id,
            })

        log_out = []
        for action in comp._escalation_log[-100:]:  # last 100
            log_out.append({
                "action":     action.action,
                "target":     action.target,
                "reason":     action.reason,
                "source":     action.source,
                "ward_state": action.ward_state,
            })

        return {
            "key_count":       len(keys_out),
            "region_count":    len(regions_out),
            "escalation_count":len(comp._escalation_log),
            "keys":            keys_out,
            "regions":         regions_out,
            "escalation_log":  log_out,
        }

    def _serialise_search(self) -> dict:
        """Capture all SearchPonds with their term→file entries."""
        idx = self._search
        ponds_out = {}
        for name, pond in idx._ponds.items():
            entries_out = []
            for entry in pond._entries:
                entries_out.append({
                    "term":         entry.term,
                    "file_path":    entry.file_path,
                    "file_size":    entry.file_size,
                    "indexed_at":   entry.indexed_at,
                    "access_count": entry.access_count,
                    "hidden":       entry.hidden,
                    "tags":         entry.tags,
                })
            ponds_out[name] = {
                "name":       pond.name,
                "owner_id":   pond.owner_id,
                "hidden":     pond.hidden,
                "created_at": pond.created_at,
                "entries":    entries_out,
            }

        return {
            "pond_count":    len(ponds_out),
            "total_entries": sum(len(p["entries"]) for p in ponds_out.values()),
            "ponds":         ponds_out,
        }

    # ── Load ─────────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str,
             cell_count: Optional[int] = None,
             ai_callback=None
             ) -> tuple:
        """
        Restore a system from an image file.

        path:        path to .img or .img.gz file
        cell_count:  override array size (default: from image)
        ai_callback: optional callable to re-attach AI after restore

        Returns (controller, shore, companion, search_index)
          search_index is None if not in the image.
        """
        print(f"[VM_IMAGE] Loading system image from '{path}'...")
        t0 = time.time()

        if path.endswith('.gz'):
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                image = json.load(f)
        else:
            with open(path, 'r', encoding='utf-8') as f:
                image = json.load(f)

        version = image.get("version", 1)
        if version > IMAGE_VERSION:
            raise ValueError(
                f"Image version {version} > supported {IMAGE_VERSION}")
        # v1/v2 images had 11-bit gate_state; v3+ uses 32-bit; v4+ adds GS_FALL_EDGE; v5+ adds PTT bridge registration.
        # gate_state values from old images are still valid — they only
        # used bits 0-10, which are unchanged in the new layout.
        legacy_gs = (version < 3)
        if legacy_gs:
            print(f"[VM_IMAGE] Legacy image (v{version}): "
                  f"gate_state is 11-bit, will load as-is (bits 0-10 compatible)")

        print(f"[VM_IMAGE] Image: version={version}, "
              f"saved={image.get('saved_at', 0):.0f}, "
              f"system='{image.get('system_id', '?')}'")

        # Restore components
        ctrl  = cls._restore_controller(image["array"], cell_count)
        shore = cls._restore_shore(image["shore"])
        comp  = cls._restore_companion(image["companion"], shore)

        search = None
        if "search_index" in image:
            search = cls._restore_search(image["search_index"])

        elapsed = time.time() - t0
        print(f"[VM_IMAGE] Restored in {elapsed:.3f}s — "
              f"{len(ctrl._regions)} regions, "
              f"{image['shore']['registry_entries']} Shore entries")

        return ctrl, shore, comp, search

    @classmethod
    def _restore_controller(cls, data: dict,
                             cell_count_override=None) -> "ImagoController":
        from unicell_array  import UniCellArray
        from controller     import ImagoController, Region
        from gate_states    import GS_NOT

        n_cells = cell_count_override or data["cell_count"]
        ctrl = ImagoController(cell_count=n_cells)
        ctrl.total_cycles = data.get("total_cycles", 0)

        for rdata in data["regions"]:
            cell_addresses = []
            for cdata in rdata["cells"]:
                cell = ctrl.array.allocate_cell()
                # Restore gate configuration
                packet = [
                    0x01,                # FUNCTION_LOAD_PATTERN
                    cdata["gs"],
                    cdata["in"],
                    cdata["out"],
                ]
                if cdata.get("out_alt") is not None:
                    packet.append(cdata["out_alt"])
                ctrl.array.write_config(cell.address, packet)
                # Restore stored value and segment
                cell._stored_value = cdata.get("stored", 0) or None
                if cdata.get("seg", 0):
                    if cdata.get("seg"): ctrl.array.assign_segment(cell.address, cdata["seg"])
                cell_addresses.append(cell.address)

            region = Region(cell_addresses, rdata["image_name"])
            region.cycles_run = rdata.get("cycles_run", 0)
            region.state      = rdata.get("state", "HALTED")
            ctrl._regions[rdata["region_id"]] = ctrl._track_address_range(region)

        return ctrl

    @classmethod
    def _restore_shore(cls, data: dict) -> "ShoreV2":
        from shore_v2 import ShoreV2, ShoreEntry

        shore_id = data.get("shore_id", "shore_0")
        base     = data.get("base_address", 0x00500000)

        shore = ShoreV2(shore_id=shore_id, base_address=base)

        # Restore registry
        for name, edata in data["registry"].items():
            if name == "__shore__":
                continue   # already created by ShoreV2.__init__
            entry = ShoreEntry(
                name          = edata["name"],
                resource_type = edata["resource_type"],
                local_address = edata["local_address"],
                base_address  = edata["base_address"],
                offset        = edata.get("offset", 0),
                pond_id           = edata.get("pond_id"),
                ward_state        = edata.get("ward_state", "IDLE"),
                view_mask         = edata.get("view_mask", 0xFFFFFFFF),
                is_escalated      = edata.get("is_escalated", False),
                capabilities_word = edata.get("capabilities_word", 0),
            )
            entry.last_seen = edata.get("last_seen", 0.0)
            shore.register(entry)

        # Restore connections
        for key_str, cdata in data.get("connections", {}).items():
            from shore_v2 import Connection
            conn = Connection(
                source      = cdata["source"],
                destination = cdata["destination"],
                state       = cdata.get("state", "LIVE"),
            )
            conn.created_at = cdata.get("created_at", 0.0)
            shore._connections.put(key_str, conn)

        return shore

    @classmethod
    def _restore_companion(cls, data: dict,
                            shore: "ShoreV2") -> "Companion":
        from companion import Companion, AccessKey, RegionRecord

        from unicell_array import UniCellArray
        from controller import ImagoController
        dummy_array = UniCellArray(100)
        dummy_ctrl  = ImagoController(cell_count=100)
        comp = Companion.boot(dummy_array, shore, dummy_ctrl)

        # Restore keys (skip keys already created at boot)
        existing_ids = set(comp._keys.keys())
        for kid, kdata in data["keys"].items():
            if kid in existing_ids:
                continue
            key = AccessKey(
                key_id    = kdata["key_id"],
                key_type  = kdata["key_type"],
                holder_id = kdata["holder_id"],
                resource  = kdata.get("resource", ""),
            )
            key.issued_at  = kdata.get("issued_at", 0.0)
            key.revoked    = kdata.get("revoked", False)
            comp._keys[kid] = key

        # Restore regions
        comp._regions = []
        for rdata in data.get("regions", []):
            rec = RegionRecord(
                base     = rdata["base"],
                size     = rdata["size"],
                owner_id = rdata["owner_id"],
            )
            comp._regions.append(rec)

        # Escalation log is informational — restore last 100 entries as strings
        # (EscalationAction objects; we reconstruct minimal versions)
        from companion import EscalationAction
        for adata in data.get("escalation_log", []):
            action = EscalationAction(
                action     = adata["action"],
                target     = adata["target"],
                reason     = adata["reason"],
                source     = adata.get("source", "restored"),
                ward_state = adata.get("ward_state", ""),
            )
            comp._escalation_log.append(action)

        return comp

    @classmethod
    def _restore_search(cls, data: dict) -> "SearchIndex":
        from fs_search import SearchIndex, SearchPond, SearchEntry

        idx = SearchIndex()
        for pname, pdata in data.get("ponds", {}).items():
            pond = SearchPond(
                name     = pdata["name"],
                owner_id = pdata["owner_id"],
                hidden   = pdata.get("hidden", False),
            )
            pond.created_at = pdata.get("created_at", 0.0)
            for edata in pdata.get("entries", []):
                entry = SearchEntry(
                    term         = edata["term"],
                    file_path    = edata["file_path"],
                    file_size    = edata.get("file_size", 0),
                    indexed_at   = edata.get("indexed_at", 0.0),
                    access_count = edata.get("access_count", 0),
                    hidden       = edata.get("hidden", False),
                    tags         = edata.get("tags", []),
                )
                pond._entries.append(entry)
            idx.add_pond(pond)

        return idx


# ── Convenience functions ─────────────────────────────────────────────────────

def save_image(path: str,
               controller,
               shore,
               companion=None,
               search_index=None,
               pond_manager=None) -> dict:
    """Convenience wrapper for VMImage.save()."""
    img = VMImage(controller, shore, companion,
                  search_index, pond_manager=pond_manager)
    return img.save(path)


def load_image(path: str, cell_count=None):
    """Convenience wrapper for VMImage.load()."""
    return VMImage.load(path, cell_count=cell_count)
