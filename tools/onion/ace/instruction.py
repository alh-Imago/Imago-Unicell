"""
instruction.py — AlgoID constants and InstructionSet / LayerDescriptor dataclasses
"""
from dataclasses import dataclass, field
from typing import List


class AlgoID:
    RAW     = 0x00
    RLE     = 0x01
    LZ77    = 0x02
    HUFFMAN = 0x03
    AES256  = 0x04
    DELTA   = 0x05
    LZMA    = 0x06
    LZ4     = 0x07

    _NAMES = {
        0x00: "Raw",
        0x01: "RLE",
        0x02: "LZ77",
        0x03: "Huffman",
        0x04: "AES-256-GCM",
        0x05: "Delta",
        0x06: "LZMA",
        0x07: "LZ4",
    }

    @classmethod
    def name(cls, algo_id: int) -> str:
        return cls._NAMES.get(algo_id, f"Unknown(0x{algo_id:02x})")


@dataclass
class LayerDescriptor:
    algo_id:         int   = 0x00
    compressed_size: int   = 0
    checksum:        int   = 0
    skipped:         bool  = False


@dataclass
class InstructionSet:
    original_size:  int                  = 0
    original_crc:   int                  = 0
    encrypt:        bool                 = False
    entropy_score:  float                = 0.0
    layers:         List[LayerDescriptor] = field(default_factory=list)
    delta_stride:   int                  = 2   # stride used by DELTA layer

    def add(self, algo_id: int) -> None:
        self.layers.append(LayerDescriptor(algo_id=algo_id))

    def summary(self) -> str:
        active = [l for l in self.layers if not l.skipped]
        return " → ".join(AlgoID.name(l.algo_id) for l in active) or "Raw"
