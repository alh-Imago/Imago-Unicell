"""build_ext.py — build all C extensions in-place"""
from setuptools import setup, Extension

exts = [
    Extension(
        "ace.algorithms._lz77_c",
        sources=["ace/algorithms/lz77_c.c"],
        extra_compile_args=["-O3", "-Wall"],
    ),
    Extension(
        "ace.algorithms._huffman_c",
        sources=["ace/algorithms/huffman_c.c"],
        extra_compile_args=["-O3", "-Wall"],
    ),
]

setup(name="onion-compress", ext_modules=exts)
