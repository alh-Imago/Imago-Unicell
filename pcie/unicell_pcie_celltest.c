/*
 * unicell_pcie_celltest.c
 *
 * Drives the exact known-good configure-and-inject sequence from
 * icm64_readstate.tcl (the silicon-proven JTAG/ISSP baseline) over the
 * live PCIe link instead, using AlteraPCILibraryDll.dll's exported
 * AltPci* API directly (via LoadLibrary/GetProcAddress against the raw
 * decorated export names -- no header/import-lib needed, since we only
 * need to pass opaque handles between calls, never touch their internals).
 *
 * Register map (pcie_unicell_bridge.v, confirmed against source):
 *   0x0  CMD_DATA           (write-only staging register)
 *   0x4  CMD_BUS            (write fires cmd_valid pulse)
 *   0x8  STATUS_ADDR_VALID  (read-only: out_valid | out_addr[15:0])
 *   0xC  STATUS_DATA        (read-only: out_data[31:0])
 *
 * Host convention: always write CMD_DATA first, then CMD_BUS.
 *
 * Build (Visual Studio Developer Command Prompt):
 *   cl unicell_pcie_celltest.c
 *
 * Build (MinGW-w64):
 *   gcc -o unicell_pcie_celltest.exe unicell_pcie_celltest.c
 *
 * Run, from the same folder as AlteraPCILibraryDll.dll / msvcr120.dll /
 * msvcp120.dll:
 *   unicell_pcie_celltest.exe <bus> <device> <function> <bar>
 *
 * Use the SAME bus/device/function numbers Alt_Test.exe prompted you
 * for. BAR is almost certainly 0 (the design wires the fabric command/
 * data bus behind BAR0 per the rxm_bar0 connection), but pass whatever
 * BAR number you gave Alt_Test.exe for its own successful PASS run.
 *
 * ALT_STATUS convention: 0 = success is assumed (standard for this kind
 * of API) but not confirmed against the original headers -- if every
 * call reports a consistent non-zero value, treat that value as the
 * real "success" code and re-read the printed sequence accordingly,
 * rather than assuming failure outright.
 */

#include <windows.h>
#include <stdio.h>

typedef void*   (__cdecl *AltInitAPI_t)(void);
typedef int     (__cdecl *AltPciOpenDevice_t)(void*, unsigned, unsigned, unsigned, void*);
typedef int     (__cdecl *AltPciMapResource_t)(void*, unsigned, void*);
typedef int     (__cdecl *AltPciUnmapResource_t)(void*, void*);
typedef int     (__cdecl *AltPciReadAddr32_t)(void*, void*, unsigned, unsigned*);
typedef int     (__cdecl *AltPciWriteAddr32_t)(void*, void*, unsigned, unsigned);
/* Config space. Signature from the mangled exports:
 *   ?AltPciReadCfg@@ ...PAUAltPciDeviceHandle@@PAXKK@Z
 *   -> (handle, void* buf, unsigned long offset, unsigned long length)
 * This is what lets us enable memory decode from Windows -- Intel's driver
 * never sets it, which made every BAR access return 0xFFFFFFFF regardless of
 * what the FPGA was doing, and cost several days of false negatives. */
typedef int     (__cdecl *AltPciReadCfg_t)(void*, void*, unsigned long, unsigned long);
typedef int     (__cdecl *AltPciWriteCfg_t)(void*, void*, unsigned long, unsigned long);

static AltInitAPI_t          pAltInitAPI;
static AltPciOpenDevice_t    pAltPciOpenDevice;
static AltPciMapResource_t   pAltPciMapResource;
static AltPciUnmapResource_t pAltPciUnmapResource;
static AltPciReadAddr32_t    pAltPciReadAddr32;
static AltPciWriteAddr32_t   pAltPciWriteAddr32;
static AltPciReadCfg_t       pAltPciReadCfg;
static AltPciWriteCfg_t      pAltPciWriteCfg;

/* AltPciOpenDevice/AltPciMapResource take a SINGLE pointer to a caller-
 * allocated struct (confirmed from the DLL's mangled export names --
 * "PAUAltPciDeviceHandle@@", not "PAPAUAltPciDeviceHandle@@") which they
 * fill in directly, NOT a void** for the DLL to allocate and hand back.
 * We don't have the original headers to know the real struct sizes, so
 * allocate generously-oversized, zeroed buffers and pass their raw
 * addresses directly -- gives the DLL real room to write into regardless
 * of the actual (unknown) struct size. */
static unsigned char g_devHandleBuf[1024];
static unsigned char g_resHandleBuf[1024];
static void *g_api = NULL;
static void *g_dev = g_devHandleBuf;
static void *g_res = g_resHandleBuf;

/* one configure step: write cmd_data to 0x0, then cmd_bus to 0x4 */
static void step(unsigned cmd_data, unsigned cmd_bus, const char *label) {
    int s1 = pAltPciWriteAddr32(g_dev, g_res, 0x0, cmd_data);
    int s2 = pAltPciWriteAddr32(g_dev, g_res, 0x4, cmd_bus);
    printf("  [%-22s] CMD_DATA=0x%08X CMD_BUS=0x%08X  (status %d,%d)\n",
           label, cmd_data, cmd_bus, s1, s2);
}

int main(int argc, char **argv) {
    if (argc < 5) {
        printf("Usage: %s <bus> <device> <function> <bar> [bar0_address]\n", argv[0]);
        printf("  Use the same bus/device/function Alt_Test.exe used.\n");
        printf("  BAR is almost certainly 0.\n");
        printf("\n");
        printf("  bar0_address is optional and only needed after reprogramming\n");
        printf("  the FPGA without rebooting -- that wipes config space,\n");
        printf("  including BAR0. Get the real address from Device Manager\n");
        printf("  (card -> Resources -> Memory Range) or from lspci, e.g.:\n");
        printf("    %s 8 0 0 0 0xFC9FF000\n", argv[0]);
        printf("  Do NOT guess it. Writing the wrong address makes the card\n");
        printf("  decode somewhere nothing is writing to, and every access\n");
        printf("  then reads 0xFFFFFFFF exactly as if the card were dead.\n");
        return 1;
    }
    unsigned bus  = (unsigned)strtoul(argv[1], NULL, 0);
    unsigned dev  = (unsigned)strtoul(argv[2], NULL, 0);
    unsigned func = (unsigned)strtoul(argv[3], NULL, 0);
    unsigned bar  = (unsigned)strtoul(argv[4], NULL, 0);
    unsigned want_bar = (argc > 5) ? (unsigned)strtoul(argv[5], NULL, 0) : 0u;

    HMODULE h = LoadLibraryA("AlteraPCILibraryDll.dll");
    if (!h) {
        printf("LoadLibrary failed, error %lu\n", GetLastError());
        return 1;
    }

    pAltInitAPI          = (AltInitAPI_t)         GetProcAddress(h, "?AltInitAPI@@YAPAXXZ");
    pAltPciOpenDevice    = (AltPciOpenDevice_t)   GetProcAddress(h, "?AltPciOpenDevice@@YA?AW4ALT_STATUS@@PAXIIIPAUAltPciDeviceHandle@@@Z");
    pAltPciMapResource   = (AltPciMapResource_t)  GetProcAddress(h, "?AltPciMapResource@@YA?AW4ALT_STATUS@@PAUAltPciDeviceHandle@@IPAUAltPciResource@@@Z");
    pAltPciUnmapResource = (AltPciUnmapResource_t)GetProcAddress(h, "?AltPciUnmapResource@@YA?AW4ALT_STATUS@@PAUAltPciDeviceHandle@@PAUAltPciResource@@@Z");
    pAltPciReadAddr32    = (AltPciReadAddr32_t)   GetProcAddress(h, "?AltPciReadAddr32@@YA?AW4ALT_STATUS@@PAUAltPciDeviceHandle@@PAUAltPciResource@@IPAI@Z");
    pAltPciWriteAddr32   = (AltPciWriteAddr32_t)  GetProcAddress(h, "?AltPciWriteAddr32@@YA?AW4ALT_STATUS@@PAUAltPciDeviceHandle@@PAUAltPciResource@@II@Z");
    pAltPciReadCfg       = (AltPciReadCfg_t)      GetProcAddress(h, "?AltPciReadCfg@@YA?AW4ALT_STATUS@@PAUAltPciDeviceHandle@@PAXKK@Z");
    pAltPciWriteCfg      = (AltPciWriteCfg_t)     GetProcAddress(h, "?AltPciWriteCfg@@YA?AW4ALT_STATUS@@PAUAltPciDeviceHandle@@PAXKK@Z");

    if (!pAltInitAPI || !pAltPciOpenDevice || !pAltPciMapResource ||
        !pAltPciUnmapResource || !pAltPciReadAddr32 || !pAltPciWriteAddr32) {
        printf("GetProcAddress failed for one or more exports -- DLL export names may not match.\n");
        return 1;
    }

    g_api = pAltInitAPI();
    if (!g_api) { printf("AltInitAPI returned NULL\n"); return 1; }

    int st = pAltPciOpenDevice(g_api, bus, dev, func, g_dev);
    printf("AltPciOpenDevice(bus=%u dev=%u func=%u) -> status=%d\n", bus, dev, func, st);
    if (st != 0) { printf("Non-zero status -- stopping (see note on ALT_STATUS above).\n"); return 1; }

    /* ORDERING MATTERS: config space is repaired BEFORE AltPciMapResource is
     * called. That function reads BAR0 to work out which physical address to
     * map, so calling it while BAR0 still reads zero -- which is the state
     * right after a JTAG reprogram -- produces a mapping that points at
     * nothing, and fixing the BAR afterwards does not repair a mapping that
     * has already been built. An earlier version of this file had the two
     * the wrong way round and produced exactly that failure. */

    /* ── Enable memory decode ────────────────────────────────────────────────
     * Command register is at config offset 0x04. Bit 1 = memory space enable,
     * bit 2 = bus master. Intel's driver does NOT set bit 1, so without this
     * every BAR read returns 0xFFFFFFFF no matter what the FPGA is doing.
     * Under Linux the equivalent is `setpci -s 08:00.0 COMMAND=0x0006`.
     * The register also resets on every boot, so this runs every time. */
    if (pAltPciReadCfg && pAltPciWriteCfg) {
        unsigned short cmd = 0;
        st = pAltPciReadCfg(g_dev, &cmd, 0x04, 2);
        printf("Command register (before) = 0x%04X  (status %d)\n", cmd, st);

        if (!(cmd & 0x0002)) {
            unsigned short want = (unsigned short)(cmd | 0x0006);
            st = pAltPciWriteCfg(g_dev, &want, 0x04, 2);
            printf("  memory decode was OFF -- writing 0x%04X (status %d)\n", want, st);

            cmd = 0;
            pAltPciReadCfg(g_dev, &cmd, 0x04, 2);
            printf("Command register (after)  = 0x%04X\n", cmd);
        }

        if (!(cmd & 0x0002)) {
            printf("\n  WARNING: memory decode still not set. Every BAR access\n");
            printf("  below will read 0xFFFFFFFF regardless of the FPGA state --\n");
            printf("  treat the results as meaningless, not as a fabric failure.\n\n");
        }
    } else {
        printf("Config-space access unavailable -- cannot verify memory decode.\n");
        printf("  If all reads come back FFFFFFFF, that is the likely reason.\n");
    }

    /* ── Check BAR0's base address ───────────────────────────────────────────
     * BAR0 base lives at config offset 0x10. Reprogramming the FPGA over JTAG
     * resets the entire config space -- including this -- because config space
     * is implemented in the reconfigured logic. Windows keeps its own idea of
     * where the device lives, but the card no longer decodes that address, so
     * everything reads 0xFFFFFFFF.
     *
     * Normally the BIOS reassigns on reboot. Writing it back directly avoids
     * that, which matters here: it means you can reprogram and test without a
     * reboot, and so run this test while SignalTap is capturing over JTAG. */
    if (pAltPciReadCfg && pAltPciWriteCfg) {
        unsigned bar0 = 0;
        st = pAltPciReadCfg(g_dev, &bar0, 0x10, 4);
        printf("BAR0 base (before) = 0x%08X  (status %d)\n", bar0, st);

        /* Only touch BAR0 if the caller told us what it should be. Guessing
         * here caused a real failure: an address read off a Linux boot was
         * hardcoded, Windows had assigned a different one that boot, and the
         * hardcoded value overwrote the correct one -- so the device decoded
         * an address nothing was writing to. Get the value from Device
         * Manager (Resources tab) or lspci and pass it explicitly. */
        if (want_bar != 0 && (bar0 & 0xFFFFFFF0u) != (want_bar & 0xFFFFFFF0u)) {
            printf("  BAR0 disagrees with the address given (0x%08X).\n", want_bar);
            printf("  Writing it back -- reprogramming over JTAG wipes config space.\n");
            st = pAltPciWriteCfg(g_dev, &want_bar, 0x10, 4);
            bar0 = 0;
            pAltPciReadCfg(g_dev, &bar0, 0x10, 4);
            printf("BAR0 base (after)  = 0x%08X  (status %d)\n", bar0, st);
        } else if (want_bar == 0 && (bar0 & 0xFFFFFFF0u) == 0) {
            printf("\n  BAR0 is unassigned and no address was given.\n");
            printf("  Either reboot so the BIOS assigns one, or pass the\n");
            printf("  address from Device Manager as a 5th argument:\n");
            printf("    %s <bus> <dev> <func> <bar> 0xFC9FF000\n\n", argv[0]);
        }
    }

    /* ── Map the BAR ────────────────────────────────────────────────────────
     * Only now, with the Command register and BAR0 both known good. */
    st = pAltPciMapResource(g_dev, bar, g_res);
    printf("\nAltPciMapResource(bar=%u) -> status=%d\n", bar, st);
    if (st != 0) { printf("Non-zero status -- stopping (see note on ALT_STATUS above).\n"); return 1; }

    /* ── Write-path probe ───────────────────────────────────────────────────
     * CMD_DATA and CMD_BUS both read back (cmd_data_staged / cmd_bus_echo),
     * so this proves writes land and the address decode is right before we
     * bother running the sequence. */
    {
        unsigned rb = 0;
        printf("\n--- write-path probe ---\n");
        pAltPciWriteAddr32(g_dev, g_res, 0x0, 0xDEADBEEF);
        pAltPciReadAddr32(g_dev, g_res, 0x0, &rb);
        printf("  CMD_DATA wrote DEADBEEF read %08X %s\n", rb,
               rb == 0xDEADBEEF ? "ok" : "MISMATCH");
        pAltPciWriteAddr32(g_dev, g_res, 0x4, 0xCAFEBABE);
        pAltPciReadAddr32(g_dev, g_res, 0x4, &rb);
        printf("  CMD_BUS  wrote CAFEBABE read %08X %s\n", rb,
               rb == 0xCAFEBABE ? "ok" : "MISMATCH");
    }

    /* Clear any stale sticky result so what we read afterwards is from
     * this run. A write to STATUS_ADDR_VALID clears the latch. */
    pAltPciWriteAddr32(g_dev, g_res, 0x8, 0);

    printf("\n--- replaying icm64_readstate.tcl's known-good configure+inject sequence ---\n");
    step(0x00000000, 0x05280008, "ARRAY_RESET");
    step(0x00A50000, 0x00000007, "BOOT_COMMIT");
    step(0x00000000, 0x00000018, "SET_TARGET->cell0");
    step(0x00000200, 0x05280003, "SET_OUTPUT_ADDR");
    step(0x5282082C, 0x05280004, "RECONFIGURE(PASS_B)");
    step(0x00000000, 0x00000018, "SET_TARGET->cell0");
    step(0x00000004, 0x05280022, "ROUTING(east)");
    step(0x00000000, 0x00000018, "SET_TARGET->cell0");
    step(0x00000001, 0x05280023, "TRANSIT(route-only)");
    step(0x00000000, 0x00000018, "SET_TARGET->cell0");
    step(0x00000000, 0x05280012, "SWAP_AB");
    step(0x000000AA, 0x00000001, "INJECT(addr0,val0xAA)");

    unsigned status_addr_valid = 0, status_data = 0;
    pAltPciReadAddr32(g_dev, g_res, 0x8, &status_addr_valid);
    pAltPciReadAddr32(g_dev, g_res, 0xC, &status_data);

    printf("\n--- result ---\n");
    printf("STATUS_ADDR_VALID (0x8) = 0x%08X\n", status_addr_valid);
    printf("STATUS_DATA       (0xC) = 0x%08X\n", status_data);

    if (status_addr_valid == 0xFFFFFFFF && status_data == 0xFFFFFFFF) {
        printf("\nBoth FFFFFFFF -- the endpoint is not answering at all.\n");
        printf("This is NOT a fabric result. Check the Command register above.\n");
    } else {
        /* pcie_unicell_bridge.v packs this as {15'h0, out_valid, out_addr[15:0]}
         * -- so out_addr is [15:0] and out_valid is bit 16. An earlier version
         * of this comment said bit 0, which was wrong. */
        printf("  out_valid = %u\n", (status_addr_valid >> 16) & 1u);
        printf("  out_addr  = %04X   (expect 0200 from SET_OUTPUT_ADDR)\n",
               status_addr_valid & 0xFFFFu);
        printf("  out_data  = %08X   (expect 0xAA through PASS_B)\n", status_data);
    }

    pAltPciUnmapResource(g_dev, g_res);
    return 0;
}
