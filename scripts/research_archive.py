#!/usr/bin/env python3
"""FoveaBench research evidence and code-index recorder.

Subcommands:
  inventory --repo . --output results/code-inventory-TIMESTAMP
  archive --repo . --run-dir results/SOME-RUN --output results/archive-TIMESTAMP
  verify --manifest results/archive-TIMESTAMP/evidence_manifest.json

This utility NEVER converts a technical/synthetic run into human validation,
and never uploads private dataset contents or artifacts to GitHub.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "FB-RESEARCH-ARCHIVE/1.0"
TRACKED = {".py", ".cpp", ".cc", ".c", ".h", ".hpp", ".comp", ".vert", ".frag", ".sh", ".yml", ".yaml", ".json", ".toml", ".md"}
CODE = {".py", ".cpp", ".cc", ".c", ".h", ".hpp", ".comp", ".vert", ".frag", ".sh"}
SKIP = {".git", ".venv", "venv", "build", "results", "__pycache__", ".pytest_cache", ".mypy_cache"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def git(cmd: list[str], repo: Path) -> str | None:
    try:
        completed = subprocess.run(["git", "-C", str(repo), *cmd], text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   check=True, timeout=20)
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def source_defs(path: Path) -> list[dict]:
    code = path.read_text(encoding="utf-8")
    definitions = []
    if path.suffix == ".py":
        tree = ast.parse(code, filename=str(path))
        def walk(body, parent=""):
            for node in body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = parent + node.name
                    definitions.append({"symbol": name, "line": node.lineno,
                                        "kind": "class" if isinstance(node, ast.ClassDef) else "function"})
                    if isinstance(node, ast.ClassDef):
                        walk(node.body, name + ".")
        walk(tree.body)
    elif path.suffix in {".cpp", ".cc", ".c", ".h", ".hpp"}:
        expr = re.compile(r"^\s*(?:struct|class)\s+(\w+)|^\s*(?:static\s+)?(?:int|void|double|float|bool|Settings|Gaze|std::\S+)\s+(\w+)\s*\(")
        for i, line in enumerate(code.splitlines(), 1):
            m = expr.search(line)
            if m:
                definitions.append({"symbol": m.group(1) or m.group(2), "line": i,
                                    "kind": "approximate-cxx-declaration"})
    elif path.suffix in {".comp", ".vert", ".frag"}:
        for i, line in enumerate(code.splitlines(), 1):
            if "void main()" in line:
                definitions.append({"symbol": "main", "line": i, "kind": "shader-entry"})
    elif path.suffix == ".sh":
        for i, line in enumerate(code.splitlines(), 1):
            if re.match(r"^\s*(?:function\s+\w+|\w+\s*\(\s*\)\s*\{)", line):
                definitions.append({"symbol": line.strip(), "line": i, "kind": "shell-function"})
    return definitions


def discover(repo: Path):
    # Prefer git's actual tracked files: untracked private data is intentionally omitted.
    raw = git(["ls-files", "-z"], repo)
    if raw is not None and raw:
        # -z output contains \0 delimiters; no whitespace splitting.
        paths = [repo / x for x in raw.split("\0") if x]
    else:
        paths = [p for p in repo.rglob("*") if p.is_file() and not any(s in SKIP for s in p.relative_to(repo).parts)]
    return sorted((p for p in paths if p.is_file() and p.suffix.lower() in TRACKED), key=lambda p: str(p))


def inventory(repo: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    if not repo.is_dir():
        raise FileNotFoundError(repo)
    records = []
    for p in discover(repo):
        name = p.relative_to(repo).as_posix()
        rel = p.relative_to(repo)
        cat = ("test" if str(rel).startswith("tests/") else
               "ci" if str(rel).startswith(".github/workflows/") else
               "source" if p.suffix in CODE else
               "research-documentation" if str(rel).startswith("research/") else
               "specification-or-documentation")
        records.append({"path": name, "sha256": sha256(p), "size_bytes": p.stat().st_size,
                        "category": cat, "declarations": source_defs(p) if p.suffix in CODE else []})
    result = {"schema": SCHEMA, "kind": "code-inventory", "generated_utc": datetime.now(timezone.utc).isoformat(),
              "git_commit": git(["rev-parse", "HEAD"], repo),
              "git_dirty": bool(git(["status", "--porcelain"], repo)),
              "files": records, "tracked_files_indexed": len(records),
              "declared_python_test_methods": sum(
                  int(d["symbol"].split(".")[-1].startswith("test_"))
                  for item in records if item["path"].startswith("tests/")
                  for d in item["declarations"]
              ),
              "note": "Definitions are an automated source index, not proof of functional coverage; C++ declarations are approximate."}
    output.mkdir(parents=True)
    (output / "code_inventory.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# FoveaBench automatically indexed source map", "",
             f"Git commit: `{result['git_commit'] or 'unknown'}`; dirty: `{result['git_dirty']}`.",
             f"Indexed {len(records)} tracked or fixture source/specification files.", "",
             "This is a *code index*; research claims are recorded separately in `research/CLAIMS.md`.", ""]
    for item in records:
        lines.append(f"## `{item['path']}`")
        lines.append(f"Category: {item['category']}; SHA-256: `{item['sha256']}`; bytes: {item['size_bytes']}.")
        if item["declarations"]:
            lines.extend(f"- `{d['symbol']}` — line {d['line']} ({d['kind']})" for d in item["declarations"])
        else:
            lines.append("- No automatically parsed declarations (specification, workflow, or documentation).")
        lines.append("")
    (output / "code_inventory.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[INVENTORY] {len(records)} files indexed; {result['declared_python_test_methods']} test methods; {output}", flush=True)
    return result


def enumerate_evidence(run: Path):
    if not run.is_dir():
        raise FileNotFoundError(run)
    records = []
    for base, dirs, files in os.walk(run, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
        for name in sorted(files):
            p = Path(base) / name
            if p.is_symlink():
                raise ValueError("Symlinks forbidden in scientific archive: " + str(p))
            if p.is_file():
                records.append({"path": p.relative_to(run).as_posix(),
                                "sha256": sha256(p), "size_bytes": p.stat().st_size})
    if not records:
        raise ValueError("Cannot archive empty experiment directory")
    if len(records) > 100000:
        raise ValueError("Too many files; split experiment into separate archives")
    return records


def archive(repo: Path, run: Path, output: Path, description: str) -> dict:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    run = run.resolve()
    if not run.is_dir():
        raise FileNotFoundError(run)
    if output.resolve() == run or run in output.resolve().parents:
        raise ValueError("Output must not be inside input experiment directory")
    records = enumerate_evidence(run)
    git_status = git(["status", "--porcelain"], repo)
    meta = {"schema": SCHEMA, "kind": "experiment-evidence", "created_utc": datetime.now(timezone.utc).isoformat(),
            "run_directory": str(run), "description": description,
            "git_commit": git(["rev-parse", "HEAD"], repo), "git_dirty": bool(git_status),
            "files": records, "total_bytes": sum(r["size_bytes"] for r in records),
            "evidence_count": len(records),
            "qualification": {"raw_files_fingerprinted": True,
                 "real_human_gaze_confirmed": False,
                 "live_xr_replay_equivalence_confirmed": False,
                 "hardware_vrs_speedup_confirmed": False,
                 "publication_reproduced": False},
            "limitations": "This manifest proves file identity when originals are present; it is NOT a scientific validity certificate."}
    output.mkdir(parents=True)
    (output / "evidence_manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        f"# Local experiment evidence fingerprint\n\nDescription: {description}\n\n"
        f"Original directory: `{run}`\n\nGit commit: `{meta['git_commit']}`.\n\n"
        f"Files: {len(records)}; bytes: {meta['total_bytes']:,}.\n\n"
        "This folder contains hashes and metadata, **not copies of the raw evidence**. "
        "Preserve the original files and associated software. Do not commit private gaze/participant records to Git.\n",
        encoding="utf-8")
    print(f"[ARCHIVE] {len(records)} evidence files, {meta['total_bytes']:,} bytes; output={output}", flush=True)
    return meta


def verify(manifest_file: Path) -> dict:
    meta = json.loads(manifest_file.read_text(encoding="utf-8"))
    if meta.get("schema") != SCHEMA or meta.get("kind") != "experiment-evidence":
        raise ValueError("Unsupported evidence manifest schema")
    base = Path(meta["run_directory"])
    passed = missing = changed = 0
    for item in meta["files"]:
        rel = Path(item["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("Invalid relative evidence path")
        p = base / rel
        if not p.is_file():
            missing += 1
        elif p.is_symlink() or p.stat().st_size != item["size_bytes"] or sha256(p) != item["sha256"]:
            changed += 1
        else:
            passed += 1
    total = len(meta["files"])
    print(f"[VERIFY] pass={passed}/{total} missing={missing} modified={changed}; {base}", flush=True)
    return {"passed": passed, "missing": missing, "changed": changed, "total": total, "ok": passed == total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="cmd", required=True)
    a = subs.add_parser("inventory", help="Index tracked source, tests and research documentation")
    a.add_argument("--repo", type=Path, default=Path("."))
    a.add_argument("--output", type=Path, required=True)
    b = subs.add_parser("archive", help="Fingerprint all raw experiment outputs without altering them")
    b.add_argument("--repo", type=Path, default=Path("."))
    b.add_argument("--run-dir", type=Path, required=True)
    b.add_argument("--output", type=Path, required=True)
    b.add_argument("--description", required=True)
    c = subs.add_parser("verify", help="Rehash original raw files and check against saved record")
    c.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "inventory": inventory(args.repo.resolve(), args.output)
    elif args.cmd == "archive": archive(args.repo.resolve(), args.run_dir, args.output, args.description)
    else:
        result = verify(args.manifest)
        if not result["ok"]:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
