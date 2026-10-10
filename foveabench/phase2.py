"""FB-RENDER-01 orchestration: independent, headless Vulkan compute workload.

This module never equates a compute dispatch with rasterization hardware VRS.
It permits standalone execution alongside FB-GAZE-01 without shared output state.
The C++ binary owns Vulkan initialization and timestamp queries.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys

REQUIRED = ("timestamp_ns", "truth_x", "truth_y", "used_x", "used_y", "valid")

def non_overwrite(path: Path):
    if path.exists():
        raise FileExistsError(f"Existing experimental evidence cannot be overwritten: {path}")

def valid_uv(value: str) -> float:
    n = float(value)
    if not (math.isfinite(n) and 0 <= n <= 1):
        raise ValueError(f"Gaze UV must be finite and in [0, 1], got {value!r}")
    return n

def make_trace(target: Path, frames: int = 36, hz: int = 90):
    """Calibrated? NO. Procedural gaze only; explicit label in provenance."""
    if frames < 4 or frames > 100000 or hz < 1 or hz > 2000:
        raise ValueError("Invalid trace parameters")
    non_overwrite(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(REQUIRED)
        for i in range(frames):
            t = i / hz
            x = .50 + .30 * math.sin(2 * math.pi * .65 * t)
            y = .50 + .12 * math.sin(2 * math.pi * .33 * t)
            # Jump halfway through, to expose prediction lag (NOT physiological model).
            if i >= frames // 2:
                x = .72 if i % 2 == 0 else .26
            w.writerow((round(i * 1e9 / hz), x, y, x, y, 1))
    return target

def export_phase1(path: Path, output: Path, condition: str, predictor: str,
                  trace_id: str, fallback: str = "reject"):
    """Export exactly one causal predictor condition from FB-GAZE-01 frames.

    Predictions are from the recorded phase1 benchmark output, not recomputed
    using future gaze. A missing prediction needs an explicit fallback policy.
    """
    non_overwrite(output)
    if fallback not in ("reject", "center", "hold"):
        raise ValueError("Invalid fallback")
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    last = None
    last_time = -1
    temporary = output.with_name(output.name + ".partial")
    non_overwrite(temporary)
    try:
        count = _export_phase1_impl(path, temporary, condition, predictor, trace_id, fallback)
        if not count:
            raise ValueError("No rows matched the specified condition/predictor/trace_id")
        temporary.replace(output)
        return count
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

def _export_phase1_impl(path, output, condition, predictor, trace_id, fallback):
    count=0
    last=None
    last_time=-1
    with path.open(newline="") as src, output.open("w", newline="") as dst:
        reader = csv.DictReader(src)
        req = ("condition", "predictor", "trace_id", "target_ns", "truth_x", "truth_y",
               "pred_x", "pred_y", "has_prediction")
        if not set(req).issubset(set(reader.fieldnames or [])):
            raise ValueError("This is not a valid Phase 1 frames.csv")
        writer = csv.writer(dst)
        writer.writerow(REQUIRED)
        for row in reader:
            if (row["condition"], row["predictor"], row["trace_id"]) != (condition, predictor, trace_id):
                continue
            t = int(row["target_ns"])
            if t <= last_time:
                raise ValueError("Out-of-order or duplicate Phase 1 timestamps")
            last_time=t
            x, y = valid_uv(row["truth_x"]), valid_uv(row["truth_y"])
            has_prediction = row["has_prediction"].lower() in ("true", "1")
            if has_prediction:
                px,py=valid_uv(row["pred_x"]), valid_uv(row["pred_y"])
                last=(px,py)
            elif fallback == "center":
                px,py=(.5,.5)
            elif fallback == "hold" and last is not None:
                px,py=last
            else:
                raise ValueError("Missing gaze predictions: select explicit --fallback hold|center")
            writer.writerow((t,x,y,px,py,1))
            count += 1
    return count

def percentile(data: list[float], q: float) -> float:
    ordered=sorted(data)
    if len(ordered)==1: return ordered[0]
    pos=(len(ordered)-1)*q/100
    low=math.floor(pos); high=math.ceil(pos)
    return ordered[low]*(high-pos)+ordered[high]*(pos-low) if low!=high else ordered[low]

def analyze(run_dir: Path):
    raw=run_dir/"frames.csv"
    manifest=run_dir/"manifest.json"
    if not raw.is_file() or not manifest.is_file():
        raise ValueError("Missing native Vulkan evidence")
    m=json.loads(manifest.read_text())
    groups={}
    with raw.open(newline="") as file:
        for row in csv.DictReader(file):
            key=(row["scene"],row["policy"])
            groups.setdefault(key,[]).append(row)
    if not groups: raise ValueError("Native result has zero frames")
    out=[]
    for (scene, policy),rows in sorted(groups.items()):
        t=[float(r["device_dispatch_ms"]) for r in rows if r["device_dispatch_ms"]]
        x={"scene":scene,"policy":policy,"frames":len(rows),
           "device_time_available":bool(t),
           "mean_device_dispatch_ms":statistics.mean(t) if t else "",
           "p50_device_dispatch_ms":percentile(t,50) if t else "",
           "p95_device_dispatch_ms":percentile(t,95) if t else "",
           "p99_device_dispatch_ms":percentile(t,99) if t else "",
           "mean_weighted_mse":statistics.mean(float(r["weighted_mse"]) for r in rows),
           "mean_foveal_mse":statistics.mean(float(r["foveal_mse"]) for r in rows),
           "mean_sample_fraction_proxy":statistics.mean(float(r["sample_fraction_proxy"]) for r in rows)}
        out.append(x)
    with (run_dir/"summary.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]))
        w.writeheader();w.writerows(out)
    mode=m["results_class"]
    report=["# FB-RENDER-01 native Vulkan compute report", "",
            f"- Device: {m['device_name']}", f"- Results class: **{mode}**",
            f"- Timestamp queries: {'AVAILABLE' if m.get('timestamp_query_available', False) else 'UNSUPPORTED'}",
            "- This is a **compute shader image-space approximation**; every pixel dispatches.",
            "- This is not fragment shading rate (VRS), not a scene-level render benchmark,",
            "  and does not quantify headset performance or motion-to-photon latency.",
            "- 'Sample fraction' is a theoretical pixel-block proxy, NOT counted GPU invocations.",
            "- GPU timestamp brackets only the compute dispatch; no frame/presentation inference.","",
            "| Scene | Policy | Frames | Dispatch P95 (ms) | Weighted MSE | Sample proxy |",
            "|---|---|---:|---:|---:|---:|"]
    for r in out:
        tm=f"{r['p95_device_dispatch_ms']:.5f}" if r["device_time_available"] else "unsupported"
        report.append(f"| {r['scene']} | {r['policy']} | {r['frames']} | {tm} | {r['mean_weighted_mse']:.3f} | {r['mean_sample_fraction_proxy']:.4f} |")
    (run_dir/"report.md").write_text("\n".join(report)+"\n")
    m["trace_sha256"]=hashlib.sha256((run_dir/"trace.csv").read_bytes()).hexdigest() if (run_dir/"trace.csv").exists() else None
    m["host_python_version"]=sys.version.split()[0]
    m["reports_generated_at_utc"]=datetime.now(timezone.utc).isoformat()
    m["scientific_qualification"]={
        "software_vulkan": mode=="software-vulkan-functional",
        "hardware_gpu_measured_dispatch": mode=="native-vulkan-compute-technical" and bool(out[0]["device_time_available"]),
        "real_fragment_vrs":False,
        "human_validated":False,
    }
    manifest.write_text(json.dumps(m,indent=2)+"\n")
    return out

def run_native(repo: Path, output: Path, trace: Path, *, frames:int=24,
               width:int=128,height:int=72,require_hardware:bool=False,build_dir:Path|None=None,
               capture_every:int=0):
    non_overwrite(output)
    if not trace.exists():raise FileNotFoundError(trace)
    native=repo/"native"/"vulkan_compute"
    build=build_dir or repo/"build"/"fb-vulkan"
    subprocess.run(["cmake","-S",str(native),"-B",str(build),"-DCMAKE_BUILD_TYPE=Release"],check=True)
    subprocess.run(["cmake","--build",str(build),"--parallel","2"],check=True)
    shader=build/"foveation.comp.spv"
    binary=build/"fb_vk_compute"
    import shutil
    # Native binary creates output after validation. Store the exact trace it consumed.
    cmd=[str(binary),"--shader",str(shader),"--trace",str(trace),
         "--output",str(output),"--frames",str(frames),"--width",str(width),"--height",str(height)]
    if capture_every<0:raise ValueError("capture_every must be >=0")
    if capture_every:cmd.extend(["--capture-every",str(capture_every)])
    if require_hardware:cmd.append("--require-hardware")
    subprocess.run(cmd,check=True)
    shutil.copyfile(trace,output/"trace.csv")
    return analyze(output)

def cli():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("make-trace",help="Independent synthetic input trace for concurrent tracks")
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--frames",type=int,default=36)
    a.add_argument("--hz",type=int,default=90)
    b=sub.add_parser("export-phase1",help="Use a real Phase 1 predictor output as Phase 2 input")
    for key in ("input","output"):b.add_argument("--"+key,type=Path,required=True)
    for key in ("condition","predictor","trace-id"):b.add_argument("--"+key,required=True)
    b.add_argument("--fallback",choices=("reject","center","hold"),default="reject")
    c=sub.add_parser("run",help="Compile GLSL/C++ and run actual Vulkan compute dispatch")
    c.add_argument("--output",type=Path,required=True)
    c.add_argument("--trace",type=Path,required=True)
    c.add_argument("--frames",type=int,default=24)
    c.add_argument("--width",type=int,default=128)
    c.add_argument("--height",type=int,default=72)
    c.add_argument("--require-hardware",action="store_true")
    c.add_argument("--capture-every",type=int,default=0,help="0 captures legacy sparse scientific frames; N captures each Nth frame")
    d=sub.add_parser("analyze",help="Rebuild summaries from existing native evidence")
    d.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.action=="make-trace":
        print(f"Trace generated: {make_trace(args.output,args.frames,args.hz)}")
    if args.action=="export-phase1":
        print("Exported",export_phase1(args.input,args.output,args.condition,args.predictor,
                                       args.trace_id,args.fallback),"frames")
    if args.action=="run":
        repo=Path(__file__).resolve().parent.parent
        rows=run_native(repo,args.output,args.trace,frames=args.frames,width=args.width,
                        height=args.height,require_hardware=args.require_hardware,
                        capture_every=args.capture_every)
        print(f"FB-RENDER-01: analyzed {len(rows)} policy x scene conditions -> {args.output}")
    if args.action=="analyze":
        print(f"Summarized {len(analyze(args.output))} conditions")

if __name__=="__main__": cli()
