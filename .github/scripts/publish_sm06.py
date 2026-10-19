"""Publish verified return files to the tested feature branch only."""
import base64
import hashlib
import json
import os
from pathlib import Path
import urllib.request

REPO = os.environ["GITHUB_REPOSITORY"]
HEAD = os.environ["GITHUB_SHA"]
BRANCH = os.environ["GITHUB_REF_NAME"]
if BRANCH != "feat/sm06-language-r1":
    raise SystemExit("Publication is limited to the SM06 feature branch")
ROOT = Path.cwd()
validation = json.loads((ROOT / "artifacts/SM06_RETURN_R1.validation.json").read_text())
result = json.loads((ROOT / "SM06_Dmitry_R1/return/RESULT.json").read_text())
if validation["status"] != "PASS" or result["status"] != "PASS":
    raise SystemExit("Refusing to publish a failed candidate")
if result["source_commit"] != HEAD:
    raise SystemExit("Return source commit does not match the tested checkout")
zip_path = ROOT / "artifacts/SM06_RETURN_R1.zip"
if hashlib.sha256(zip_path.read_bytes()).hexdigest() != validation["artifact"]["sha256"]:
    raise SystemExit("Final artifact hash mismatch")

def api(method, path, data=None):
    request = urllib.request.Request(
        "https://api.github.com/repos/" + REPO + path,
        data=None if data is None else json.dumps(data).encode("utf-8"),
        method=method,
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)

if api("GET", "/git/ref/heads/" + BRANCH)["object"]["sha"] != HEAD:
    raise SystemExit("Feature branch changed; refusing to overwrite it")
base_tree = api("GET", "/git/commits/" + HEAD)["tree"]["sha"]
tree = []
for path in sorted((ROOT / "SM06_Dmitry_R1/return").rglob("*")):
    if path.is_file() and not path.is_symlink():
        tree.append({
            "path": path.relative_to(ROOT).as_posix(),
            "mode": "100644", "type": "blob",
            "content": path.read_text(encoding="utf-8"),
        })
for name in ("SM06_RETURN_R1.zip", "SM06_RETURN_R1.validation.json"):
    path = ROOT / "artifacts" / name
    if name.endswith(".zip"):
        blob = api("POST", "/git/blobs", {
            "encoding": "base64",
            "content": base64.b64encode(path.read_bytes()).decode("ascii"),
        })
        entry = {"sha": blob["sha"]}
    else:
        entry = {"content": path.read_text(encoding="utf-8")}
    tree.append({"path": "artifacts/" + name, "mode": "100644", "type": "blob", **entry})
new_tree = api("POST", "/git/trees", {"base_tree": base_tree, "tree": tree})
commit = api("POST", "/git/commits", {
    "message": "Record verified SM06 return archive and raw acceptance evidence",
    "parents": [HEAD], "tree": new_tree["sha"],
})
# Fast-forward only: a concurrent branch update cannot be silently overwritten.
api("PATCH", "/git/refs/heads/" + BRANCH, {"sha": commit["sha"], "force": False})
print("Published verified return on feature branch:", commit["sha"])
print("Return ZIP SHA-256:", validation["artifact"]["sha256"])
