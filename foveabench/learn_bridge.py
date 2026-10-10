"""FB-LEARN-RENDER: audited, paired neural-prediction-to-Vulkan comparison.

This is EXPLORATORY analysis of synthetic held-out gaze, never a newly sealed
test of a subsequent trained model. Native timing is not hardware speed evidence
when the Vulkan physical device is software (Mesa llvmpipe).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from tqdm.auto import tqdm

from . import phase2

SCHEMES = ("hold", "velocity", "learned")
MOTIONS = ("fixation", "pursuit", "jump")


def csv_rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def fingerprint(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def prepare(ml_output:Path, output:Path, condition:str, max_frames:int):
    if output.exists():
        raise FileExistsError(f"Refuse overwrite: {output}")
    if max_frames != 0 and max_frames < 8:
        raise ValueError("max_frames must be 0 (all) or >=8")
    input_file=ml_output/"test_predictions.csv"
    model_file=ml_output/"model.npz"
    model_manifest_file=ml_output/"manifest.json"
    if not (input_file.is_file() and model_file.is_file() and model_manifest_file.is_file()):
        raise FileNotFoundError("Require complete trained output: test_predictions.csv, model.npz and manifest.json")
    original=json.loads(model_manifest_file.read_text())
    if original.get("suite")!="FB-LEARN-01/1.0":
        raise ValueError("Model manifest version mismatch")
    expected={"condition","trace_id","timestamp_ns","subject_id","truth_x","truth_y",
              "hold_x","hold_y","velocity_x","velocity_y","learned_x","learned_y"}
    by_motion=defaultdict(lambda:defaultdict(list))
    print(f"[PREPARE] Reading {input_file}",flush=True)
    seen=set()
    with input_file.open(newline="") as f:
        r=csv.DictReader(f)
        if not expected.issubset(r.fieldnames or []):
            raise ValueError("Trained test_predictions.csv missing required headers")
        for row in tqdm(r,desc="Indexing held-out predictions",unit="frames"):
            if row["condition"]!=condition:continue
            motion=next((m for m in MOTIONS if row["trace_id"].startswith("synthetic-"+m+"-")),None)
            if motion is None:continue
            key=(row["trace_id"],row["timestamp_ns"])
            if key in seen:
                raise ValueError(f"Duplicate timestamp: {key}")
            seen.add(key)
            by_motion[motion][row["trace_id"]].append(row)
    selected={}
    for motion in MOTIONS:
        if not by_motion[motion]:
            raise ValueError(f"No held-out {motion!r} trace for {condition}")
        trace_id=sorted(by_motion[motion])[0]
        rows=sorted(by_motion[motion][trace_id],key=lambda r:int(r["timestamp_ns"]))
        if max_frames:rows=rows[:max_frames]
        if len(rows)<8:
            raise ValueError(f"Insufficient paired eligible frames for {trace_id}")
        subject_set={r["subject_id"] for r in rows}
        if len(subject_set)!=1:
            raise ValueError("Multiple identities within selected trace")
        last=-1
        for row in rows:
            t=int(row["timestamp_ns"])
            if t<=last:
                raise ValueError(f"Nonmonotonic held-out time: {trace_id}")
            last=t
            for field in ("truth_x","truth_y",*(p+"_"+axis for p in SCHEMES for axis in ("x","y"))):
                phase2.valid_uv(row[field])
        selected[motion]=dict(trace_id=trace_id,subject_id=rows[0]["subject_id"],frames=len(rows),rows=rows)
        print(f"[PREPARE] {motion:8s}: {trace_id}, {len(rows)} paired frames",flush=True)
    output.mkdir(parents=True)
    traces=output/"traces"
    traces.mkdir()
    for motion,info in tqdm(selected.items(),desc="Exporting aligned traces",unit="motion"):
        for scheme in SCHEMES:
            path=traces/f"{motion}-{scheme}.csv"
            with path.open("w",newline="") as f:
                w=csv.writer(f)
                w.writerow(phase2.REQUIRED)
                for row in info["rows"]:
                    w.writerow((int(row["timestamp_ns"]),row["truth_x"],row["truth_y"],
                                row[scheme+"_x"],row[scheme+"_y"],1))
    evidence={"suite":"FB-LEARN-RENDER/1.0",
              "prediction_source_sha256":fingerprint(input_file),
              "model_checkpoint_sha256":fingerprint(model_file),
              "model_manifest_sha256":fingerprint(model_manifest_file),
              "condition":condition,
              "selection":"one lexicographically-first held-out synthetic trace per movement, all eligible paired frames",
              "data_partition":"TRAINED MODEL HELD-OUT TEST; exploratory re-use, NOT a fresh sealed external test",
              "source_trained_on_synthetic_only":original["synthetic_only"],
              "trace_counts":{m:{k:v for k,v in info.items() if k!="rows"} for m,info in selected.items()},
              "models":list(SCHEMES),
              "hardware_raster_vrs":False,"human_validated":False,
              "warning":"Do not use this test partition for tuning then call it independent final confirmation"}
    (output/"manifest.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(f"[READY] {output} (9 aligned renderer inputs); checkpoint SHA256 {evidence['model_checkpoint_sha256'][:16]}...",flush=True)
    return evidence


def analyze(prepared:Path):
    metadata=json.loads((prepared/"manifest.json").read_text())
    stats=[]
    frame_rows=[]
    device_classes=set()
    for motion in MOTIONS:
        reference={}
        for scheme in SCHEMES:
            run=prepared/"render"/f"{motion}-{scheme}"
            m=json.loads((run/"manifest.json").read_text())
            device_classes.add(m["results_class"])
            if m.get("full_reference_pixel_mismatch_max",1)!=0:
                raise ValueError(f"Full-reference rendering mismatch: {run}")
            rows=csv_rows(run/"frames.csv")
            subset=[r for r in rows if r["policy"]=="tracked"]
            if len(subset)!=2*metadata["trace_counts"][motion]["frames"]:
                raise ValueError(f"Unexpected frame count: {run}")
            points={}
            for row in subset:
                key=(row["scene"],int(row["frame_index"]))
                if key in points:raise ValueError("Duplicate output frame")
                points[key]=row
            if scheme=="hold":reference=points
            else:
                if points.keys()!=reference.keys():
                    raise ValueError("Nonpaired renderer frame identities")
                for k,r in points.items():
                    ref=reference[k]
                    if any(r[f]!=ref[f] for f in ("timestamp_ns","truth_x","truth_y")):
                        # String formatting of floats is deterministic within one native program.
                        raise ValueError(f"Unpaired true gaze / timestamp: {motion} {scheme} {k}")
            for scene in ("chirp","edges"):
                seq=[r for k,r in points.items() if k[0]==scene]
                if not seq:raise ValueError(f"Missing scene: {scene}")
                mse=[float(r["weighted_mse"]) for r in seq]
                fovea=[float(r["foveal_mse"]) for r in seq]
                record={"movement":motion,"scene":scene,"model":scheme,"frames":len(seq),
                        "weighted_mse_mean":statistics.mean(mse),"weighted_mse_p95":phase2.percentile(mse,95),
                        "foveal_mse_mean":statistics.mean(fovea)}
                if scheme!="hold":
                    comparable=[(float(points[k]["weighted_mse"]),float(reference[k]["weighted_mse"]))
                                for k in sorted(points) if k[0]==scene]
                    record["better_frames"]=sum(a < b-1e-9 for a,b in comparable)
                    record["worse_frames"]=sum(a > b+1e-9 for a,b in comparable)
                    record["tied_frames"]=len(comparable)-record["better_frames"]-record["worse_frames"]
                    for (k, (v,h)) in zip([k for k in sorted(points) if k[0]==scene], comparable):
                        frame_rows.append({"movement":motion,"scene":scene,"model":scheme,
                                           "frame_index":k[1],"hold_mse":h,
                                           "candidate_mse":v,"delta_mse_candidate_minus_hold":v-h})
                else:
                    record.update(better_frames=0,worse_frames=0,tied_frames=len(seq))
                stats.append(record)
    if len(device_classes)!=1:raise ValueError("Different Vulkan device classifications across runs")
    for row in stats:
        base=next(a for a in stats if a["movement"]==row["movement"] and
                  a["scene"]==row["scene"] and a["model"]=="hold")
        row["relative_reduction_vs_hold_pct"]=(base["weighted_mse_mean"]-row["weighted_mse_mean"])/base["weighted_mse_mean"]*100 if base["weighted_mse_mean"] else 0.0
    with (prepared/"comparison.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
    with (prepared/"paired_frame_errors.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(frame_rows[0]));w.writeheader();w.writerows(frame_rows)
    lines=["# FB-LEARN-RENDER: learned gaze to native Vulkan", "",
           "- Same held-out synthetic trace, timestamps and true gaze for all three predictors.",
           "- These are exploratory results on already examined test identities; NOT a fresh final generalization test.",
           "- Weighted MSE is an uncalibrated engineering image proxy, NOT a psychophysical perception metric.",
           f"- Vulkan classification: **{next(iter(device_classes))}**. No hardware VRS claim.",
           "- Per-run dispatch timing is not comparable as a GPU speedup (serial software Vulkan runs).",
           "- Missing predictions are excluded identically for every predictor; reported frames are eligible pairs only.","",
           "| Movement | Scene | Predictor | Frames | Weighted MSE | Δ vs hold | Better / Worse / Tied frames |",
           "|---|---|---|---:|---:|---:|---|"]
    for row in stats:
        lines.append(f"| {row['movement']} | {row['scene']} | {row['model']} | {row['frames']} | "
                     f"{row['weighted_mse_mean']:.3f} | {row['relative_reduction_vs_hold_pct']:+.2f}% | "
                     f"{row['better_frames']} / {row['worse_frames']} / {row['tied_frames']} |")
    (prepared/"report.md").write_text("\n".join(lines)+"\n")
    metadata["renderer_result_classes"]=list(device_classes)
    metadata["rendering_evaluated"]=True
    (prepared/"manifest.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print("\n".join(lines),flush=True)
    return stats


def render(prepared:Path,width:int,height:int):
    manifest_path=prepared/"manifest.json"
    if not manifest_path.is_file():raise FileNotFoundError("Run prepare first")
    metadata=json.loads(manifest_path.read_text())
    if metadata.get("suite")!="FB-LEARN-RENDER/1.0":
        raise ValueError("Unknown prepared manifest")
    if (prepared/"render").exists():
        raise FileExistsError("Rendering already begun: refusing overwrite")
    if width<16 or height<16:raise ValueError("Image resolution must be >=16 in both axes")
    (prepared/"render").mkdir()
    repo=Path(__file__).resolve().parent.parent
    jobs=[(motion,scheme,metadata["trace_counts"][motion]["frames"]) for motion in MOTIONS for scheme in SCHEMES]
    for motion,scheme,frames in tqdm(jobs,desc="Native Vulkan gaze comparisons",unit="workload",dynamic_ncols=True):
        trace=prepared/"traces"/f"{motion}-{scheme}.csv"
        out=prepared/"render"/f"{motion}-{scheme}"
        tqdm.write(f"[VULKAN] Starting {motion}/{scheme}: {frames} gaze frames, {frames*8} compute dispatches")
        phase2.run_native(repo,out,trace,frames=frames,width=width,height=height)
        tqdm.write(f"[VULKAN] PASS {motion}/{scheme}: {frames*8} dispatches. Output: {out}")
    result=analyze(prepared)
    print(f"[DONE] {len(jobs)} renderer runs; {sum(j[2]*8 for j in jobs):,} Vulkan compute dispatches",flush=True)
    print(f"[DONE] Report: {prepared/'report.md'}",flush=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("prepare",help="Create paired held-out gaze traces for three predictor models")
    a.add_argument("--ml-output",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    a.add_argument("--condition",default="latency-60")
    a.add_argument("--max-frames",type=int,default=0,help="0=all eligible frames; for fast CI allow 24")
    b=sub.add_parser("render",help="Run nine native Vulkan workloads with tqdm and paired analysis")
    b.add_argument("--prepared",required=True,type=Path)
    b.add_argument("--width",type=int,default=128)
    b.add_argument("--height",type=int,default=72)
    args=p.parse_args()
    if args.action=="prepare":prepare(args.ml_output,args.output,args.condition,args.max_frames)
    else:render(args.prepared,args.width,args.height)


if __name__=="__main__":
    main()
