# SM-06 R1 return report

Status: **PASS**. Python: 3.12.15.
Source Git commit: 5aab8a338621828636b3d9346ed449f0764d3cde.

Two fresh extractions of the issued ZIP were overlaid with only permitted
candidate/return files. CP0 and CP1 were executed in each extraction, bracketed
by PACKAGE_CHECK. Every command below was actually invoked; stdout, stderr,
argv, working directory, timestamps and exit codes are retained separately.
The original provenance directory is issued historical evidence, not a fresh run.

## Commands and actual results

| Command label | Exit code | Unittest suite counts | Raw logs |
|---|---:|---|---|
| python_version | 0 | [] | return/evidence/verification/python_version.stdout / return/evidence/verification/python_version.stderr |
| git_version | 0 | [] | return/evidence/verification/git_version.stdout / return/evidence/verification/git_version.stderr |
| git_commit | 0 | [] | return/evidence/verification/git_commit.stdout / return/evidence/verification/git_commit.stderr |
| pass1_package_before | 0 | [] | return/evidence/verification/pass1_package_before.stdout / return/evidence/verification/pass1_package_before.stderr |
| pass1_cp0 | 0 | [32, 44, 32, 30, 5, 9] | return/evidence/verification/pass1_cp0.stdout / return/evidence/verification/pass1_cp0.stderr |
| pass1_cp1 | 0 | [13, 28] | return/evidence/verification/pass1_cp1.stdout / return/evidence/verification/pass1_cp1.stderr |
| pass1_package_after | 0 | [] | return/evidence/verification/pass1_package_after.stdout / return/evidence/verification/pass1_package_after.stderr |
| pass2_package_before | 0 | [] | return/evidence/verification/pass2_package_before.stdout / return/evidence/verification/pass2_package_before.stderr |
| pass2_cp0 | 0 | [32, 44, 32, 30, 5, 9] | return/evidence/verification/pass2_cp0.stdout / return/evidence/verification/pass2_cp0.stderr |
| pass2_cp1 | 0 | [13, 28] | return/evidence/verification/pass2_cp1.stdout / return/evidence/verification/pass2_cp1.stderr |
| pass2_package_after | 0 | [] | return/evidence/verification/pass2_package_after.stdout / return/evidence/verification/pass2_package_after.stderr |

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

Errors detected: []

## Changed files relative to the issued ZIP

- candidate/README.md
- candidate/first_sm06_language.py
- candidate/packs/da-DK.json
- candidate/packs/en-GB.json
- candidate/packs/es-ES.json
- candidate/packs/ru-RU.json
- candidate/packs/uk-UA.json
- candidate/tests/test_sm06.py
- return/REPORT.md
- return/RESULT.json
- return/SEMANTIC_REVIEW.md
- return/SHA256SUMS.json
- return/TRACEABILITY.md
- return/evidence/verification/candidate_test_inventory.json
- return/evidence/verification/commands.json
- return/evidence/verification/git_commit.command.json
- return/evidence/verification/git_commit.stderr
- return/evidence/verification/git_commit.stdout
- return/evidence/verification/git_version.command.json
- return/evidence/verification/git_version.stderr
- return/evidence/verification/git_version.stdout
- return/evidence/verification/pass1_cp0.command.json
- return/evidence/verification/pass1_cp0.stderr
- return/evidence/verification/pass1_cp0.stdout
- return/evidence/verification/pass1_cp1.command.json
- return/evidence/verification/pass1_cp1.stderr
- return/evidence/verification/pass1_cp1.stdout
- return/evidence/verification/pass1_package_after.command.json
- return/evidence/verification/pass1_package_after.stderr
- return/evidence/verification/pass1_package_after.stdout
- return/evidence/verification/pass1_package_before.command.json
- return/evidence/verification/pass1_package_before.stderr
- return/evidence/verification/pass1_package_before.stdout
- return/evidence/verification/pass2_cp0.command.json
- return/evidence/verification/pass2_cp0.stderr
- return/evidence/verification/pass2_cp0.stdout
- return/evidence/verification/pass2_cp1.command.json
- return/evidence/verification/pass2_cp1.stderr
- return/evidence/verification/pass2_cp1.stdout
- return/evidence/verification/pass2_package_after.command.json
- return/evidence/verification/pass2_package_after.stderr
- return/evidence/verification/pass2_package_after.stdout
- return/evidence/verification/pass2_package_before.command.json
- return/evidence/verification/pass2_package_before.stderr
- return/evidence/verification/pass2_package_before.stdout
- return/evidence/verification/python_version.command.json
- return/evidence/verification/python_version.stderr
- return/evidence/verification/python_version.stdout
- return/verify_sm06.py
