"""Deterministic research harness for foveation policies.

This module deliberately separates (a) synthetic gaze/scene inputs, (b) an
image-space sample-sharing reference model, and (c) metrics and provenance.

IMPORTANT: The model is NOT Vulkan VRS, hardware GPU timing, or a calibrated
perceptual metric. Nothing reported here should be called measured GPU speedup.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from foveabench import __version__

# All angles are in degrees; gaze coordinates are normalized screen positions.
# A FOV is needed to turn normalized distances into physical angular offsets.
H_FOV_DEG, V_FOV_DEG = 90.0, 90.0
FOVEA_DEG, MIDDLE_DEG = 5.0, 15.0
TILE_PX = 8  # Multiple of 1x1, 2x2 and 4x4 reference sample footprints.
POLICIES = ("full", "fixed", "gaze_0ms", "gaze_40ms", "gaze_80ms")
TRACES = ("fixation", "pursuit", "saccade")
SCENES = ("chirp", "edges")


@dataclass(frozen=True)
class Gaze:
    """Synthetic sample. Time is integer ns, origin is normalized image space."""
    timestamp_ns: int
    x: float
    y: float
    valid: bool = True


def assert_gaze(samples: list[Gaze]) -> None:
    """Reject malformed traces instead of silently clamping or interpolating."""
    if not samples:
        raise ValueError("Empty gaze trace")
    prev = -1
    for sample in samples:
        if sample.timestamp_ns <= prev:
            raise ValueError("Gaze timestamps must be strictly increasing")
        if not (math.isfinite(sample.x) and math.isfinite(sample.y)):
            raise ValueError("Gaze coordinates must be finite")
        if not (0 <= sample.x <= 1 and 0 <= sample.y <= 1):
            raise ValueError("Gaze coordinates must lie in [0, 1]")
        prev = sample.timestamp_ns


def gaze_trace(kind: str, frames: int, hz: int) -> list[Gaze]:
    """Generate a fixed synthetic stimulus, never labelled as human eye data."""
    if kind not in TRACES or frames < 2 or hz < 1:
        raise ValueError("Invalid trace kind, frame count or sample frequency")
    out = []
    for i in range(frames):
        t = i / hz
        if kind == "fixation":
            x, y = .72, .42
        elif kind == "pursuit":
            x = .50 + .30 * math.sin(2 * math.pi * .65 * t)
            y = .50 + .12 * math.sin(2 * math.pi * .33 * t)
        else:  # Controlled abrupt changes; not a physiological saccade model.
            segment_frames = max(2, min(hz // 3, frames // 3))
            x, y = ((.22, .32) if (i // segment_frames) % 2 == 0
                    else (.78, .68))
        out.append(Gaze(round(i * 1_000_000_000 / hz), x, y))
    assert_gaze(out)
    return out


def gaze_at_delay(trace: list[Gaze], index: int, delay_ms: int) -> Gaze:
    """Zero-order hold: most recent sample timestamp <= frame_time-delay."""
    if delay_ms < 0:
        raise ValueError("Negative latency is invalid")
    target = trace[index].timestamp_ns - delay_ms * 1_000_000
    timestamps = [s.timestamp_ns for s in trace]
    selected = max(0, bisect.bisect_right(timestamps, target) - 1)
    return trace[selected]


def angular_map(width: int, height: int, gx: float, gy: float) -> np.ndarray:
    """3-D ray angular separation on a rectilinear virtual display.

    Pixels and gaze are mapped through the same pinhole projection and the
    acos(dot(normalized_ray(pixel), normalized_ray(gaze))) great-circle angle
    is reported in degrees. This is NOT an HMD lens-distortion calibration.
    """
    u = (np.arange(width, dtype=np.float64) + .5) / width
    v = (np.arange(height, dtype=np.float64) + .5) / height
    tx = math.tan(math.radians(H_FOV_DEG / 2))
    ty = math.tan(math.radians(V_FOV_DEG / 2))
    px = (2 * u - 1)[None, :] * tx
    py = (1 - 2 * v)[:, None] * ty
    gz = np.array([(2 * gx - 1) * tx, (1 - 2 * gy) * ty, 1.0])
    gz /= np.linalg.norm(gz)
    dot = (px * gz[0] + py * gz[1] + gz[2]) / np.sqrt(px * px + py * py + 1)
    return np.degrees(np.arccos(np.clip(dot, -1, 1)))


def reference_scene(kind: str, width: int, height: int, frame: int) -> np.ndarray:
    """Two deterministic, hand-defined visual stressors, not real XR scenes.

    'chirp' raises spatial frequency with x and introduces slight motion.
    'edges' uses hard edges/checkers that reveal block-sharing artifacts.
    Both are intentionally full-resolution reference images.
    """
    x, y = np.meshgrid(np.arange(width) / width, np.arange(height) / height)
    if kind == "chirp":
        wave = np.sin(2 * np.pi * (5 * x + 36 * x*x + .07 * frame))
        stripe = np.cos(2 * np.pi * (8 * y + 12 * x*y))
        rgb = np.stack([.5 + .45 * wave, .5 + .42 * stripe,
                        .5 + .24 * wave + .22 * stripe], axis=2)
    elif kind == "edges":
        check = ((np.floor(x * 42) + np.floor(y * 25)) % 2)
        disk = ((x - (.50 + .10 * np.sin(frame / 8)))**2
                + (y - .48)**2 < .13**2).astype(float)
        bar = (abs(x - (.20 + frame / (width*4))) < .018).astype(float)
        rgb = np.stack([.15 + .7 * check, .12 + .75 * disk,
                        .15 + .7 * bar], axis=2)
    else:
        raise ValueError("Unknown visual stimulus")
    return np.ascontiguousarray(np.uint8(np.round(np.clip(rgb, 0, 1) * 255)))


def render_reference_model(reference: np.ndarray, gaze_xy: tuple[float, float],
                           policy: str) -> tuple[np.ndarray, int]:
    """Imitate block sample sharing in a variable-rate shading-like image.

    Each 8x8 tile chooses one of three footprints (1,2,4) based on angular
    distance at its center to the *policy* gaze. A block emits the color of
    its central reference pixel. Count is an analytical sample proxy, NOT
    hardware shader-invocation counter. This can model image artifacts and
    coarse shading demand, but NOT Vulkan shading behavior/performance.
    """
    h, w, _ = reference.shape
    if policy == "full":
        return reference.copy(), w * h
    gx, gy = (.5, .5) if policy == "fixed" else gaze_xy
    output = np.empty_like(reference)
    # Tile-center angular classification prevents per-pixel nonuniformity from
    # being mistaken for hardware VRS (whose supported combiner/tile rules vary).
    angles = angular_map(w, h, gx, gy)
    samples = 0
    for y0 in range(0, h, TILE_PX):
        for x0 in range(0, w, TILE_PX):
            y1, x1 = min(y0 + TILE_PX, h), min(x0 + TILE_PX, w)
            theta = float(angles[(y0+y1-1)//2, (x0+x1-1)//2])
            rate = 1 if theta <= FOVEA_DEG else 2 if theta <= MIDDLE_DEG else 4
            for yy in range(y0, y1, rate):
                for xx in range(x0, x1, rate):
                    yy1, xx1 = min(yy+rate, y1), min(xx+rate, x1)
                    # Nearest-center sample, no anti-alias or reconstructed blur.
                    sy, sx = min(yy + rate//2, h-1), min(xx + rate//2, w-1)
                    output[yy:yy1, xx:xx1] = reference[sy, sx]
                    samples += 1
    return output, samples


def quality_metrics(ref: np.ndarray, output: np.ndarray,
                    actual_gaze: Gaze) -> dict[str, float | None]:
    """Compute exact RGB pixel error, gaze-weighted error and foveal error.

    The Gaussian weight is an explicitly chosen diagnostic, NOT a calibrated
    perceptual JND model. A 1% uniform floor prevents invisible outer pixels
    from being given zero weight. 'None' PSNR denotes perfect MSE=0.
    """
    h, w, _ = ref.shape
    theta = angular_map(w, h, actual_gaze.x, actual_gaze.y)
    err = (ref.astype(np.float64) - output.astype(np.float64)) ** 2
    per_pixel = np.mean(err, axis=2)
    mse = float(np.mean(per_pixel))
    weight = .01 + np.exp(-.5 * (theta / 5.0)**2)
    wmse = float(np.sum(per_pixel * weight) / np.sum(weight))
    foveal = per_pixel[theta <= FOVEA_DEG]
    foveal_mse = float(np.mean(foveal)) if foveal.size else None
    def psnr(m: float) -> float | None:
        return 10 * math.log10(255*255 / m) if m > 0 else None
    return {"mse": mse, "psnr_db": psnr(mse),
            "weighted_mse": wmse, "weighted_psnr_db": psnr(wmse),
            "foveal_mse": foveal_mse}


def write_ppm(path: Path, frame: np.ndarray) -> None:
    """Store exact raw RGB pixels with zero optional image dependencies."""
    h, w, _ = frame.shape
    with path.open("wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
        f.write(np.ascontiguousarray(frame).tobytes())


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    """One row per scene, trace, and policy; no fake significance tests."""
    result = []
    for scene in SCENES:
        for trace in TRACES:
            for policy in POLICIES:
                r = [x for x in rows if x["scene"] == scene
                     and x["trace"] == trace and x["policy"] == policy]
                cpu = [x["cpu_model_ms"] for x in r]
                def mean(key: str) -> float:
                    return round(statistics.fmean(x[key] for x in r), 6)
                def percentile(q: float) -> float:
                    return round(float(np.percentile(cpu, q)), 6)
                result.append({
                    "scene": scene, "trace": trace, "policy": policy,
                    "frames": len(r), "avg_mse": mean("mse"),
                    "avg_weighted_mse": mean("weighted_mse"),
                    "avg_foveal_mse": mean("foveal_mse"),
                    "mean_sample_fraction_proxy": mean("sample_fraction_proxy"),
                    "cpu_model_p50_ms_diagnostic": percentile(50),
                    "cpu_model_p95_ms_diagnostic": percentile(95),
                    "cpu_model_p99_ms_diagnostic": percentile(99),
                })
    return result


def write_svg(path: Path, summary: list[dict]) -> None:
    """Dependency-free static Pareto-style diagnostic: proxy vs weighted MSE."""
    # One scene/trace chosen for legibility; other conditions remain in CSV.
    group = [r for r in summary if r["scene"] == "chirp"
             and r["trace"] == "saccade"]
    maximum = max((r["avg_weighted_mse"] for r in group), default=1) or 1
    colors = {"full": "#222222", "fixed": "#986800", "gaze_0ms": "#137b51",
              "gaze_40ms": "#346ac4", "gaze_80ms": "#a7335b"}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="850" height="520" viewBox="0 0 850 520">',
           '<rect width="850" height="520" fill="white"/>',
           '<text x="70" y="37" font-family="sans-serif" font-size="19">Saccade / chirp: analytical sample cost versus error</text>',
           '<text x="70" y="58" font-family="sans-serif" font-size="12">Reference model only — not actual GPU samples or perceptual validation</text>',
           '<path d="M80 90 V445 H780" stroke="#222" stroke-width="2" fill="none"/>',
           '<text x="305" y="495" font-family="sans-serif" font-size="14">Sample fraction proxy (lower is less modeled work)</text>',
           '<text x="10" y="80" font-family="sans-serif" font-size="12">Gaze-weighted MSE (lower is better)</text>']
    for row in group:
        x = 80 + 700 * float(row["mean_sample_fraction_proxy"])
        y = 445 - 330 * float(row["avg_weighted_mse"]) / maximum
        c = colors[row["policy"]]
        label = row["policy"].replace("&", "&amp;")
        svg += [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="{c}"/>',
                f'<text x="{min(x+10,690):.2f}" y="{y-9:.2f}" font-family="sans-serif" font-size="12">{label}</text>']
    svg.append('</svg>')
    path.write_text("\n".join(svg), encoding="utf-8")


def run(preset: str, output: Path) -> None:
    """Run a synthetic, deterministic suite and create an auditable package."""
    if preset not in ("smoke", "study"):
        raise ValueError("Unknown preset")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}. Choose a fresh --output.")
    frames, width, height, hz = ((12, 128, 72, 60) if preset == "smoke"
                                 else (90, 256, 144, 90))
    output.mkdir(parents=True)
    (output / "frames").mkdir()
    (output / "traces").mkdir()
    raw = []
    traces = {name: gaze_trace(name, frames, hz) for name in TRACES}
    hashes = {}
    for name, samples in traces.items():
        trace_path = output / "traces" / f"{name}.csv"
        write_csv(trace_path, ["timestamp_ns", "x", "y", "valid"],
                  [vars(g) for g in samples])
        hashes[name] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    for scene in SCENES:
        for trace_name, samples in traces.items():
            for i, gaze in enumerate(samples):
                ref = reference_scene(scene, width, height, i)
                for policy in POLICIES:
                    if policy == "full":
                        selected = gaze
                    elif policy == "fixed":
                        selected = Gaze(gaze.timestamp_ns, .5, .5)
                    else:
                        latency = int(policy.split("_")[1].removesuffix("ms"))
                        selected = gaze_at_delay(samples, i, latency)
                    start = time.perf_counter_ns()
                    image, n = render_reference_model(
                        ref, (selected.x, selected.y), policy)
                    cpu_ms = (time.perf_counter_ns() - start) / 1_000_000
                    metric = quality_metrics(ref, image, gaze)
                    raw.append({
                        "scene": scene, "trace": trace_name, "policy": policy,
                        "frame_index": i, "timestamp_ns": gaze.timestamp_ns,
                        "true_x": gaze.x, "true_y": gaze.y,
                        "used_x": selected.x, "used_y": selected.y,
                        "sample_count_proxy": n,
                        "sample_fraction_proxy": n / (width * height),
                        "cpu_model_ms": cpu_ms,
                        "mse": metric["mse"], "weighted_mse": metric["weighted_mse"],
                        "foveal_mse": metric["foveal_mse"],
                        "psnr_db": metric["psnr_db"],
                        "weighted_psnr_db": metric["weighted_psnr_db"],
                    })
                    # Artifact examples; all frames' numeric results still logged.
                    if i in (0, frames//2):
                        write_ppm(output / "frames" /
                                  f"{scene}_{trace_name}_{policy}_{i:03d}.ppm", image)
    write_csv(output / "frames.csv", list(raw[0]), raw)
    summary = summarize(raw)
    write_csv(output / "summary.csv", list(summary[0]), summary)
    write_svg(output / "overview.svg", summary)
    # Assertions are also recorded as a machine-readable evidence ledger.
    full_rows = [r for r in raw if r["policy"] == "full"]
    checks = {
        "trace_monotonic_and_bounded": "PASS",
        "full_reference_pixel_identical": "PASS" if all(r["mse"] == 0 for r in full_rows) else "FAIL",
        "full_reference_sample_fraction_one": "PASS" if all(r["sample_fraction_proxy"] == 1 for r in full_rows) else "FAIL",
        "all_sample_fractions_physical_bounds": "PASS" if all(0 < r["sample_fraction_proxy"] <= 1 for r in raw) else "FAIL",
        "software_model_initial_run": "PASS",
        "ubuntu_utm_execution": "NOT_RUN",
        "real_vulkan_gpu_timestamps": "NOT_IMPLEMENTED",
        "illixr_adapter": "NOT_IMPLEMENTED",
        "recorded_human_gaze": "NOT_IMPLEMENTED",
        "live_replay_agreement": "NOT_TESTED",
        "fpga_xilinx_vivado": "OUT_OF_SCOPE",
    }
    manifest = {
        "project": "FoveaBench", "version": __version__,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preset": preset, "frames_per_condition": frames,
        "resolution": [width, height], "sample_hz": hz,
        "fov_degrees": [H_FOV_DEG, V_FOV_DEG],
        "foveal_threshold_deg": FOVEA_DEG, "middle_threshold_deg": MIDDLE_DEG,
        "tile_px": TILE_PX, "traces_sha256": hashes,
        "runner_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "software": {"python": sys.version.split()[0], "numpy": np.__version__,
                     "system": platform.platform(), "machine": platform.machine()},
        "evidence": "synthetic-trace synthetic-scene CPU image-space reference model",
        "limitations": [
            "No GPU/Vulkan performance, energy, photometric calibration, real eye tracking, or FPGA measurements.",
            "Sample count is an idealized proxy, not a hardware shader-invocation count.",
            "Gaussian gaze-weighted MSE is a diagnostic, not an experimentally validated perceptual metric.",
            "Deterministic stimuli do not imply wall-clock runtime determinism.",
            "The first unavailable delayed gaze is held at the earliest sample; startup frames are included.",
        ],
        "files": ["frames.csv", "summary.csv", "overview.svg", "traces/", "frames/"],
        "checks": checks,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "STATUS.md").write_text(
        "# Execution ledger\n\n" +
        "\n".join(f"- **{key}**: {status}" for key,status in checks.items()) +
        "\n\nThese checks certify only the local reference-model run.\n",
        encoding="utf-8")
    if any(v == "FAIL" for v in checks.values()):
        raise RuntimeError("Internal experiment validation failed; see manifest.json")
    print(f"PASS: {len(raw)} model frames; {len(summary)} conditions")
    print(f"Output: {output.resolve()}")
    print("WARNING: Model/proxy results only; NO measured GPU performance.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="Run the first synthetic comparison")
    run_parser.add_argument("--preset", choices=("smoke", "study"), default="smoke")
    run_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        run(args.preset, args.output)


if __name__ == "__main__":
    main()
