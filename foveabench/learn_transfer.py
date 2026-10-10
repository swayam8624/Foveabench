"""FB-LEARN-TRANSFER: inspect learned gating and evaluate on *new* synthetic agent IDs.

This is a strict, frozen-checkpoint transfer assessment. No weights or
thresholds are fitted on the incoming data; source test metrics are not
substitutes for new observations. No human generalization is implied.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
from collections import defaultdict
import numpy as np
from tqdm.auto import tqdm
from .learn import load_pairs, net, metrics

EXPECTED_FEATURES = ("hold_x","hold_y","velocity_dx","velocity_dy","disagreement",
                     "age_100ms","sample_count_10","past_hold_dx_10","past_hold_dy_10")
SCHEMES = ("hold","velocity","learned")


def csv_write(path, rows):
    if not rows:
        raise ValueError("Refusing empty evidence file")
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def checkpoint(ml_dir):
    source=ml_dir/"model.npz"
    manifest_file=ml_dir/"manifest.json"
    partition=ml_dir/"splits.csv"
    if not all(p.is_file() for p in (source,manifest_file,partition)):
        raise FileNotFoundError("Need model.npz, manifest.json and splits.csv")
    manifest=json.loads(manifest_file.read_text())
    if manifest.get("suite")!="FB-LEARN-01/1.0":
        raise ValueError("Unrecognized trained checkpoint")
    with np.load(source,allow_pickle=False) as m:
        params=[m[n].copy() for n in ("w1","b1","w2","b2")]
        means=m["mean"].copy()
        scales=m["std"].copy()
        names=tuple(str(n) for n in m["features"])
    if names!=EXPECTED_FEATURES or means.shape!=(9,) or scales.shape!=(9,):
        raise ValueError("Model input schema mismatch")
    if params[0].shape[0]!=9 or params[0].shape[1]!=len(params[1]) or params[2].shape!=(len(params[1]),1):
        raise ValueError("Invalid neural checkpoint shapes")
    if not np.isfinite(np.concatenate([*map(lambda x:x.ravel(),params),means,scales])).all() or (scales<=0).any():
        raise ValueError("Invalid or nonfinite checkpoint values")
    known=set()
    with partition.open(newline="") as partition_file:
        for row in csv.DictReader(partition_file):
            if row["subject_id"] in known:
                raise ValueError("Duplicate subject in training partitions")
            known.add(row["subject_id"])
    if not known:
        raise ValueError("Missing original identity register")
    return params,means,scales,known,manifest,source


def inspection(args):
    p=args.ml_output/"test_predictions.csv"
    if not p.is_file():
        raise FileNotFoundError(p)
    records=defaultdict(list)
    with p.open(newline="") as f:
        r=csv.DictReader(f)
        required={"condition","trace_id","subject_id"}
        columns=set(r.fieldnames or ())
        if not required.issubset(columns):
            raise ValueError("Missing learned prediction audit fields")
        # FB-LEARN-01 uses blend_weight; FB-LEARN-TRANSFER uses velocity_weight.
        # Do not require only one spelling or re-train a checkpoint to inspect it.
        weight_field=next((name for name in ("blend_weight","velocity_weight") if name in columns),None)
        if weight_field is None:
            raise ValueError("Missing blend_weight or velocity_weight in predictions")
        print(f"[INSPECT] Using saved inference column {weight_field}; no training or model modification",flush=True)
        for row in tqdm(r,desc="Examining frozen neural actions",unit="frames"):
            try:
                weight=float(row[weight_field])
            except (ValueError,TypeError):
                raise ValueError(f"Invalid policy weight at row {r.line_num}") from None
            if not np.isfinite(weight) or weight<0 or weight>1:
                raise ValueError(f"Invalid policy blending weight at row {r.line_num}")
            motion=row["trace_id"].rsplit("-",1)[0]
            records["ALL"].append(weight)
            records[motion].append(weight)
    if not records["ALL"]:
        raise ValueError("Empty learned prediction audit")
    print("\n=== NEURAL CONTROLLER: HOW OFTEN DOES IT TRUST VELOCITY? ===")
    for kind,w in sorted(records.items()):
        a=np.asarray(w)
        print(f"{kind:24s} n={len(a):>6,} | mean_alpha={a.mean():.5f} "
              f"| p50={np.median(a):.5f} | p90={np.quantile(a,.9):.5f} "
              f"| weight<0.05={(a<.05).mean():.1%} | weight>0.50={(a>.5).mean():.1%}")
    print("An alpha of 0 means hold; 1 means unrestricted velocity; this is diagnostic on a previously seen test set.")
    return records


def evaluate(args):
    if args.output.exists():
        raise FileExistsError(f"Refuse overwriting experimental evidence: {args.output}")
    params,mean,std,known,model_manifest,model_path=checkpoint(args.ml_output)
    inputhash=hashlib.sha256(args.phase1_frames.read_bytes()).hexdigest()
    if inputhash==model_manifest.get("sha256_input"):
        raise ValueError("This is the original model training source. Supply a new Phase 1 run")
    X,H,V,Y,identities,motions,keys,excluded=load_pairs(args.phase1_frames)
    unique=set(identities)
    fresh=sorted(unique-known)
    overlap=sorted(unique & known)
    if not fresh:
        raise ValueError("No genuinely unused synthetic identity labels: generate a profile with synthetic_sessions_per_kind >=5")
    if not args.allow_seen:
        include=np.flatnonzero(np.isin(identities,fresh))
    else:
        include=np.arange(len(identities))
    print(f"[EVALUATE] New identities: {len(fresh)}, previously used identities: {len(overlap)}",flush=True)
    print(f"[EVALUATE] Fresh-only eligible frames: {int(np.sum(np.isin(identities,fresh))):,}",flush=True)
    if len(include)<100:
        raise ValueError("Too few observations after ID disjointness filter")
    Z=np.clip((X[include]-mean)/std,-15,15)
    _,alpha=net(Z,params)
    P=H[include]+alpha[:,None]*(V[include]-H[include])
    targets=Y[include]
    movement=motions[include]
    subj=identities[include]
    groups=[("ALL",np.ones(len(include),dtype=bool))]
    groups.extend((m,movement==m) for m in sorted(set(movement)))
    results=[]
    for name,mask in tqdm(groups,desc="Held-out transfer metrics",unit="group"):
        for model,points in (("hold",H[include][mask]),("velocity",V[include][mask]),("learned",P[mask])):
            m=metrics(points,targets[mask])
            results.append({"movement":name,"model":model,"frames":len(points),**m})
    args.output.mkdir(parents=True)
    csv_write(args.output/"comparison.csv",results)
    detailed=[]
    for j,i in enumerate(tqdm(include,desc="Exporting frozen-checkpoint predictions",unit="frames")):
        detailed.append({"condition":keys[i][0],"trace_id":keys[i][1],"timestamp_ns":keys[i][2],
                         "subject_id":identities[i],"truth_x":Y[i,0],"truth_y":Y[i,1],
                         "hold_x":H[i,0],"hold_y":H[i,1],
                         "velocity_x":V[i,0],"velocity_y":V[i,1],
                         "learned_x":P[j,0],"learned_y":P[j,1],
                         "velocity_weight":alpha[j]})
    csv_write(args.output/"test_predictions.csv",detailed)
    fields={"suite":"FB-LEARN-TRANSFER/1.0",
        "source_checkpoint_sha256":hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "source_training_sha256":model_manifest.get("sha256_input"),
        "evaluation_frames_sha256":inputhash,
        "input":str(args.phase1_frames),
        "synthetic_only":True,
        "fresh_identity_count":len(fresh),
        "previously_seen_identity_labels_excluded":len(overlap) if not args.allow_seen else 0,
        "fresh_evaluation_identities":fresh,
        "eligible_frame_pairs":len(include),
        "excluded_unavailable_pairs_global":excluded,
        "checkpoint_frozen":True,
        "trained_model_epoch":model_manifest.get("best_epoch"),
        "evaluated_previous_identities":bool(args.allow_seen),
        "training":"NO NEW TRAINING; frozen checkpoint inference",
        "real_human_validation":False,
        "new_procedural_family":"NO. Same fixation/pursuit/jump synthetic generator with new seed and disjoint pseudonyms.",
        "status":"exploratory evaluation; does not establish real human population generalization"}
    (args.output/"manifest.json").write_text(json.dumps(fields,indent=2)+"\n")
    lines=["# FB-LEARN-TRANSFER: frozen neural policy on new synthetic identities","",
        f"- Fresh pseudonymous agents: {len(fresh)}; paired valid model frames: {len(include):,}.",
        f"- Source gaze file fingerprint: {inputhash}.",
        f"- Original checkpoint: epoch {model_manifest.get('best_epoch')}; **weights frozen**.",
        "- Existing training/validation/test IDs are excluded automatically.",
        "- No human validation. New synthetic seeds are not independent physiological populations.",
        "- Same synthetic generator; this assesses limited within-generator robustness.",
        "- No new training or policy tuning occurs in this evaluation.",
        "",
        "| Motion | Policy | Frames | Mean gaze angle (°) | P95 (°) | Miss 5° |",
        "|---|---|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['movement']} | {r['model']} | {r['frames']} | "
                     f"{r['mean_angle_deg']:.4f} | {r['p95_angle_deg']:.4f} | {r['miss_5deg']:.2%} |")
    (args.output/"report.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines),flush=True)
    print(f"[DONE] Transfer results: {args.output} | model SHA {fields['source_checkpoint_sha256'][:16]}...",flush=True)
    return fields


def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="action",required=True)
    a=s.add_parser("inspect",help="Report how much the trained controller trusts velocity")
    a.add_argument("--ml-output",type=Path,required=True)
    b=s.add_parser("evaluate",help="Frozen model on NEW subject-ID synthetic Phase 1 evidence")
    b.add_argument("--ml-output",type=Path,required=True)
    b.add_argument("--phase1-frames",type=Path,required=True)
    b.add_argument("--output",type=Path,required=True)
    b.add_argument("--allow-seen",action="store_true",help="Debug only: include training IDs, not a held-out assessment")
    x=p.parse_args()
    if x.action=="inspect":inspection(x)
    else:evaluate(x)

if __name__=="__main__":
    main()
