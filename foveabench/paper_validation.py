"""Paper replication register and cautious human/metric agreement checks.

Never generates or fabricates human responses. Uses caller-provided published or
consented ratings only; this code does not verify that the declared provenance
is legally or scientifically valid. No published score is copied as our result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from tqdm.auto import tqdm

REGISTRY = Path(__file__).resolve().parent.parent / "benchmark_spec/papers/reproduction_registry.json"
COLS = {"participant_id", "stimulus_id", "human_score", "predicted_score"}


def read_register(path=REGISTRY):
    registry=json.loads(path.read_text())
    if registry.get("schema")!="FB-PAPER-REGISTRY/1.0":
        raise ValueError("Paper registry version mismatch")
    ids=[]
    for p in registry["papers"]:
        if not all(p.get(k) for k in ("id","title","url","state","study_kind","replication_requirements")):
            raise ValueError("Incomplete paper reproducibility contract")
        ids.append(p["id"])
    if len(set(ids))!=len(ids):raise ValueError("Duplicate paper ID")
    return registry


def midranks(x):
    x=np.asarray(x,dtype=float)
    order=np.argsort(x,kind="stable")
    result=np.zeros(len(x),dtype=float)
    i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[order[j]]==x[order[i]]:j+=1
        result[order[i:j]]=(i+j-1)/2+1
        i=j
    return result


def spearman(x,y):
    a=midranks(x);b=midranks(y)
    if len(a)<3 or a.std()==0 or b.std()==0:return float('nan')
    return float(np.corrcoef(a,b)[0,1])


def preference_agreement(x,y):
    hits=ties=total=0
    for i in range(len(x)):
        for j in range(i+1,len(x)):
            aa=np.sign(x[i]-x[j]);bb=np.sign(y[i]-y[j])
            if aa==0 or bb==0:
                ties+=1;continue
            total+=1;hits+=int(aa==bb)
    return (hits/total if total else float('nan'),total,ties)


def compare(reference:Path,provenance_file:Path,output:Path,bootstraps:int,seed:int):
    if output.exists():raise FileExistsError(f"Existing evidence must not be overwritten: {output}")
    if not 20<=bootstraps<=10000:raise ValueError("Bootstrap must be in [20,10000]")
    info=json.loads(provenance_file.read_text())
    required=("paper_id","source_url","license","human_rating_source","display_calibration",
              "quality_higher_is_better","provenance_verified_by_operator")
    if any(k not in info for k in required):
        raise ValueError("Missing explicit provenance/calibration metadata fields")
    registry=read_register()
    paper=next((p for p in registry["papers"] if p["id"]==info["paper_id"]),None)
    if not paper:raise ValueError("Unknown referenced publication")
    if not info["quality_higher_is_better"]:
        raise ValueError("Normalize both scores to higher-is-better before comparison")
    if not info["provenance_verified_by_operator"]:
        raise ValueError("Operator must verify source documentation; do not relabel fabricated human data")
    if info["human_rating_source"] in ("synthetic","unknown"):
        raise ValueError("No simulated ratings may be labelled as published human observations")
    rows=[]
    with reference.open(newline="") as fp:
        reader=csv.DictReader(fp)
        if not COLS.issubset(reader.fieldnames or []):raise ValueError("Expected columns: "+str(sorted(COLS)))
        for r in tqdm(reader,desc="Reading supplied human-score table",unit="row"):
            who=r["participant_id"].strip();stim=r["stimulus_id"].strip()
            if not who or not stim:raise ValueError("Missing participant/stimulus identifier")
            human=float(r["human_score"]);prediction=float(r["predicted_score"])
            if not math.isfinite(human) or not math.isfinite(prediction):raise ValueError("Nonfinite scores")
            rows.append((who,stim,human,prediction))
    people=sorted(set(r[0] for r in rows));stimuli=sorted(set(r[1] for r in rows))
    if len(people)<5 or len(stimuli)<6:raise ValueError("At least 5 independent participants and 6 stimuli required")
    if len(set((r[0],r[1]) for r in rows))!=len(rows):raise ValueError("Duplicate participant-stimulus rating")
    predictions=defaultdict(list)
    for p,s,h,y in rows:predictions[s].append(y)
    inconsistent=[s for s,values in predictions.items() if max(values)-min(values)>1e-9]
    if inconsistent:raise ValueError("Predicted metric must be one fixed value per stimulus, independent of participant")
    pred=np.array([predictions[s][0] for s in stimuli])
    by_person=defaultdict(dict)
    for p,s,h,_ in rows:by_person[p][s]=h
    def aggregate(sample):
        means=[]
        for s in stimuli:
            ratings=[by_person[p][s] for p in sample if s in by_person[p]]
            if not ratings:return None
            means.append(float(np.mean(ratings)))
        return np.array(means)
    human=aggregate(people)
    measured=spearman(pred,human)
    agree,pairs,ties=preference_agreement(pred,human)
    rng=np.random.default_rng(seed)
    bs=[]
    for _ in tqdm(range(bootstraps),desc="Participant-cluster bootstrap",unit="sample"):
        sample=rng.choice(people,len(people),replace=True)
        h=aggregate(sample)
        if h is not None:
            rank=spearman(pred,h)
            if math.isfinite(rank):bs.append(rank)
    if len(bs)<bootstraps//2:raise ValueError("Too many bootstrap samples missing complete stimulus coverage")
    output.mkdir(parents=True)
    metric={"spearman_rho":measured,"preference_pair_agreement":agree,
        "non_tied_stimulus_pairs":pairs,"tied_pairs_excluded":ties,
        "rho_bootstrap_95pct":[float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))],
        "participants":len(people),"stimuli":len(stimuli),"human_rows":len(rows),
        "bootstrap_valid_replicates":len(bs),"source_sha256":hashlib.sha256(reference.read_bytes()).hexdigest(),
        "operator_claimed_verified_provenance":True,"independent_source_verification_by_FoveaBench":False,
        "published_result_replication_certified":False,
        "note":"Agreement diagnostics for supplied human scores; not a certified paper replication or independent new human study"}
    (output/"metrics.json").write_text(json.dumps(metric,indent=2,allow_nan=False)+"\n")
    (output/"provenance.snapshot.json").write_text(json.dumps(info,indent=2)+"\n")
    (output/"report.md").write_text("# Human-perception alignment diagnostic (uncertified)\n\n"
        f"- Paper: {paper['title']}\n"
        f"- Operator-declared ratings source: {info['human_rating_source']}\n"
        f"- Participants: {len(people)}, stimuli: {len(stimuli)}.\n"
        f"- Spearman rank correlation: **{measured:.4f}**.\n"
        f"- Participant-cluster bootstrap 95% interval: **[{metric['rho_bootstrap_95pct'][0]:.4f}, {metric['rho_bootstrap_95pct'][1]:.4f}]**.\n"
        f"- Pairwise preference agreement: **{agree:.2%}** ({pairs} valid non-tied stimulus pairs).\n\n"
        "**Not certified:** The benchmark cannot independently verify that ratings are human,"
        " licenses apply, or the paper used the same stimuli and statistical treatment."
        " Published figures remain external references, not our own measurements.\n")
    print((output/"report.md").read_text(),flush=True)
    return metric


def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest="command",required=True)
    a=s.add_parser("registry",help="Print target papers and replication blockers")
    a.add_argument("--path",type=Path,default=REGISTRY)
    c=s.add_parser("compare-human",help="Audit supplied real/published human quality ratings vs our predictions")
    c.add_argument("--csv",type=Path,required=True)
    c.add_argument("--provenance",type=Path,required=True)
    c.add_argument("--output",type=Path,required=True)
    c.add_argument("--bootstrap",type=int,default=500)
    c.add_argument("--seed",type=int,default=20261010)
    args=p.parse_args()
    if args.command=="registry":
        print("PAPER REPRODUCTION BACKLOG -- registry entries are NOT completed reproductions")
        for item in read_register(args.path)["papers"]:
            print(f"[{item['state']}] {item['id']}: {item['title']}")
            for gate in item["replication_requirements"]:
                print("  - "+gate)
    else:compare(args.csv,args.provenance,args.output,args.bootstrap,args.seed)

if __name__=="__main__":main()
