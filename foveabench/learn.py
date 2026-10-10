"""FB-LEARN-01: train a real causal neural gate on paired Phase 1 predictions.
This is supervised learning, NOT reinforcement learning or human validation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from tqdm.auto import tqdm

FEATURES = ("hold_x","hold_y","velocity_dx","velocity_dy","disagreement",
            "age_100ms","sample_count_10","past_hold_dx_10","past_hold_dy_10")

def load_pairs(path):
    paired = defaultdict(dict)
    cols = {"condition","predictor","trace_id","subject_id","target_ns",
            "truth_x","truth_y","pred_x","pred_y","has_prediction","age_ms","delivered_samples"}
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if not cols.issubset(reader.fieldnames or []):
            raise ValueError("Expected canonical Phase 1 frames.csv")
        for row in tqdm(reader,desc="Loading causal predictions",unit="rows"):
            if row["predictor"] not in ("hold","velocity"):
                continue
            key = (row["condition"],row["trace_id"],int(row["target_ns"]))
            if row["predictor"] in paired[key]:
                raise ValueError(f"Duplicate predictor: {key}")
            paired[key][row["predictor"]] = row
    x,h,v,y,subjects,motions,keys = [],[],[],[],[],[],[]
    prior = {}
    unavailable = 0
    for key, pair in tqdm(sorted(paired.items()),desc="Pairing observations",unit="frames"):
        if set(pair) != {"hold","velocity"}:
            raise ValueError(f"Unpaired baseline outputs: {key}")
        a,b = pair["hold"],pair["velocity"]
        if a["subject_id"] != b["subject_id"] or a["truth_x"] != b["truth_x"] or a["truth_y"] != b["truth_y"]:
            raise ValueError(f"Ground truth / subject mismatch: {key}")
        if a["has_prediction"].lower() not in ("true","1") or b["has_prediction"].lower() not in ("true","1"):
            unavailable += 1
            continue
        pa = np.array([float(a["pred_x"]),float(a["pred_y"])])
        pb = np.array([float(b["pred_x"]),float(b["pred_y"])])
        truth = np.array([float(a["truth_x"]),float(a["truth_y"])])
        values = np.r_[pa,pb,truth]
        if not np.isfinite(values).all() or (values < 0).any() or (values > 1).any():
            raise ValueError(f"Invalid gaze coordinates: {key}")
        age = float(a["age_ms"])
        count = int(a["delivered_samples"])
        if not math.isfinite(age) or age < 0 or count < 0:
            raise ValueError(f"Invalid observation age/count: {key}")
        seq = (key[0],key[1])
        dp = pa-prior[seq] if seq in prior else np.zeros(2)
        prior[seq] = pa
        diff = pb-pa
        features = [pa[0],pa[1],diff[0],diff[1],np.linalg.norm(diff),
                    age/100.0,min(count,100)/10.0,dp[0]*10,dp[1]*10]
        x.append(features);h.append(pa);v.append(pb);y.append(truth)
        subjects.append(a["subject_id"])
        motions.append(key[1].rsplit("-",1)[0] if key[1].startswith("synthetic-") else "recorded")
        keys.append(key)
    if len(x)<100:
        raise ValueError("Not enough paired frames for model fitting")
    print(f"[DATA] {len(x):,} matched usable frames; {unavailable:,} missing predictions excluded",flush=True)
    return (np.asarray(x,dtype=np.float64),np.asarray(h),np.asarray(v),np.asarray(y),
            np.asarray(subjects),np.asarray(motions),keys,unavailable)

def split_subjects(subjects,motions,seed):
    # Motion stratification is used for procedural recordings only.
    person_kind = {}
    for s,m in zip(subjects,motions):
        if s in person_kind and person_kind[s]!=m:
            raise ValueError("Inconsistent movement stratum per identity")
        person_kind[s]=m
    strata = defaultdict(list)
    for s,m in person_kind.items():
        strata[m].append(s)
    if any(len(g)<3 for g in strata.values()):
        strata = {"mixed":list(person_kind)}
    rng=np.random.default_rng(seed)
    assignment={}
    for kind, members in sorted(strata.items()):
        members=sorted(members);rng.shuffle(members)
        n=len(members)
        if n<3:raise ValueError("Need >=3 disjoint identities")
        nv=max(1,round(.2*n));nt=max(1,round(.2*n))
        if nv+nt>=n:nv=nt=1
        for i,s in enumerate(members):
            assignment[s]="train" if i<n-nv-nt else "validation" if i<n-nt else "test"
    split=np.array([assignment[s] for s in subjects])
    assert set(subjects[split=="train"]).isdisjoint(set(subjects[split=="test"]))
    assert set(subjects[split=="train"]).isdisjoint(set(subjects[split=="validation"]))
    assert set(subjects[split=="test"]).isdisjoint(set(subjects[split=="validation"]))
    return split,assignment

def net(x,weights):
    w1,b1,w2,b2=weights
    hidden=np.tanh(x@w1+b1)
    z=np.clip((hidden@w2+b2).ravel(),-25,25)
    alpha=1/(1+np.exp(-z))
    return hidden,alpha

def angles(p,q):
    # Same documented 90deg rectilinear camera as Phase 1, NOT HMD calibrated.
    a=np.column_stack([2*p[:,0]-1,1-2*p[:,1],np.ones(len(p))])
    b=np.column_stack([2*q[:,0]-1,1-2*q[:,1],np.ones(len(q))])
    a/=np.linalg.norm(a,axis=1)[:,None];b/=np.linalg.norm(b,axis=1)[:,None]
    return np.rad2deg(np.arccos(np.clip((a*b).sum(axis=1),-1,1)))

def metrics(p,q):
    err=angles(p,q)
    return dict(mean_angle_deg=float(np.mean(err)),p95_angle_deg=float(np.percentile(err,95)),
                miss_5deg=float(np.mean(err>5)),uv_mse=float(np.mean(((p-q)**2).sum(axis=1))))

def csv_save(path,rows):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def train(args):
    if args.output.exists():raise FileExistsError("Refusing to overwrite an existing experiment")
    if not 1<=args.epochs<=2000 or args.batch_size<1 or args.lr<=0 or not 2<=args.hidden<=256:
        raise ValueError("Invalid hyperparameters")
    print(f"[START] ML experiment seed={args.seed} epochs={args.epochs} hidden={args.hidden}",flush=True)
    X,H,V,Y,subjects,motions,keys,excluded=load_pairs(args.phase1_frames)
    splits,assignment=split_subjects(subjects,motions,args.seed)
    itr,iv,it=[np.flatnonzero(splits==s) for s in ("train","validation","test")]
    for s,ix in (("TRAIN",itr),("VALIDATION",iv),("TEST",it)):
        print(f"[SPLIT] {s:<10} {len(ix):>6,} frames, {len(set(subjects[ix]))} identities",flush=True)
    mean=X[itr].mean(axis=0);std=X[itr].std(axis=0);std[std<1e-8]=1
    Z=np.clip((X-mean)/std,-15,15)
    diff=V-H
    rng=np.random.default_rng(args.seed)
    weights=[rng.normal(0,.10,(len(FEATURES),args.hidden)),np.zeros(args.hidden),
             rng.normal(0,.10,(args.hidden,1)),np.zeros(1)]
    first=[np.zeros_like(a) for a in weights]
    second=[np.zeros_like(a) for a in weights]
    best=float("inf");best_weights=None;best_epoch=0;stale=0;step=0;history=[]
    print("[MODEL] 9 -> tanh(hidden) -> sigmoid(blend). Prediction = hold + blend*(velocity-hold)",flush=True)
    for epoch in tqdm(range(1,args.epochs+1),desc="Training neural gaze gate",unit="epoch",dynamic_ncols=True):
        permutation=rng.permutation(itr)
        for start in range(0,len(permutation),args.batch_size):
            ix=permutation[start:start+args.batch_size]
            hidden,alpha=net(Z[ix],weights)
            error=H[ix]+alpha[:,None]*diff[ix]-Y[ix]
            ga=(2.0/len(ix))*(error*diff[ix]).sum(axis=1)*alpha*(1-alpha)
            gh=(ga[:,None]@weights[2].T)*(1-hidden**2)
            gradients=[Z[ix].T@gh,gh.sum(axis=0),hidden.T@ga[:,None],np.array([ga.sum()])]
            step+=1
            for j,g in enumerate(gradients):
                first[j]=.9*first[j]+.1*g;second[j]=.999*second[j]+.001*g*g
                weights[j]-=args.lr*(first[j]/(1-.9**step))/(np.sqrt(second[j]/(1-.999**step))+1e-8)
        _,aval=net(Z[iv],weights)
        pv=H[iv]+aval[:,None]*diff[iv]
        vm=metrics(pv,Y[iv])
        _,atr=net(Z[itr],weights)
        train_mse=float(np.mean(((H[itr]+atr[:,None]*diff[itr]-Y[itr])**2).sum(axis=1)))
        improved=vm["uv_mse"]<best-1e-12
        if improved:
            best=vm["uv_mse"];best_weights=[a.copy() for a in weights];best_epoch=epoch;stale=0
        else:stale+=1
        history.append(dict(epoch=epoch,train_uv_mse=train_mse,validation_uv_mse=vm["uv_mse"],
                            validation_mean_angle_deg=vm["mean_angle_deg"],checkpoint_improved=improved))
        tqdm.write(f"[EPOCH {epoch:03d}] train={train_mse:.7f} val={vm['uv_mse']:.7f} "
                   f"val_angle={vm['mean_angle_deg']:.4f}° best_epoch={best_epoch}")
        if stale>=args.patience:
            print(f"[EARLY STOP] no validation improvement for {args.patience} epochs",flush=True)
            break
    assert best_weights is not None
    args.output.mkdir(parents=True)
    csv_save(args.output/"history.csv",history)
    csv_save(args.output/"splits.csv",[{"subject_id":s,"split":v} for s,v in sorted(assignment.items())])
    np.savez_compressed(args.output/"model.npz",w1=best_weights[0],b1=best_weights[1],
                        w2=best_weights[2],b2=best_weights[3],mean=mean,std=std,
                        features=np.asarray(FEATURES))
    with np.load(args.output/"model.npz",allow_pickle=False) as f:
        checkpoint=[f[k] for k in ("w1","b1","w2","b2")]
        testZ=np.clip((X[it]-f["mean"])/f["std"],-15,15)
    _,alpha=net(testZ,checkpoint)
    pred=H[it]+alpha[:,None]*diff[it]
    tests=[]
    for movement in ("ALL",*sorted(set(motions[it]))):
        if movement=="ALL":ix=it;pg=pred
        else:
            ix=it[motions[it]==movement]
            z=np.clip((X[ix]-mean)/std,-15,15)
            _,g=net(z,checkpoint);pg=H[ix]+g[:,None]*diff[ix]
        for name,points in (("hold",H[ix]),("velocity",V[ix]),("learned",pg)):
            m=metrics(points,Y[ix])
            tests.append({"movement":movement,"model":name,"frames":len(ix),**m})
            print(f"[HELD-OUT] {movement:21} {name:8} mean={m['mean_angle_deg']:.4f}° "
                  f"P95={m['p95_angle_deg']:.4f}° miss5={m['miss_5deg']:.2%}",flush=True)
    csv_save(args.output/"test_metrics.csv",tests)
    csv_save(args.output/"test_predictions.csv",[
        {"condition":keys[i][0],"trace_id":keys[i][1],"timestamp_ns":keys[i][2],
         "subject_id":subjects[i],"truth_x":Y[i,0],"truth_y":Y[i,1],
         "hold_x":H[i,0],"hold_y":H[i,1],"velocity_x":V[i,0],"velocity_y":V[i,1],
         "learned_x":pred[j,0],"learned_y":pred[j,1],"blend_weight":alpha[j]}
        for j,i in enumerate(it)])
    original=next(r for r in tests if r["movement"]=="ALL" and r["model"]=="hold")
    learned=next(r for r in tests if r["movement"]=="ALL" and r["model"]=="learned")
    metadata={"suite":"FB-LEARN-01/1.0","source":str(args.phase1_frames),
              "sha256_input":hashlib.sha256(args.phase1_frames.read_bytes()).hexdigest(),
              "synthetic_only":all(str(s).startswith("synthetic-agent-") for s in subjects),
              "training":"supervised gradient descent / Adam; NOT RL","seed":args.seed,
              "best_epoch":best_epoch,"epochs_completed":len(history),"test_pairs":len(it),
              "train_identities":len(set(subjects[itr])),"validation_identities":len(set(subjects[iv])),
              "test_identities":len(set(subjects[it])),"excluded_missing_pairs":excluded,
              "heldout_hold_mean_deg":original["mean_angle_deg"],
              "heldout_learned_mean_deg":learned["mean_angle_deg"],
              "improvement_over_hold":learned["mean_angle_deg"]<original["mean_angle_deg"],
              "human_validated":False,"real_gpu_measured":False}
    (args.output/"manifest.json").write_text(json.dumps(metadata,indent=2)+"\n")
    lines=["# FB-LEARN-01 — supervised neural gaze blending","",
           f"- Best checkpoint: epoch {best_epoch} / {len(history)} epochs.",
           f"- Strictly disjoint train/validation/test identities: {metadata['train_identities']}/{metadata['validation_identities']}/{metadata['test_identities']}.",
           f"- Excluded unavailable candidate pairs: {excluded}.",
           "- Inputs are causal candidate gaze predictions, not gaze ground truth.",
           "- True gaze enters only training loss and held-out evaluation.",
           "- Synthetic only. No human perceptual, ILLIXR or physical GPU validity.",
           "- This is real supervised ML training, not reinforcement learning.","",
           "| Movement | Predictor | Frames | Mean angular error (deg) | P95 (deg) | Miss >5° |",
           "|---|---|---:|---:|---:|---:|"]
    for r in tests:
        lines.append(f"| {r['movement']} | {r['model']} | {r['frames']} | "
                     f"{r['mean_angle_deg']:.4f} | {r['p95_angle_deg']:.4f} | {r['miss_5deg']:.2%} |")
    (args.output/"report.md").write_text("\n".join(lines)+"\n")
    (args.output/"STATUS.md").write_text("# FB-LEARN-01\n\nTraining: PASS\nHeld-out evaluation: PASS\n"
        "Human validation: NOT RUN\nReinforcement learning: NOT IMPLEMENTED\n")
    print(f"[DONE] Trained weights: {args.output/'model.npz'} | report: {args.output/'report.md'}",flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("train")
    a.add_argument("--phase1-frames",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    a.add_argument("--epochs",type=int,default=60)
    a.add_argument("--batch-size",type=int,default=512)
    a.add_argument("--hidden",type=int,default=24)
    a.add_argument("--lr",type=float,default=.003)
    a.add_argument("--patience",type=int,default=20)
    a.add_argument("--seed",type=int,default=20261010)
    args=p.parse_args()
    train(args)

if __name__=="__main__":
    main()
