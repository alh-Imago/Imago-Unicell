"""
mathtrix_animate.py — Video and Animation Output for MathTrix
=============================================================
Takes any MathTrix result (Result1D, Result2D, ResultParticles, or
pagerank dict) and produces either:

  - A live window (pygame or matplotlib interactive)
  - An MP4 file (via ffmpeg, no display needed)
  - A GIF file (via Pillow or matplotlib)
  - A sequence of PNG frames

The GPU does the rendering. UniCell produces the data.

Usage:
------
    from mathtrix import quick_gray_scott, quick_nbody, quick_laplacian
    from mathtrix_animate import animate, show

    # Save MP4
    r = quick_gray_scott(size=64, steps=500)
    animate(r, output="turing_patterns.mp4", fps=30)

    # Save GIF
    animate(r, output="turing_patterns.gif", fps=15)

    # Live window (requires display)
    show(r, title="Gray-Scott")

    # Sequence of PNGs
    animate(r, output="frames/frame_{:04d}.png")

    # N-body gravity
    r = quick_nbody(n=12, steps=200)
    animate(r, output="nbody.mp4", fps=24, trail_length=20)

    # 1D heat diffusion
    r = quick_laplacian(size=128, steps=300)
    animate(r, output="heat_1d.mp4", fps=20)

Architecture:
-------------
    mathtrix.py   → Result objects (.frames, .trajectories, .history)
            ↓
    mathtrix_animate.py  → numpy arrays → matplotlib FuncAnimation
            ↓
    ffmpeg / Pillow / display  →  MP4 / GIF / window / PNG

No new data format. The MathTrix output shape defines the renderer:
    Result2D        → 2D heatmap (colourmap applied by GPU via matplotlib)
    Result1D        → line chart animation
    ResultParticles → scatter plot / trail animation
    pagerank dict   → line chart (rank convergence per node)

Colourmaps:
    default  — 'inferno' (perceptually uniform, dark-to-bright)
    wave     — 'RdBu_r' (diverging, zero = white)
    ising    — 'coolwarm' (spin up/down)
    chemical — 'viridis' (reaction-diffusion)
    custom   — any matplotlib colourmap name
"""

from __future__ import annotations

import os
import sys
import math
import time
from pathlib import Path
from typing import Optional, Union

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as mpanim
from matplotlib.colors import Normalize

# Use Agg backend when no display is available (server, SSH, etc.)
# The caller can switch to a different backend before importing this module.
_has_display = bool(os.environ.get("DISPLAY") or
                    os.environ.get("WAYLAND_DISPLAY") or
                    sys.platform == "win32" or
                    sys.platform == "darwin")

if not _has_display and matplotlib.get_backend() == "TkAgg":
    matplotlib.use("Agg")


# ── Colourmap selection ───────────────────────────────────────────────────────

_CMAP_DEFAULTS = {
    "laplacian_1d":  "inferno",
    "laplacian_2d":  "inferno",
    "wave":          "RdBu_r",
    "wave_2d":       "RdBu_r",
    "gray_scott":    "viridis",
    "ising":         "coolwarm",
    "conway":        "plasma",
    "fast_marching": "cividis",
    "pagerank":      "tab10",
    "nbody":         None,      # particle colours, not a heatmap
    "boids":         None,
}

_PARTICLE_COLOURS = [
    "#58a6ff", "#f0883e", "#3fb950", "#f85149",
    "#d29922", "#a371f7", "#39d353", "#ff7b72",
    "#79c0ff", "#ffa657", "#56d364", "#ff7b72",
]


def _pick_cmap(model: str, cmap: Optional[str] = None) -> str:
    if cmap:
        return cmap
    return _CMAP_DEFAULTS.get(model, "inferno")


# ── Frame extraction ──────────────────────────────────────────────────────────

def _frames_2d(result) -> list[np.ndarray]:
    """Convert Result2D frames to list of numpy arrays, normalised 0–1."""
    arrays = []
    for frame in result.frames:
        arr = np.array(frame, dtype=np.float32)
        mn, mx = arr.min(), arr.max()
        if mx > mn:
            arr = (arr - mn) / (mx - mn)
        arrays.append(arr)
    return arrays


def _frames_1d(result) -> list[np.ndarray]:
    """Convert Result1D frames to list of 1D numpy arrays."""
    return [np.array(f, dtype=np.float32) for f in result.frames]


def _frames_particles(result) -> list[np.ndarray]:
    """Convert ResultParticles trajectories to list of Nx2 numpy arrays."""
    return [np.array(f, dtype=np.float32) for f in result.trajectories]


def _frames_ranks(result: dict) -> list[np.ndarray]:
    """Convert pagerank history to list of rank vectors."""
    return [np.array(f, dtype=np.float32) for f in result["history"]]


# ── Renderers ─────────────────────────────────────────────────────────────────

def _make_anim_2d(frames: list[np.ndarray], model: str,
                  title: str, cmap: str,
                  fps: int, figsize: tuple) -> mpanim.FuncAnimation:
    """Heatmap animation for 2D grid results."""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, color="#c9d1d9", fontsize=10, pad=8)

    im = ax.imshow(frames[0], cmap=cmap, vmin=0, vmax=1,
                   interpolation="nearest", aspect="auto",
                   origin="upper")

    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.ax.yaxis.set_tick_params(color="#8b949e")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#8b949e", fontsize=7)

    frame_text = ax.text(0.02, 0.97, "", transform=ax.transAxes,
                         color="#8b949e", fontsize=7, va="top")

    def update(i):
        im.set_data(frames[i])
        frame_text.set_text(f"frame {i+1}/{len(frames)}")
        return im, frame_text

    interval = max(1, 1000 // fps)
    return mpanim.FuncAnimation(fig, update, frames=len(frames),
                                interval=interval, blit=True)


def _make_anim_1d(frames: list[np.ndarray], model: str,
                  title: str, cmap: str,
                  fps: int, figsize: tuple) -> mpanim.FuncAnimation:
    """Line chart animation for 1D grid results."""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#111827")
    ax.set_xlim(0, len(frames[0]) - 1)
    ymin = min(f.min() for f in frames)
    ymax = max(f.max() for f in frames)
    margin = (ymax - ymin) * 0.05 or 0.1
    ax.set_ylim(ymin - margin, ymax + margin)
    ax.tick_params(colors="#8b949e"); ax.spines[:].set_color("#30363d")
    ax.set_title(title, color="#c9d1d9", fontsize=10, pad=8)

    x = np.arange(len(frames[0]))
    line, = ax.plot(x, frames[0], color="#58a6ff", linewidth=1.5)
    fill = ax.fill_between(x, frames[0], ymin - margin,
                           alpha=0.15, color="#58a6ff")
    frame_text = ax.text(0.98, 0.97, "", transform=ax.transAxes,
                         color="#8b949e", fontsize=7, va="top", ha="right")

    def update(i):
        nonlocal fill
        line.set_ydata(frames[i])
        fill.remove()
        fill = ax.fill_between(x, frames[i], ymin - margin,
                               alpha=0.15, color="#58a6ff")
        frame_text.set_text(f"frame {i+1}/{len(frames)}")
        return line, frame_text

    interval = max(1, 1000 // fps)
    return mpanim.FuncAnimation(fig, update, frames=len(frames),
                                interval=interval, blit=False)


def _make_anim_particles(frames: list[np.ndarray], model: str,
                         title: str, trail_length: int,
                         fps: int, figsize: tuple) -> mpanim.FuncAnimation:
    """Scatter/trail animation for particle results (N-body, boids)."""
    n = frames[0].shape[0] if len(frames) > 0 else 1

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#111827")
    ax.set_xlim(-0.05, 1.05); ax.set_ylim(-0.05, 1.05)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, color="#c9d1d9", fontsize=10, pad=8)
    ax.spines[:].set_color("#30363d")

    colours = [_PARTICLE_COLOURS[i % len(_PARTICLE_COLOURS)] for i in range(n)]

    # Trail lines
    trail_lines = []
    for i in range(n):
        line, = ax.plot([], [], color=colours[i], alpha=0.3,
                        linewidth=0.8, solid_capstyle="round")
        trail_lines.append(line)

    # Current position dots
    scatters = []
    for i in range(n):
        sc = ax.plot([], [], "o", color=colours[i], markersize=6,
                     markeredgecolor="#0d1117", markeredgewidth=0.5)[0]
        scatters.append(sc)

    frame_text = ax.text(0.02, 0.97, "", transform=ax.transAxes,
                         color="#8b949e", fontsize=7, va="top")

    def update(fi):
        for i in range(n):
            # Trail: last trail_length frames
            start = max(0, fi - trail_length)
            trail_x = [((frames[f][i][0]) % 1.0) for f in range(start, fi+1)]
            trail_y = [((frames[f][i][1]) % 1.0) for f in range(start, fi+1)]
            trail_lines[i].set_data(trail_x, trail_y)
            # Current position
            cx = (frames[fi][i][0]) % 1.0
            cy = (frames[fi][i][1]) % 1.0
            scatters[i].set_data([cx], [cy])
        frame_text.set_text(f"frame {fi+1}/{len(frames)}")
        return trail_lines + scatters + [frame_text]

    interval = max(1, 1000 // fps)
    return mpanim.FuncAnimation(fig, update, frames=len(frames),
                                interval=interval, blit=True)


def _make_anim_ranks(frames: list[np.ndarray], model: str,
                     title: str, fps: int,
                     figsize: tuple) -> mpanim.FuncAnimation:
    """Line chart animation for PageRank convergence."""
    n_nodes = min(frames[0].shape[0], 8)  # show top 8

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#111827")
    ax.set_xlim(0, len(frames) - 1)
    ax.set_ylim(0, max(f.max() for f in frames) * 1.1)
    ax.tick_params(colors="#8b949e"); ax.spines[:].set_color("#30363d")
    ax.set_title(title, color="#c9d1d9", fontsize=10, pad=8)
    ax.set_xlabel("Iteration", color="#8b949e", fontsize=8)
    ax.set_ylabel("Rank", color="#8b949e", fontsize=8)

    lines = []
    for i in range(n_nodes):
        colour = _PARTICLE_COLOURS[i % len(_PARTICLE_COLOURS)]
        line, = ax.plot([], [], color=colour, linewidth=1.5,
                        label=f"node {i}")
        lines.append(line)
    ax.legend(fontsize=7, labelcolor="#c9d1d9",
              facecolor="#161b22", edgecolor="#30363d")

    def update(fi):
        x = list(range(fi + 1))
        for i, line in enumerate(lines):
            y = [frames[f][i] for f in range(fi + 1)]
            line.set_data(x, y)
        return lines

    interval = max(1, 1000 // fps)
    return mpanim.FuncAnimation(fig, update, frames=len(frames),
                                interval=interval, blit=True)


# ── Public API ────────────────────────────────────────────────────────────────

def animate(
    result,
    output: str,
    fps: int = 20,
    dpi: int = 120,
    cmap: Optional[str] = None,
    trail_length: int = 15,
    figsize: tuple = (6, 6),
    title: Optional[str] = None,
    verbose: bool = True,
) -> str:
    """
    Render a MathTrix result to a video or image file.

    Parameters
    ----------
    result      : Result1D, Result2D, ResultParticles, or pagerank dict
    output      : Output path. Extension determines format:
                    .mp4  — H.264 video via ffmpeg (recommended)
                    .gif  — animated GIF via Pillow
                    .png  — if path contains {}, saves frame sequence
                            e.g. "frames/frame_{:04d}.png"
    fps         : Frames per second (default 20)
    dpi         : Dots per inch for raster output (default 120)
    cmap        : Matplotlib colourmap name (auto-selected if None)
    trail_length: Particle trail length in frames (default 15)
    figsize     : Figure size in inches (default 6×6)
    title       : Window/figure title (auto from model name if None)
    verbose     : Print progress (default True)

    Returns
    -------
    Absolute path of the written file.

    Examples
    --------
    >>> from mathtrix import quick_gray_scott
    >>> r = quick_gray_scott(size=64, steps=500)
    >>> animate(r, "turing.mp4", fps=30)
    '/path/to/turing.mp4'
    """
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = _detect_model(result)
    t = title or _make_title(result, model)
    c = _pick_cmap(model, cmap)

    if verbose:
        print(f"  ⬡ MathTrix animate: {model} → {output_path.name}")

    anim = _build_animation(result, model, t, c, fps, figsize, trail_length)

    ext = output_path.suffix.lower()

    if ext == ".mp4":
        writer = mpanim.FFMpegWriter(
            fps=fps,
            metadata={"title": t, "artist": "UniCell MathTrix"},
            extra_args=["-vcodec", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "18", "-preset", "fast"],
        )
        if verbose:
            print(f"  Encoding {len(_get_frames(result))} frames at {fps}fps → {output_path}")
        anim.save(str(output_path), writer=writer, dpi=dpi)

    elif ext == ".gif":
        writer = mpanim.PillowWriter(fps=fps)
        if verbose:
            print(f"  Encoding {len(_get_frames(result))} frames → {output_path}")
        anim.save(str(output_path), writer=writer, dpi=dpi)

    elif ext == ".png" and "{" in output:
        # Frame sequence
        frames = _get_frames(result)
        if verbose:
            print(f"  Saving {len(frames)} PNG frames to {output_path.parent}/")
        for fi, frame_data in enumerate(frames):
            frame_path = output_path.parent / (output_path.name.format(fi))
            fig, ax = _make_single_frame_fig(frame_data, model, t, c, figsize)
            fig.savefig(str(frame_path), dpi=dpi, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)

    else:
        # Single PNG — save final frame
        frames = _get_frames(result)
        fig, ax = _make_single_frame_fig(frames[-1], model, t, c, figsize)
        fig.savefig(str(output_path), dpi=dpi, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)

    plt.close("all")

    if verbose:
        size_kb = output_path.stat().st_size // 1024
        print(f"  ✓ Written: {output_path} ({size_kb} KB)")

    return str(output_path)


def show(
    result,
    fps: int = 20,
    cmap: Optional[str] = None,
    trail_length: int = 15,
    figsize: tuple = (7, 7),
    title: Optional[str] = None,
    loop: bool = True,
) -> None:
    """
    Show a MathTrix result in a live window.

    Requires a display (X11, Wayland, macOS, Windows).
    On a headless server, use animate() to save a file instead.

    Parameters
    ----------
    result      : Result1D, Result2D, ResultParticles, or pagerank dict
    fps         : Playback speed in frames per second
    cmap        : Matplotlib colourmap (auto if None)
    trail_length: Particle trail length (default 15)
    figsize     : Window size in inches
    title       : Window title
    loop        : Loop animation (default True)
    """
    model = _detect_model(result)
    t = title or _make_title(result, model)
    c = _pick_cmap(model, cmap)

    anim = _build_animation(result, model, t, c, fps, figsize, trail_length)
    anim._repeat = loop

    plt.tight_layout()
    plt.show()
    plt.close("all")


def snapshot(
    result,
    output: str,
    frame: int = -1,
    dpi: int = 150,
    cmap: Optional[str] = None,
    figsize: tuple = (6, 6),
    title: Optional[str] = None,
) -> str:
    """
    Save a single frame as a PNG. Default: final frame.

    Useful for the paper, README, and documentation.
    """
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    model = _detect_model(result)
    t = title or _make_title(result, model)
    c = _pick_cmap(model, cmap)
    frames = _get_frames(result)
    frame_data = frames[frame]

    fig, ax = _make_single_frame_fig(frame_data, model, t, c, figsize)
    fig.savefig(str(output_path), dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)

    return str(output_path)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _detect_model(result) -> str:
    """Detect result type from object or dict."""
    if isinstance(result, dict):
        return result.get("model", "pagerank")
    return getattr(result, "model", "unknown")


def _make_title(result, model: str) -> str:
    titles = {
        "laplacian_1d":  "1D Heat Diffusion",
        "laplacian_2d":  "2D Heat Diffusion",
        "wave_2d":       "2D Wave Equation",
        "gray_scott":    "Gray-Scott Turing Patterns",
        "ising":         "Ising Spin Lattice",
        "nbody":         "N-Body Gravity",
        "boids":         "Boids Flocking",
        "pagerank":      "PageRank Convergence",
        "conway":        "Continuous Conway",
        "fast_marching": "Fast Marching — Geodesic Wavefront",
    }
    return titles.get(model, model.replace("_", " ").title())


def _get_frames(result) -> list:
    """Get raw frames from any result type."""
    if isinstance(result, dict):
        return result.get("history", result.get("frames", []))
    if hasattr(result, "trajectories"):
        return result.trajectories
    return result.frames


def _build_animation(result, model, title, cmap, fps, figsize,
                     trail_length) -> mpanim.FuncAnimation:
    """Dispatch to the right renderer based on result type."""
    if isinstance(result, dict):
        frames = _frames_ranks(result)
        return _make_anim_ranks(frames, model, title, fps, figsize)

    result_type = type(result).__name__

    if result_type == "Result2D":
        frames = _frames_2d(result)
        return _make_anim_2d(frames, model, title, cmap, fps, figsize)

    if result_type == "Result1D":
        frames = _frames_1d(result)
        return _make_anim_1d(frames, model, title, cmap, fps, figsize)

    if result_type == "ResultParticles":
        frames = _frames_particles(result)
        return _make_anim_particles(frames, model, title, trail_length,
                                    fps, figsize)

    raise ValueError(
        f"Unknown result type '{result_type}'. "
        f"Expected Result1D, Result2D, ResultParticles, or pagerank dict."
    )


def _make_single_frame_fig(frame_data, model, title, cmap, figsize):
    """Render a single frame to a matplotlib figure."""
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(title, color="#c9d1d9", fontsize=10, pad=8)

    if isinstance(frame_data, np.ndarray) and frame_data.ndim == 2:
        im = ax.imshow(frame_data, cmap=cmap, vmin=0, vmax=1,
                       interpolation="nearest", aspect="auto", origin="upper")
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        cbar.ax.yaxis.set_tick_params(color="#8b949e")
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#8b949e", fontsize=7)
    elif isinstance(frame_data, np.ndarray) and frame_data.ndim == 1:
        x = np.arange(len(frame_data))
        ax.plot(x, frame_data, color="#58a6ff", linewidth=1.5)
        ax.fill_between(x, frame_data, frame_data.min() * 0.9,
                        alpha=0.15, color="#58a6ff")
        ax.tick_params(colors="#8b949e")
        ax.spines[:].set_color("#30363d")
    elif isinstance(frame_data, np.ndarray) and frame_data.ndim == 2 and frame_data.shape[1] == 2:
        # Particles
        for i in range(frame_data.shape[0]):
            c = _PARTICLE_COLOURS[i % len(_PARTICLE_COLOURS)]
            ax.plot(frame_data[i, 0] % 1.0, frame_data[i, 1] % 1.0,
                    "o", color=c, markersize=8)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    return fig, ax


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    from mathtrix import (
        MathTrix, Grid1D, Grid2D,
        quick_laplacian, quick_gray_scott, quick_nbody,
    )

    parser = argparse.ArgumentParser(
        description="MathTrix Animation Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mathtrix_animate.py                        # all demos → /tmp/
  python mathtrix_animate.py --demo wave --out w.mp4
  python mathtrix_animate.py --demo nbody --fps 30
  python mathtrix_animate.py --demo gray_scott --gif
        """,
    )
    parser.add_argument("--demo", default="all",
                        choices=["all","laplacian","wave","gray_scott",
                                 "nbody","ising","boids","conway",
                                 "fast_marching","pagerank"])
    parser.add_argument("--out",  default=None, help="Output path")
    parser.add_argument("--fps",  type=int, default=20)
    parser.add_argument("--gif",  action="store_true", help="Save as GIF")
    parser.add_argument("--show", action="store_true", help="Show live window")
    parser.add_argument("--size", type=int, default=32)
    parser.add_argument("--steps",type=int, default=60)
    args = parser.parse_args()

    ext = ".gif" if args.gif else ".mp4"
    outdir = Path(args.out).parent if args.out else Path("/tmp/unicell_demo")
    outdir.mkdir(parents=True, exist_ok=True)

    mt = MathTrix()

    demos = {
        "laplacian": lambda: (
            quick_laplacian(size=args.size or 64, steps=args.steps or 80),
            "laplacian_1d"
        ),
        "wave": lambda: (
            mt.wave_2d(Grid2D(args.size, args.size).set_gaussian(),
                       steps=args.steps or 60),
            "wave_2d"
        ),
        "gray_scott": lambda: (
            quick_gray_scott(size=args.size or 48, steps=args.steps or 120),
            "gray_scott"
        ),
        "nbody": lambda: (
            quick_nbody(n=8, steps=args.steps or 80),
            "nbody"
        ),
        "ising": lambda: (
            mt.ising(Grid2D(args.size, args.size).set_random_spins(),
                     T=2.5, steps=args.steps or 80),
            "ising"
        ),
        "boids": lambda: (
            mt.boids(n=16, steps=args.steps or 80),
            "boids"
        ),
        "conway": lambda: (
            mt.conway(Grid2D(args.size, args.size), steps=args.steps or 60),
            "conway"
        ),
        "fast_marching": lambda: (
            mt.laplacian_2d(  # placeholder until fast_marching in mathtrix
                Grid2D(args.size, args.size).set_gaussian(), steps=args.steps or 60),
            "fast_marching"
        ),
        "pagerank": lambda: (
            mt.pagerank(nodes=12, steps=args.steps or 30),
            "pagerank"
        ),
    }

    run_demos = list(demos.keys()) if args.demo == "all" else [args.demo]

    for name in run_demos:
        print(f"\n{'─'*40}")
        print(f"Demo: {name}")
        result, model_id = demos[name]()
        out = args.out or str(outdir / f"{name}{ext}")

        if args.show:
            show(result, fps=args.fps, title=_make_title(result, model_id))
        else:
            animate(result, out, fps=args.fps)

    print(f"\n{'─'*40}")
    print(f"All demos complete. Output: {outdir}/")
