"""FB-GAZE-01: causally replay timestamped gaze under controlled sensor faults.

An independent, headless baseline study. No ILLIXR source, proprietary hardware,
GPU timing, or participant data is required. This is not perceptual validation.

Precise semantics:
  sample timestamp   = when the eye signal represents the gaze direction
  delivery timestamp = when the algorithm is permitted to observe the sample
  target timestamp   = frame target gaze time, never accessible to predictor
  predictor input    = delivered valid gaze samples with delivery <= target
  predictor output   = predicted direction for target, in normalized view UV
  evaluation         = angular ray difference from withheld target ground truth

When new gaze data are collected, the dataset schema must preserve acquisition
and delivery timestamps; simulating transport latency is NOT measuring it.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
from typing import Any

SPEC_VERSION = "FB-GAZE-01/1.0"
DATA_COLUMNS = ("trace_id", "subject_id", "timestamp_ns", "gaze_x", "gaze_y", "valid")
SUMMARY_COLUMNS = ("condition", "predictor", "trace_count", "eligible_frames",
                   "total_frames", "availability", "mean_angular_deg", "p50_deg",
                   "p95_deg", "p99_deg", "miss_rate_5deg", "unconditional_miss_rate_5deg", "meets_quality_gate")
TRACE_COLUMNS = ("condition", "predictor", "trace_id", "subject_id", "source", "frames",
                 "eligible_frames", "availability", "mean_angular_deg", "p95_deg",
                 "miss_rate_5deg")
FRAME_COLUMNS = ("condition", "predictor", "trace_id", "subject_id", "target_ns",
                 "truth_x", "truth_y", "pred_x", "pred_y", "has_prediction",
                 "angular_error_deg", "velocity_bin", "age_ms", "delivered_samples")


@dataclass(frozen=True)
class Sample:
    trace_id: str
    subject_id: str
    t_ns: int
    x: float | None
    y: float | None
    valid: bool


@dataclass(frozen=True)
class Observation:
    sample_ns: int
    delivered_ns: int
    x: float
    y: float


def checked_number(n: Any, label: str, lo: float, hi: float) -> float:
    try:
        value = float(n)
    except (ValueError, TypeError):
        raise ValueError(f"{label}: expected finite numeric value") from None
    if not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f"{label}: expected finite [{lo}, {hi}], got {n!r}")
    return value


def verify_samples(samples: list[Sample]) -> None:
    if not samples:
        raise ValueError("Dataset contains no gaze records")
    last_by_trace: dict[str, int] = {}
    owners: dict[str, str] = {}
    valid_counts: dict[str, int] = {}
    for sample in samples:
        if not sample.trace_id or not sample.subject_id:
            raise ValueError("Nonempty trace_id and subject_id are mandatory")
        last = last_by_trace.get(sample.trace_id)
        if sample.t_ns < 0 or (last is not None and sample.t_ns <= last):
            raise ValueError(f"Non-monotonic timestamp in trace {sample.trace_id}")
        if sample.trace_id in owners and owners[sample.trace_id] != sample.subject_id:
            raise ValueError("One trace_id cannot belong to multiple subjects")
        last_by_trace[sample.trace_id] = sample.t_ns
        owners[sample.trace_id] = sample.subject_id
        valid_counts[sample.trace_id] = valid_counts.get(sample.trace_id, 0) + int(sample.valid)
        if sample.valid:
            if sample.x is None or sample.y is None:
                raise ValueError("Valid gaze needs gaze_x and gaze_y")
            checked_number(sample.x, "gaze_x", 0, 1)
            checked_number(sample.y, "gaze_y", 0, 1)
        elif sample.x is not None or sample.y is not None:
            raise ValueError("Invalid gaze must leave both coordinates blank")
    if any(count < 3 for count in valid_counts.values()):
        raise ValueError("Each trace requires at least 3 valid samples")


def load_csv(path: Path) -> list[Sample]:
    with path.open("r", newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None or set(reader.fieldnames) != set(DATA_COLUMNS):
            raise ValueError(f"CSV headers must be exactly {list(DATA_COLUMNS)}")
        out: list[Sample] = []
        for row in reader:
            if None in row or any(x is None for x in row.values()):
                raise ValueError("CSV row has unexpected field count")
            flag = row["valid"].strip().lower()
            if flag not in ("0", "1", "false", "true"):
                raise ValueError("valid must be 0/1/false/true")
            valid = flag in ("1", "true")
            try:
                t = int(row["timestamp_ns"])
            except ValueError:
                raise ValueError("timestamp_ns must be an integer") from None
            if not valid and (row["gaze_x"].strip() or row["gaze_y"].strip()):
                raise ValueError("Invalid gaze coordinates must be blank")
            out.append(Sample(row["trace_id"], row["subject_id"], t,
                              checked_number(row["gaze_x"], "gaze_x", 0, 1) if valid else None,
                              checked_number(row["gaze_y"], "gaze_y", 0, 1) if valid else None,
                              valid))
    verify_samples(out)
    return out


def canonical_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_manifest(obj: dict[str, Any], *, synthetic: bool) -> None:
    keys = {"dataset_id", "source_kind", "source_url", "license", "consent_status",
            "coordinate_system", "timebase", "sampling_description",
            "eye_channel", "device_and_firmware", "calibration", "processing",
            "data_loss", "measurement_uncertainty", "signal_latency"}
    if set(obj) != keys:
        raise ValueError(f"Dataset manifest keys must be exactly {sorted(keys)}")
    if obj["source_kind"] not in ("synthetic", "recorded"):
        raise ValueError("source_kind must be synthetic or recorded")
    if bool(obj["source_kind"] == "synthetic") != synthetic:
        raise ValueError("Source kind mismatch")
    if obj["coordinate_system"] != "normalized_uv_top_left":
        raise ValueError("Explicitly convert coordinates; normalized_uv_top_left is required")
    if obj["timebase"] != "relative_monotonic_ns":
        raise ValueError("Timestamps must be relative, monotonic nanoseconds")
    if obj["eye_channel"] != "combined_gaze":
        raise ValueError("This profile is combined-gaze only; do not silently average eyes")
    if not all(isinstance(v, str) and v.strip() for v in obj.values()):
        raise ValueError("No metadata field may be empty; write 'unknown' explicitly")
    if not synthetic and (obj["license"].lower() == "unknown" or
                          obj["consent_status"].lower() == "unknown"):
        raise ValueError("Recorded data requires confirmed license and permission/consent metadata")


def synthetic_traces(seed: int, hz: int, frames: int, sessions_per_kind: int) -> list[Sample]:
    """Procedural *stress signals*, never described as human gaze recordings."""
    rng = random.Random(seed)
    out = []
    for kind in ("fixation", "pursuit", "jump"):
        for session in range(sessions_per_kind):
            phase = rng.uniform(-.7, .7)
            base_x = rng.uniform(.38, .62)
            base_y = rng.uniform(.38, .62)
            for i in range(frames):
                t = i / hz
                if kind == "fixation":
                    x = base_x + .004 * math.sin(2 * math.pi * .9*t + phase)
                    y = base_y + .003 * math.cos(2 * math.pi * .5*t + phase)
                elif kind == "pursuit":
                    x = base_x + .22*math.sin(2*math.pi*.85*t+phase)
                    y = base_y + .10*math.cos(2*math.pi*.43*t+phase)
                else:
                    segment = (i // max(2, hz//4)) % 2
                    x = (.23 + .04*phase) if segment == 0 else (.77 + .04*phase)
                    y = .40 if segment == 0 else .65
                out.append(Sample(f"synthetic-{kind}-{session:02}",
                                  f"synthetic-agent-{kind}-{session:02}",
                                  round(i*1e9/hz), max(0.0, min(1.0, x)),
                                  max(0.0, min(1.0, y)), True))
    verify_samples(out)
    return out


def direction(x: float, y: float, hfov: float, vfov: float) -> tuple[float, float, float]:
    """Pinhole gaze ray; no headset optics or lens distortion simulated."""
    dx = (2*x-1)*math.tan(math.radians(hfov/2))
    dy = (1-2*y)*math.tan(math.radians(vfov/2))
    norm = math.sqrt(dx*dx + dy*dy + 1)
    return dx/norm, dy/norm, 1/norm


def angular_error(ax: float, ay: float, bx: float, by: float, hfov: float,
                  vfov: float) -> float:
    a = direction(ax, ay, hfov, vfov)
    b = direction(bx, by, hfov, vfov)
    c = min(1.0, max(-1.0, sum(x*y for x, y in zip(a, b))))
    return math.degrees(math.acos(c))


def group_samples(samples: list[Sample]) -> dict[str, list[Sample]]:
    result: dict[str, list[Sample]] = {}
    for s in samples:
        result.setdefault(s.trace_id, []).append(s)
    return result


def observations(samples: list[Sample], *, seed: int, condition: dict,
                 hfov: float, vfov: float) -> list[Observation]:
    """Paired algorithms consume the SAME noisy, delayed, dropped observations."""
    rng = random.Random(seed)
    result = []
    for sample in samples:
        if not sample.valid or rng.random() < condition["dropout_probability"]:
            continue
        assert sample.x is not None and sample.y is not None
        # Deg/FOV is a small-angle UV approximation, not a calibrated camera.
        nx = sample.x + rng.gauss(0, condition["noise_sigma_deg"] / hfov)
        ny = sample.y + rng.gauss(0, condition["noise_sigma_deg"] / vfov)
        delay_ms = max(0.0, condition["latency_ms"] +
                       rng.gauss(0, condition["jitter_sigma_ms"]))
        result.append(Observation(sample.t_ns, sample.t_ns + round(delay_ms*1e6),
                                  min(1, max(0, nx)), min(1, max(0, ny))))
    # Sort arrival before sample time: out-of-order delivery cannot leak future.
    result.sort(key=lambda x: (x.delivered_ns, x.sample_ns))
    return result


def predict(observed: list[Observation], model: str, target_ns: int,
            horizon_cap_ms: float, max_stale_ms: float) -> tuple[float, float, float] | None:
    if not observed:
        return None
    # In a jittery transport, the LAST delivered packet need not be the
    # NEWEST sample. Select greatest sample_ns among already delivered.
    # No sample with delivery time > target is accepted by the caller.
    ordered = sorted(observed, key=lambda o: o.sample_ns)
    latest = ordered[-1]
    age = (target_ns-latest.sample_ns)/1e6
    if age > max_stale_ms:
        return None
    if model == "hold" or len(observed) < 2:
        return latest.x, latest.y, age
    if model != "velocity":
        raise ValueError(f"Unknown algorithm: {model}")
    # Use two temporally distinct measurement samples; arrived order may differ.
    older = next((o for o in reversed(ordered[:-1])
                  if o.sample_ns < latest.sample_ns), None)
    if older is None:
        return latest.x, latest.y, age
    dt = (latest.sample_ns-older.sample_ns)/1e9
    extrap_sec = min(max(0, (target_ns-latest.sample_ns)/1e9), horizon_cap_ms/1000)
    vx = (latest.x-older.x)/dt
    vy = (latest.y-older.y)/dt
    return (min(1, max(0, latest.x+vx*extrap_sec)),
            min(1, max(0, latest.y+vy*extrap_sec)), age)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    r = (len(ordered)-1)*q/100
    lo = int(r)
    hi = min(lo+1, len(ordered)-1)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(r-lo)


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_config(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    mandatory = {"spec_version", "frame_hz", "hfov_deg", "vfov_deg", "max_stale_ms",
                 "horizon_cap_ms", "radius_threshold_deg", "algorithms", "conditions",
                 "synthetic_frames", "synthetic_sessions_per_kind", "quality_gate"}
    if set(obj) != mandatory or obj["spec_version"] != SPEC_VERSION:
        raise ValueError("Profile fields/version do not match FB-GAZE-01/1.0")
    for key in ("hfov_deg", "vfov_deg"):
        checked_number(obj[key], key, 1, 179)
    checked_number(obj["radius_threshold_deg"], "radius_threshold_deg", .01, 90)
    checked_number(obj["max_stale_ms"], "max_stale_ms", 1, 10000)
    checked_number(obj["horizon_cap_ms"], "horizon_cap_ms", 0, 10000)
    if not isinstance(obj["frame_hz"], int) or not 1 <= obj["frame_hz"] <= 1000:
        raise ValueError("frame_hz must be integer 1..1000")
    if (not isinstance(obj["synthetic_frames"], int) or obj["synthetic_frames"] < 10
            or not isinstance(obj["synthetic_sessions_per_kind"], int)
            or obj["synthetic_sessions_per_kind"] < 1):
        raise ValueError("Invalid synthetic workload sizes")
    if set(obj["quality_gate"]) != {"min_availability", "max_miss_rate_5deg"}:
        raise ValueError("Explicit quality gate thresholds required")
    for name in ("min_availability", "max_miss_rate_5deg"):
        checked_number(obj["quality_gate"][name],name,0,1)
    if obj["algorithms"] != ["hold", "velocity"]:
        raise ValueError("v1 standard profile runs both fixed baselines")
    if not isinstance(obj["conditions"], list) or not obj["conditions"]:
        raise ValueError("Empty conditions")
    for c in obj["conditions"]:
        if set(c) != {"id", "latency_ms", "jitter_sigma_ms", "noise_sigma_deg",
                      "dropout_probability"} or not isinstance(c["id"], str):
            raise ValueError("Malformed condition")
        for k in ("latency_ms", "jitter_sigma_ms"):
            checked_number(c[k], k, 0, 10000)
        checked_number(c["noise_sigma_deg"], "noise_sigma_deg", 0, 90)
        checked_number(c["dropout_probability"], "dropout_probability", 0, 1)
    if len({c["id"] for c in obj["conditions"]}) != len(obj["conditions"]):
        raise ValueError("Duplicate condition IDs")
    return obj


def generate_rows(traces: dict[str, list[Sample]], config: dict, seed: int, kind: str
                 ) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    trace_stats: list[dict] = []
    hfov, vfov = config["hfov_deg"], config["vfov_deg"]
    for condition in config["conditions"]:
        cid = condition["id"]
        for trace_id, samples in sorted(traces.items()):
            # Hash, don't use Python's randomized hash(); conditions remain paired.
            seed_material = f"{seed}|{cid}|{trace_id}|v1".encode()
            case_seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")
            events = observations(samples, seed=case_seed, condition=condition,
                                  hfov=hfov, vfov=vfov)
            for model in config["algorithms"]:
                cursor = 0
                # Only two newest-by-sample-time arrivals are required.
                # Avoid O(N^2) rescans when replaying multi-hour gaze traces.
                arrived: list[Observation] = []
                considered = 0
                eligible = 0
                errs: list[float] = []
                miss = 0
                for i, truth in enumerate(samples):
                    target = truth.t_ns
                    while cursor < len(events) and events[cursor].delivered_ns <= target:
                        packet = events[cursor]
                        arrived.append(packet)
                        arrived.sort(key=lambda o: o.sample_ns)
                        arrived = arrived[-2:]
                        cursor += 1
                    if any(o.delivered_ns > target for o in arrived):
                        raise AssertionError("Future-delivered observation leaked")
                    if not truth.valid:
                        continue
                    considered += 1
                    pred = predict(arrived, model, target, config["horizon_cap_ms"],
                                   config["max_stale_ms"])
                    assert truth.x is not None and truth.y is not None
                    if i == 0 or not samples[i-1].valid:
                        vclass = "unknown"
                    else:
                        last = samples[i-1]
                        assert last.x is not None and last.y is not None
                        deg = angular_error(last.x,last.y,truth.x,truth.y,hfov,vfov)
                        vel = deg * 1e9/(truth.t_ns-last.t_ns)
                        vclass = "low" if vel < 30 else "medium" if vel < 150 else "high"
                    result = {"condition": cid, "predictor": model, "trace_id": trace_id,
                              "subject_id": truth.subject_id, "target_ns": target,
                              "truth_x": truth.x, "truth_y": truth.y,
                              "pred_x": None, "pred_y": None,
                              "has_prediction": False, "angular_error_deg": None,
                              "velocity_bin": vclass, "age_ms": None,
                              "delivered_samples": cursor}
                    if pred is not None:
                        eligible += 1
                        x, y, age = pred
                        e = angular_error(x,y,truth.x,truth.y,hfov,vfov)
                        errs.append(e)
                        miss += e > config["radius_threshold_deg"]
                        result.update({"pred_x": x, "pred_y": y, "has_prediction": True,
                                       "angular_error_deg": e, "age_ms": age})
                    rows.append(result)
                trace_stats.append({"condition": cid, "predictor": model,
                                    "trace_id": trace_id, "subject_id": samples[0].subject_id,
                                    "source": kind, "frames": considered,
                                    "eligible_frames": eligible,
                                    "availability": eligible/considered if considered else None,
                                    "mean_angular_deg": mean(errs), "p95_deg": percentile(errs,95),
                                    "miss_rate_5deg": miss/eligible if eligible else None})
    return rows, trace_stats


def aggregate(rows: list[dict], traces: list[dict], config: dict) -> tuple[list[dict], list[dict]]:
    out, comparisons = [], []
    for condition in config["conditions"]:
        cid = condition["id"]
        policy_rows = {}
        for model in config["algorithms"]:
            rs = [r for r in rows if r["condition"] == cid and r["predictor"] == model]
            ts = [r for r in traces if r["condition"] == cid and r["predictor"] == model]
            errors = [float(r["angular_error_deg"]) for r in rs if r["has_prediction"]]
            eligible = len(errors)
            total = len(rs)
            policy_rows[model] = ts
            av = eligible/total if total else None
            miss_rate = (sum(x > config["radius_threshold_deg"] for x in errors)/eligible if eligible else None)
            gate = (av is not None and miss_rate is not None and
                    av >= config["quality_gate"]["min_availability"] and
                    miss_rate <= config["quality_gate"]["max_miss_rate_5deg"])
            out.append({"condition": cid, "predictor": model,
                        "trace_count": len(ts), "eligible_frames": eligible,
                        "total_frames": total, "availability": av,
                        "mean_angular_deg": mean(errors), "p50_deg": percentile(errors, 50),
                        "p95_deg": percentile(errors, 95), "p99_deg": percentile(errors,99),
                        "miss_rate_5deg": miss_rate, "meets_quality_gate": gate,
                        "unconditional_miss_rate_5deg":
                            (total-eligible+sum(x > config["radius_threshold_deg"] for x in errors))/total if total else None})
        # Paired comparisons are trace-level means. Invalid predictions are not
        # silently treated as zero error; the absence rate stays separate.
        hold = {r["trace_id"]: r for r in policy_rows["hold"]}
        velocity = {r["trace_id"]: r for r in policy_rows["velocity"]}
        paired = [(tid, velocity[tid]["mean_angular_deg"]-h["mean_angular_deg"])
                  for tid, h in hold.items() if h["mean_angular_deg"] is not None
                  and velocity[tid]["mean_angular_deg"] is not None]
        deltas = [x[1] for x in paired]
        comparisons.append({"condition": cid, "metric": "trace_mean_angular_deg",
                            "comparison": "velocity_minus_hold",
                            "paired_trace_count": len(deltas),
                            "paired_trace_mean_difference_deg": mean(deltas),
                            "interpretation": "negative_favors_velocity; synthetic_traces_not_human_subjects"})
    return out, comparisons


def package_run(*, config_path: Path, output: Path, seed: int,
                data_path: Path | None, metadata_path: Path | None) -> None:
    config = load_config(config_path)
    if output.exists():
        raise FileExistsError("Refusing to overwrite an experiment directory")
    if data_path is None and metadata_path is not None:
        raise ValueError("--dataset-manifest requires --dataset")
    if data_path is not None and metadata_path is None:
        raise ValueError("Recorded dataset requires --dataset-manifest")
    if data_path is None:
        samples = synthetic_traces(seed, config["frame_hz"],config["synthetic_frames"],
                                   config["synthetic_sessions_per_kind"])
        kind = "synthetic"
        dataset_hash = hashlib.sha256("\n".join(str(s) for s in samples).encode()).hexdigest()
        metadata = {"dataset_id":"procedural-FB-GAZE-01", "source_kind":"synthetic",
                    "source_url":"generated_locally", "license":"Apache-2.0",
                    "consent_status":"not_applicable", "coordinate_system":"normalized_uv_top_left",
                    "timebase":"relative_monotonic_ns", "sampling_description":"procedural_exact_frame_hz",
                    "eye_channel":"combined_gaze", "device_and_firmware":"none_synthetic",
                    "calibration":"none_synthetic", "processing":"procedural_formula_v1",
                    "data_loss":"none_in_ground_truth", "measurement_uncertainty":"not_empirical",
                    "signal_latency":"zero_in_ground_truth;synthetic_conditions_in_config"}
    else:
        samples = load_csv(data_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        validate_manifest(metadata, synthetic=False)
        kind = "recorded"
        dataset_hash = canonical_hash(data_path)
    validate_manifest(metadata, synthetic=(kind=="synthetic"))
    grouped = group_samples(samples)
    if not all(len({s.subject_id for s in t}) == 1 for t in grouped.values()):
        raise ValueError("Mismatched subject")
    rows, per_trace = generate_rows(grouped,config,seed,kind)
    summary, paired = aggregate(rows,per_trace,config)
    # Results directory appears only after successful input/compute validation.
    output.mkdir(parents=True)
    write_csv(output/"frames.csv",FRAME_COLUMNS,rows)
    write_csv(output/"per_trace.csv",TRACE_COLUMNS,per_trace)
    write_csv(output/"summary.csv",SUMMARY_COLUMNS,summary)
    write_csv(output/"paired.csv",("condition","metric","comparison","paired_trace_count",
                                    "paired_trace_mean_difference_deg","interpretation"),paired)
    (output/"dataset_metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    (output/"profile.json").write_text(json.dumps(config,indent=2)+"\n")
    checks = {
        "input_trace_validity":"PASS", "causal_observation_delivery":"PASS",
        "paired_identical_observation_stream":"PASS",
        "source_hash_recorded":"PASS", "metrics_nonnegative":"PASS" if all(
            float(r["angular_error_deg"]) >= 0 for r in rows if r["has_prediction"]) else "FAIL",
        "recorded_dataset_metadata_present":"PASS" if kind=="recorded" else "NOT_RUN",
        "human_participant_authenticity_verified":"NOT_VERIFIED",
        "vulkan_gpu_time":"NOT_IMPLEMENTED", "illixr_runtime":"NOT_IMPLEMENTED",
        "human_perceptual_validation":"NOT_RUN", "physical_latency_measurement":"NOT_RUN",
    }
    manifest = {
        "spec_version": SPEC_VERSION, "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "source_kind":kind, "dataset_sha256":dataset_hash,
        "profile_sha256":canonical_hash(config_path),
        "engine_sha256":canonical_hash(Path(__file__)), "seed":seed,
        "traces":len(grouped), "declared_subject_identifiers":len({s.subject_id for s in samples}),
        "verified_human_participants":None,
        "frames":len(rows), "conditions":len(config["conditions"]),
        "algorithms":config["algorithms"],
        "platform":{"python":sys.version.split()[0],"machine":platform.machine(),"os":platform.platform()},
        "evidence":"causal gaze prediction simulation; not GPU/XR/human results",
        "limitations":["Ground-truth trajectories may be synthetic.",
          "Delay, noise and dropout are injected, not physically measured.",
          "Small-angle noise perturbation ignores lens geometry.",
          "Velocity bins are analytical stress categories, not validated eye-movement labels.",
          "No gaze-quality/perceptual/GPU claims are justified.",
          "No inference about participant population from synthetic agents."],
        "checks":checks}
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (output/"STATUS.md").write_text("# Run validation\n\n"+"\n".join(
        f"- {k}: **{v}**" for k,v in checks.items())+"\n")
    lines = ["# FB-GAZE-01 automated study", "",f"Source: **{kind}**; traces: **{len(grouped)}**; "
             f"frame evaluations: **{len(rows)}**; conditions: **{len(config['conditions'])}**.",
             "", "| Condition | Model | Available % | P95 angular error (deg) | Miss >5 deg | Quality gate |",
             "|---|---|---:|---:|---:|---|"]
    for r in summary:
        def fmt(x: float | None, pct: bool=False) -> str:
            return "N/A" if x is None else f"{100*x:.2f}%" if pct else f"{x:.3f}"
        lines.append(f"| {r['condition']} | {r['predictor']} | {fmt(r['availability'],True)} | "
                     f"{fmt(r['p95_deg'])} | {fmt(r['miss_rate_5deg'],True)} | "
                     f"{'PASS' if r['meets_quality_gate'] else 'FAIL'} |")
    lines += ["", "**Interpretation:** angular error is based on normalized pinhole rays with "
              "declared field of view. 'Miss' is a geometric 5° threshold, **not** an "
              "empirically calibrated perceptual outcome.","",
              "Quality gate is an illustrative stress-study acceptance rule, not an accredited perceptual standard.","",
              "Sample delivery and prediction are causally constrained. No gaze sample delivered "
              "after a target frame is visible to its prediction.","",
              "The input profiles and dataset metadata are snapshotted with hashes. "
              "Frame rows are not independent participants; no population-level p-values are reported.",""]
    (output/"report.md").write_text("\n".join(lines))
    if "FAIL" in checks.values():
        raise RuntimeError("Experiment internal check failed")
    print(f"FB-GAZE-01 PASS: {len(grouped)} traces, {len(config['conditions'])} conditions, "
          f"{len(rows)} scored frame-model pairs")
    print("Synthetic data are NOT human-grounded. Zero real GPU measurements.")
    print("Report:", (output/"report.md").resolve())


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command",required=True)
    run = commands.add_parser("run",help="Run an autonomous gaze resilience study")
    run.add_argument("--config",type=Path,default=Path("benchmark_spec/profiles/fb-gaze-01.json"))
    run.add_argument("--dataset",type=Path)
    run.add_argument("--dataset-manifest",type=Path)
    run.add_argument("--output",required=True,type=Path)
    run.add_argument("--seed",type=int,default=20261010)
    check = commands.add_parser("validate-dataset",help="Validate strict normalized gaze CSV and metadata")
    check.add_argument("--dataset",required=True,type=Path)
    check.add_argument("--dataset-manifest",required=True,type=Path)
    args = cli.parse_args()
    try:
        if args.command == "run":
            package_run(config_path=args.config, output=args.output,seed=args.seed,
                        data_path=args.dataset,metadata_path=args.dataset_manifest)
        else:
            samples=load_csv(args.dataset)
            validate_manifest(json.loads(args.dataset_manifest.read_text()),synthetic=False)
            print("VALID:",len(samples),"records / sha256:",canonical_hash(args.dataset))
    except (ValueError, FileExistsError, OSError) as exc:
        cli.exit(2,f"FoveaBench input/run error: {exc}\n")


if __name__ == "__main__":
    main()
