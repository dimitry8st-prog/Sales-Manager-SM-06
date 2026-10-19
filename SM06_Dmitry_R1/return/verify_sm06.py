#!/usr/bin/env python3
"""SM-06 reproducible CP0/CP1 verification and complete return packaging.

Run from a repository checkout:
    python -B SM06_Dmitry_R1/return/verify_sm06.py --repo .
Only Python's standard library and Git are used. No application runtime is installed.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

PACKAGE = "SM06_Dmitry_R1"
ISSUED_ZIP = "SM-06_Dmitriy_Stazher_R1.zip"
ISSUED_GIT_BLOB = "6cf5b65550e366de727cf0f41a45b941f89c5fbb"
LOCALES = ("en-GB", "ru-RU", "es-ES", "da-DK", "uk-UA")
MANIFEST = "return/SHA256SUMS.json"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def allowed(path):
    return (path in {"candidate/first_sm06_language.py", "candidate/README.md"}
            or path in {f"candidate/packs/{x}.json" for x in LOCALES}
            or path.startswith("candidate/tests/")
            or path.startswith("return/"))


def files(root):
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink is not permitted: {path}")
        if any(part in {"__pycache__", ".pytest_cache", ".git"} for part in path.parts):
            continue
        if path.is_file():
            if path.suffix in {".pyc", ".pyo"}:
                continue
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def archive_files(raw):
    """Validate every path and CRC before accepting any archive payload."""
    result = {}
    seen = set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC verification failed")
        for entry in archive.infolist():
            name = entry.filename
            path = PurePosixPath(name)
            if ("\\" in name or path.is_absolute() or ".." in path.parts
                    or not path.parts or path.parts[0] != PACKAGE
                    or ":" in path.parts[0]):
                raise ValueError(f"Unsafe ZIP path: {name}")
            key = name.casefold().rstrip("/")
            if key in seen:
                raise ValueError(f"Duplicate ZIP path: {name}")
            seen.add(key)
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError(f"Symlink ZIP member: {name}")
            if entry.is_dir():
                continue
            if len(path.parts) < 2:
                raise ValueError(f"Unexpected ZIP member: {name}")
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            if any(x in {"__pycache__", ".git", ".pytest_cache"} for x in path.parts):
                raise ValueError(f"Cache or VCS member: {name}")
            if relative.endswith((".pyc", ".pyo")):
                raise ValueError(f"Compiled member: {name}")
            result[relative] = archive.read(entry)
    return result


def materialize(root, payload):
    root.mkdir(parents=True, exist_ok=True)
    for relative, raw in payload.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def test_inventory(root):
    inventory = []
    for relative in sorted(files(root)):
        if relative.startswith("candidate/tests/") and relative.endswith(".py"):
            tree = ast.parse((root / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for method in node.body:
                        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if method.name.startswith("test"):
                                inventory.append(f"{relative}::{node.name}.{method.name}")
    return sorted(inventory)


def run_command(root, evidence, label, arguments, records):
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Prevent an inherited PYTHONPATH from changing the issued test environment.
    env.pop("PYTHONPATH", None)
    try:
        process = subprocess.run(arguments, cwd=root, env=env, capture_output=True,
                                 timeout=180, check=False)
        out, err, code = process.stdout, process.stderr, process.returncode
    except subprocess.TimeoutExpired as error:
        out, err, code = error.stdout or b"", error.stderr or b"", 124
        err += b"\nVerifier timeout after 180 seconds.\n"
    except OSError as error:
        out, err, code = b"", str(error).encode("utf-8"), 127
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / f"{label}.stdout").write_bytes(out)
    (evidence / f"{label}.stderr").write_bytes(err)
    record = {
        "label": label, "argv": arguments, "command": shlex.join(arguments),
        "cwd": str(root), "started_utc": started,
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "exit_code": code,
        "stdout": f"return/evidence/verification/{label}.stdout",
        "stderr": f"return/evidence/verification/{label}.stderr",
    }
    combined = (out + b"\n" + err).decode("utf-8", errors="replace")
    record["unittest_counts"] = [
        int(n) for n in re.findall(r"(?m)^Ran (\d+) tests? in ", combined)
    ]
    record["skips_found"] = bool(re.search(
        r"(?im)^\s*OK\s*\([^)]*skipped\s*=|^\s*skipped\s| \.\.\. skipped ", combined
    ))
    records.append(record)
    write_json(evidence / f"{label}.command.json", record)
    print(f"{label}: exit={code}; suites={record['unittest_counts']}", flush=True)
    return record, combined


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def validate_finished(payload, original, source_payload):
    manifest = json.loads(payload[MANIFEST].decode("utf-8"))
    expected = set(payload) - {MANIFEST}
    if set(manifest) != expected:
        raise ValueError("SHA256 manifest coverage is not exact")
    for relative, digest in manifest.items():
        if sha256(payload[relative]) != digest:
            raise ValueError(f"SHA256 mismatch: {relative}")
    for relative, raw in original.items():
        if not allowed(relative) and payload.get(relative) != raw:
            raise ValueError(f"Protected baseline differs: {relative}")
    for relative, raw in source_payload.items():
        if payload.get(relative) != raw:
            raise ValueError(f"Packaged source differs: {relative}")
    return {"crc": "PASS", "paths": "PASS", "hashes": "PASS",
            "manifest_files": len(manifest), "files": len(payload),
            "issued_files_count": len(original),
            "protected_baseline_bytes": "PASS", "source_bytes": "PASS"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    source_root = repo / PACKAGE
    artifacts = repo / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    errors, records, passes = [], [], []
    return_root = source_root / "return"
    evidence = return_root / "evidence" / "verification"
    if evidence.exists():
        shutil.rmtree(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    raw_zip = (repo / ISSUED_ZIP).read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(raw_zip)).encode() + b"\0" + raw_zip).hexdigest()
    if git_blob != ISSUED_GIT_BLOB:
        raise ValueError("Issued ZIP changed from the approved repository blob")
    original = archive_files(raw_zip)
    require(len(original) == 57, "Issued archive must contain 57 files", errors)
    source_payload = files(source_root)
    for relative, raw in original.items():
        if not allowed(relative):
            require(source_payload.get(relative) == raw,
                    f"Protected file changed or missing: {relative}", errors)
    for relative in source_payload:
        require(relative in original or allowed(relative),
                f"New file outside the allowed paths: {relative}", errors)
    required_candidate = {"candidate/first_sm06_language.py", "candidate/README.md"}
    required_candidate.update(f"candidate/packs/{x}.json" for x in LOCALES)
    for relative in sorted(required_candidate):
        require(relative in source_payload, f"Candidate file missing: {relative}", errors)
    inventory = test_inventory(source_root)
    require(bool(inventory), "Candidate test inventory is empty", errors)
    for document in ("SEMANTIC_REVIEW.md",):
        require((return_root / document).is_file(), f"Missing {document}", errors)
    version, _ = run_command(repo, evidence, "python_version",
                              [sys.executable, "-VV"], records)
    require(version["exit_code"] == 0, "Python version command failed", errors)
    require(sys.version_info[:2] == (3, 12), "Verification requires Python 3.12", errors)
    git_version, _ = run_command(repo, evidence, "git_version", ["git", "--version"], records)
    require(git_version["exit_code"] == 0, "Git version command failed", errors)
    commit, commit_text = run_command(repo, evidence, "git_commit",
                                      ["git", "rev-parse", "HEAD"], records)
    require(commit["exit_code"] == 0, "Git commit lookup failed", errors)
    if errors:
        print("Input validation failed; commands below remain factual diagnostics.", flush=True)
    with tempfile.TemporaryDirectory(prefix="sm06-verification-") as temporary:
        for number in (1, 2):
            clean = Path(temporary) / f"pass{number}" / PACKAGE
            materialize(clean, original)
            # Overlay only files the task authorizes the candidate to change.
            materialize(clean, {p: b for p, b in source_payload.items() if allowed(p)})
            current = {"pass": number, "fresh_extraction": True, "commands": []}
            for stage, arguments in (
                ("package_before", [sys.executable, "-B", "PACKAGE_CHECK.py"]),
                ("cp0", [sys.executable, "-B", "acceptance/run.py", "cp0"]),
                ("cp1", [sys.executable, "-B", "acceptance/run.py", "cp1"]),
                ("package_after", [sys.executable, "-B", "PACKAGE_CHECK.py"]),
            ):
                label = f"pass{number}_{stage}"
                record, text = run_command(clean, evidence, label, arguments, records)
                current["commands"].append(label)
                require(record["exit_code"] == 0, f"{label} exited {record['exit_code']}", errors)
                if stage.startswith("package"):
                    try:
                        result = json.loads(text.strip())
                    except ValueError:
                        result = {}
                    require(result.get("status") == "PASS"
                            and result.get("protected_files") == 55
                            and result.get("errors") == [],
                            f"{label}: protected 55-file PASS was not confirmed", errors)
                else:
                    counts = record["unittest_counts"]
                    require(not record["skips_found"], f"{label}: skipped tests", errors)
                    if stage == "cp0":
                        require(len(counts) == 6 and sum(counts) == 152
                                and all(counts), f"{label}: expected six suites / 152 tests", errors)
                    else:
                        require(len(counts) == 2 and counts[0] == 13 and counts[1] > 0,
                                f"{label}: expected 13 frozen tests plus nonempty own suite", errors)
            clean_payload = files(clean)
            for relative, raw in original.items():
                if not allowed(relative):
                    require(clean_payload.get(relative) == raw,
                            f"pass{number} changed protected file: {relative}", errors)
            for relative, raw in source_payload.items():
                if allowed(relative):
                    require(clean_payload.get(relative) == raw,
                            f"pass{number} mutated submitted file: {relative}", errors)
            passes.append(current)
    write_json(evidence / "commands.json", records)
    write_json(evidence / "candidate_test_inventory.json", inventory)
    # The issued provenance remains byte-for-byte historical evidence.
    status = "PASS" if not errors else "FAIL"
    metadata = {
        "task": "SM-06", "revision": "R1", "status": status,
        "source_commit": commit_text.strip(),
        "issued_zip": {"file": ISSUED_ZIP, "git_blob": git_blob,
                       "sha256": sha256(raw_zip), "bytes": len(raw_zip)},
        "python": sys.version, "verification_passes": passes,
        "protected_files": 55, "issued_files": len(original),
        "candidate_test_methods": len(inventory),
        "errors": errors,
        "limits": {
            "independent_language_acceptance": "NOT_RUN",
            "trusted_producer_acceptance": "NOT_RUN",
            "production_installation": "NOT_RUN",
            "complete_SM06_integration": "NOT_RUN",
            "outbound_operations": "NOT_RUN",
            "issued_provenance": "HISTORICAL_UNCHANGED",
        },
    }
    write_json(return_root / "RESULT.json", metadata)
    command_rows = []
    for item in records:
        command_rows.append(f"| {item['label']} | {item['exit_code']} | "
                            f"{item['unittest_counts']} | {item['stdout']} / {item['stderr']} |")
    report = f"""# SM-06 R1 return report

Status: **{status}**. Python: {sys.version.split()[0]}.
Source Git commit: {commit_text.strip()}.

Two fresh extractions of the issued ZIP were overlaid with only permitted
candidate/return files. CP0 and CP1 were executed in each extraction, bracketed
by PACKAGE_CHECK. Every command below was actually invoked; stdout, stderr,
argv, working directory, timestamps and exit codes are retained separately.
The original provenance directory is issued historical evidence, not a fresh run.

## Commands and actual results

| Command label | Exit code | Unittest suite counts | Raw logs |
|---|---:|---|---|
{chr(10).join(command_rows)}

## Reproduce

From the repository root with Python 3.12 and Git:
    python -B SM06_Dmitry_R1/return/verify_sm06.py --repo .

For direct execution after extracting the return ZIP:
    cd SM06_Dmitry_R1
    python -B PACKAGE_CHECK.py
    python -B acceptance/run.py cp0
    python -B acceptance/run.py cp1

The candidate ABI is candidate/first_sm06_language.py. Consult CONTRACT.md
and candidate/README.md before connecting trusted producers. An independent
integration owner must compare snapshot hashes before copying only accepted
module/packs into an approved location. Snapshot drift requires coordination,
not overwriting a working SOURCE. Use an offline recorder for save_materials;
a real callback may enqueue sales.send. This return
does not alter production configuration or install an outbound sender.

## Recovery

Keep the issued ZIP and its recorded SHA-256. To recover a test environment,
extract that ZIP into a fresh directory and overlay the permitted candidate
and return files from this archive. Re-run PACKAGE_CHECK and both checkpoints.
Do not restore by overwriting a shared runtime. A production installation
requires a prior backup/manifest and an independently verified scoped restore;
that installation/restore gate is NOT_RUN here. The legacy external RU seam
identified in INTEGRATION.md remains the integration owner’s responsibility.
No live state is changed here.

## Scope and limits

A PASS requires all 55 manifest-protected files to remain unchanged; actual
results are in the package-check logs and RESULT.json. Language pack texts are
educational samples; internal semantic review is in SEMANTIC_REVIEW.md.
Independent native-language acceptance, trusted-producer acceptance,
production installation and complete SM-06 integration are NOT_RUN.
No production credentials, database, dispatcher or outbound connection is used.

Errors detected: {json.dumps(errors, ensure_ascii=False)}
"""
    (return_root / "REPORT.md").write_text(report, encoding="utf-8")
    trace = """# Requirement → code → test → raw log

Normative requirements are in CONTRACT.md (steps 1–6), TASK_ORDER.md and
INTEGRATION.md. Each frozen test reference below is
acceptance/run.py::Acceptance.<test_method>. Every listed CP1 assertion executes
in both pass1_cp1.stderr and pass2_cp1.stderr; stdout is retained alongside.
An own-test inventory follows and supplements these immutable tests.

| Requirement | Implementation | Frozen test / evidence |
|---|---|---|
| Five locales × five kinds, nonempty subject/body, no fact IDs | candidate/packs/*.json | test_pack_shape_all5_kinds_and_no_fact_claim_ids |
| Exact real-chain text, version, one save and input immutability for all 25 cases | prepare_language_materials → actual F130 | test_all25_actual_chain_exact_once_immutable |
| Evidence priority and en-GB default | select_language | test_selection_priority_and_default |
| Unsupported explicit choice fails without trying lower evidence or saving | select_language | test_explicit_unavailable_no_downgrade_zero_save |
| Exact evidence shape, invalid values, mixed/unknown handling | select_language | test_invalid_evidence_country_mixed_unknown_zero_save |
| Registry/binding default and version equality | select_language + real F105/F106 | test_registry_binding_scope_mismatch |
| Drift, missing template, blank body; original errors, zero save | prepare_language_materials → actual F130 | test_drift_missing_blank_zero_save_passthrough |
| Malformed loaded registry produces F106 error, not raw KeyError | select_language + real F106 | test_malformed_registry_no_raw_keyerror |
| Unapproved facts, blank subject and naive now cannot save | actual F105/F106/F130 | test_unapproved_fact_blank_subject_invalid_now_zero_save |
| Dependency exception object identity and zero save | prepare_language_materials → actual F130 | test_dependency_exception_identity |
| Missing permitted English default fails closed | select_language + real F105 | test_unavailable_english_default_rejects |
| Callback exception object identity, one attempt, no retry | prepare_language_materials → actual F130 | test_callback_exception_identity_and_no_retry |
| Extra synthetic locale works without an enum change | select_language | test_synthetic_extra_locale_no_hardcoded_enum |
| Existing dependencies unchanged and compatible | reference/ with frozen CP0 | pass1_cp0.stderr / pass2_cp0.stderr: required six suites / 152 tests |
| Protected bytes preserved before/after tests | PACKAGE_CHECK.py and issued-ZIP comparison | pass{1,2}_package_{before,after}.stdout |
| Nonempty own tests and no skipped suites | verify_sm06.py result parsing | commands.json; RESULT.json |
| Complete ZIP, exact paths, SHA-256 coverage, reproducibility | verify_sm06.py | SHA256SUMS.json; external SM06_RETURN_R1.validation.json |
| Equivalent neutral sample intent in five languages | candidate/packs/*.json | SEMANTIC_REVIEW.md: internal self-review; independent language QA NOT_RUN |
| Trusted producers, installation, restore and full runtime | Separate integration-owner acceptance | NOT_RUN; see INTEGRATION.md |

All raw files named above are in return/evidence/verification/.
A PASS requires every executed command and mandatory count/no-skip check to pass;
the table describes required coverage, while RESULT.json records actual results.

## Submitted candidate tests

"""
    trace += "\n".join(f"- {item}" for item in inventory) + "\n"
    (return_root / "TRACEABILITY.md").write_text(trace, encoding="utf-8")
    # Include a complete list of changes without making manifest self-hashes.
    (return_root / "SHA256SUMS.json").write_text("{}\n", encoding="utf-8")
    payload = files(source_root)
    changed = sorted(p for p, raw in payload.items() if original.get(p) != raw)
    metadata["changed_files"] = changed
    report += "\n## Changed files relative to the issued ZIP\n\n"
    report += "\n".join(f"- {p}" for p in changed) + "\n"
    (return_root / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(return_root / "RESULT.json", metadata)
    payload = files(source_root)
    write_json(return_root / "SHA256SUMS.json",
               {p: sha256(raw) for p, raw in payload.items() if p != MANIFEST})
    payload = files(source_root)
    artifact = artifacts / "SM06_RETURN_R1.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, raw in sorted(payload.items()):
            member = zipfile.ZipInfo(f"{PACKAGE}/{relative}")
            member.external_attr = (stat.S_IFREG | 0o644) << 16
            member.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(member, raw)
    validation = {"status": status, "errors": errors, "checks": []}
    final_bytes = artifact.read_bytes()
    # Independently re-open and inspect the finished ZIP twice.
    for number in (1, 2):
        try:
            verified = archive_files(final_bytes)
            check = validate_finished(verified, original, payload)
            check["pass"] = number
            validation["checks"].append(check)
        except (ValueError, KeyError, zipfile.BadZipFile) as error:
            validation["status"] = "FAIL"
            validation["errors"].append(f"Final ZIP check {number}: {error}")
            validation["checks"].append({"pass": number, "status": "FAIL", "error": str(error)})
    validation["artifact"] = {"path": artifact.name, "bytes": len(final_bytes),
                               "sha256": sha256(final_bytes)}
    write_json(artifacts / "SM06_RETURN_R1.validation.json", validation)
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
