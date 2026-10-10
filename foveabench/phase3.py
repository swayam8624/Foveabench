"""Phase 3 FB-CAMPAIGN-01: offline gaze-model comparison with held-out identities.

Full-information offline training is NOT RL. This suite uses only the current
Phase 1 prediction records and does not imply perceptual or GPU validity.
"""
from __future__ import annotations
import argparse,collections,csv,hashlib,json,math,random,statistics,subprocess,sys,platform
from pathlib import Path
from datetime import datetime,timezone

VERSION="FB-CAMPAIGN-01/3.0"
COLUMNS={"condition","predictor","trace_id","subject_id","target_ns","has_prediction","angular_error_deg"}
PENALTY=90.0

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def read_data(path):
    """Reject unpaired/inconsistent evidence, not just missing CSV headers."""
    seen=set();mapping={};groups=collections.defaultdict(lambda:[0,0,0.,0.])
    pairs=collections.defaultdict(set)
    n=0
    with path.open(newline="") as f:
        reader=csv.DictReader(f)
        if not COLUMNS.issubset(reader.fieldnames or []):raise ValueError("Invalid Phase 1 evidence headers")
        for row in reader:
            condition,model,trace,person=(row[k] for k in ("condition","predictor","trace_id","subject_id"))
            if not all((condition,model,trace,person)):raise ValueError("Missing identity")
            t=int(row["target_ns"])
            if t<0:raise ValueError("Invalid timestamp")
            key=(condition,model,trace,t)
            if key in seen:raise ValueError("Duplicate prediction")
            seen.add(key)
            if trace in mapping and mapping[trace]!=person:raise ValueError("Trace mapped to two identities")
            mapping[trace]=person
            pairs[(condition,model)].add((trace,t))
            valid=row["has_prediction"].lower()
            if valid not in ("true","false","1","0"):raise ValueError("Invalid availability flag")
            available=valid in ("true","1")
            value=row["angular_error_deg"].strip()
            if available:
                if not value:raise ValueError("Missing angular error")
                error=float(value)
                if not math.isfinite(error) or not 0<=error<=180:raise ValueError("Invalid angle")
            else:
                if value:raise ValueError("Unavailable prediction cannot have an error")
                error=PENALTY
            g=groups[(condition,model,person)]
            g[0]+=1;g[1]+=int(available);g[2]+=error;g[3]+=error if available else 0
            n+=1
    models=sorted({k[1] for k in pairs});conditions=sorted({k[0] for k in pairs})
    subjects=sorted(set(mapping.values()))
    if len(models)<2 or len(subjects)<3:raise ValueError("Need >=2 models and >=3 identity groups")
    for cond in conditions:
        reference=None
        for model in models:
            frames=pairs.get((cond,model))
            if not frames or (reference is not None and frames!=reference):
                raise ValueError("Predictor frame keys are not paired")
            reference=frames
    rows=[]
    for (cond,model,person),(total,available,sum_loss,sum_available_error) in sorted(groups.items()):
        rows.append(dict(condition=cond,predictor=model,subject_id=person,
                         frames=total,available=available,availability=available/total,
                         penalized_mean_deg=sum_loss/total,
                         conditional_mean_deg=sum_available_error/available if available else None))
    return rows,models,conditions,subjects,n

def splits_for(subjects,seed):
    subjects=sorted(subjects)
    if len(subjects)<3:raise ValueError("Need >=3 identities")
    random.Random(seed).shuffle(subjects)
    n=len(subjects);train=max(1,int(.6*n));val=max(1,int(.2*n))
    if train+val>=n:train=n-2;val=1
    return {s:("train" if i<train else "validation" if i<train+val else "test")
            for i,s in enumerate(subjects)}

def summary(rows,split,cond,model):
    x=[r for r in rows if r["split"]==split and r["condition"]==cond and r["predictor"]==model]
    if not x:raise ValueError("Missing split records")
    return {"subjects":len(x),
            "mean_penalized_deg":statistics.mean(r["penalized_mean_deg"] for r in x),
            "mean_availability":statistics.mean(r["availability"] for r in x)}

def uncertainty(rows,cond,model,baseline,seed,count):
    def by_model(name):
        return {r["subject_id"]:r["penalized_mean_deg"] for r in rows if r["split"]=="test" and r["condition"]==cond and r["predictor"]==name}
    a,b=by_model(model),by_model(baseline)
    if not a or a.keys()!=b.keys():raise ValueError("Unpaired test subjects")
    diff=[a[s]-b[s] for s in sorted(a)]
    rng=random.Random(seed)
    boot=sorted(statistics.mean(rng.choice(diff) for _ in diff) for _ in range(count))
    return statistics.mean(diff),boot[int(.025*(count-1))],boot[int(.975*(count-1))],len(diff)

def export_csv(path,rows):
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)

def run(frames,output,seed=20261010,baseline="hold",phase2=None,bootstrap=1000):
    if output.exists():raise FileExistsError(output)
    if not frames.is_file():raise FileNotFoundError(frames)
    if bootstrap<100 or bootstrap>50000:raise ValueError("Invalid bootstrap count")
    rows,models,conds,subjects,count=read_data(frames)
    if baseline not in models:raise ValueError("Unknown baseline")
    group=splits_for(subjects,seed)
    for r in rows:r["split"]=group[r["subject_id"]]
    selected=[];summary_rows=[];diff_rows=[]
    for condition in conds:
        # Training data only. The simulator condition is known here, unlike a
        # deployed system where a controller must infer its own environment state.
        chosen=min(models,key=lambda model:(summary(rows,"train",condition,model)["mean_penalized_deg"],model))
        selected.append({"condition":condition,"selected_predictor":chosen})
        for split in ("train","validation","test"):
            for model in models:
                summary_rows.append({"condition":condition,"split":split,"predictor":model,
                    "selected_by_train":model==chosen,**summary(rows,split,condition,model)})
        mean,lo,hi,n=uncertainty(rows,condition,chosen,baseline,seed+sum(map(ord,condition)),bootstrap)
        diff_rows.append({"condition":condition,"selected":chosen,"baseline":baseline,
            "test_delta_deg":mean,"ci95_low":lo,"ci95_high":hi,"heldout_groups":n})
    sidecar=None
    if phase2 is not None:
        mpath=phase2/"manifest.json"; spath=phase2/"summary.csv"
        if not mpath.is_file() or not spath.is_file():raise ValueError("Invalid Phase 2 sidecar")
        m=json.loads(mpath.read_text())
        if not str(m.get("suite","")).startswith("FB-RENDER"):raise ValueError("Wrong Phase 2 suite")
        sidecar={"classification":m.get("results_class"),
                "manifest_sha256":sha(mpath),"summary_sha256":sha(spath),
                "synchronized_with_gaze":False}
    output.mkdir(parents=True)
    export_csv(output/"per_subject.csv",rows)
    export_csv(output/"summary.csv",summary_rows)
    export_csv(output/"selected_policies.csv",selected)
    export_csv(output/"test_uncertainty.csv",diff_rows)
    export_csv(output/"splits.csv",[{"subject_id":s,"split":group[s]} for s in sorted(group)])
    manifest={"spec_version":VERSION,"created_utc":datetime.now(timezone.utc).isoformat(),
      "phase1_sha256":sha(frames),"phase2_reference":sidecar,"seed":seed,
      "missing_penalty_deg":PENALTY,"subjects":len(subjects),"frame_model_rows":count,
      "conditions":conds,"predictors":models,"bootstrap":bootstrap,
      "split_unit":"subject_id","human_perception_validated":False,
      "real_gpu_score_qualified":False,"rl_agent_trained":False,
      "known_simulator_condition_required_for_policy":True,
      "host":platform.platform(),"python":sys.version.split()[0]}
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    report=["# FB-CAMPAIGN-01: held-out synthetic research campaign","",
      f"{count} prediction outcomes; {len(subjects)} identity groups; {len(conds)} conditions.",
      "Train/validation/test split by subject_id. No subject overlaps.",
      "Offline full-information model choice uses training labels only; not RL.",
      "The benchmark condition identifier is known in training but not necessarily observable during real XR.",
      f"Missing predictions incur a declared {PENALTY:g} degree penalty; not calibrated perception.",
      "Participant bootstrap is only a synthetic-session diagnostic with this source data.",
      "No empirical gaze, real hardware VRS, or human judgment has been validated.","",
      "| Condition | Chosen policy | Held-out delta vs hold (deg) | 95% paired interval |",
      "|---|---|---:|---:|"]
    for r in diff_rows:
        report.append(f"| {r['condition']} | {r['selected']} | {r['test_delta_deg']:.4f} | [{r['ci95_low']:.4f}, {r['ci95_high']:.4f}] |")
    (output/"report.md").write_text("\n".join(report)+"\n")
    (output/"STATUS.md").write_text("# Status\n- Campaign execution: PASS\n- Paired frame equality: PASS\n- Disjoint identity splits: PASS\n- Empirical datasets downloaded: NO\n- Live XR/human validity: NOT TESTED\n")
    return manifest

def cli():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest="action",required=True)
    c=subs.add_parser("run")
    c.add_argument("--phase1-frames",type=Path)
    c.add_argument("--generate-phase1",action="store_true")
    c.add_argument("--phase2-output",type=Path)
    c.add_argument("--output",type=Path,required=True)
    c.add_argument("--seed",type=int,default=20261010)
    c.add_argument("--baseline",default="hold")
    c.add_argument("--bootstrap",type=int,default=1000)
    d=subs.add_parser("datasets")
    d.add_argument("--registry",type=Path,default=Path(__file__).resolve().parent.parent/"benchmark_spec/datasets/registry.json")
    a=p.parse_args()
    if a.action=="datasets":
        registry=json.loads(a.registry.read_text())
        for item in registry["datasets"]:
            print(item["id"],item["availability"],item["role"],sep=" | ")
        return
    if a.output.exists():raise FileExistsError(a.output)
    if bool(a.phase1_frames)==bool(a.generate_phase1):
        p.error("Specify exactly one input source: --phase1-frames or --generate-phase1")
    if a.generate_phase1:
        upstream=a.output.with_name(a.output.name+"-phase1-input")
        if upstream.exists():raise FileExistsError(upstream)
        subprocess.run([sys.executable,"-m","foveabench.phase1","run","--seed",str(a.seed),
                        "--output",str(upstream)],check=True)
        frames=upstream/"frames.csv"
    else:frames=a.phase1_frames
    result=run(frames,a.output,a.seed,a.baseline,a.phase2_output,a.bootstrap)
    print(f"{VERSION} PASS: {result['frame_model_rows']} frame-level outcomes, {result['subjects']} identities.")

if __name__=="__main__":cli()
