"""Verify protected bytes and reject candidate writes outside the allowlist."""
from pathlib import Path
import hashlib,json,re,sys
p=Path(__file__).resolve().parent
m=json.loads((p/'SHA256SUMS_PROTECTED.json').read_text())
errors=[]
for path,digest in m.items():
 f=p/path
 if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=digest:errors.append('protected mismatch: '+path)
allowed=re.compile(r'(candidate/first_sm06_language\.py|candidate/packs/(en-GB|ru-RU|es-ES|da-DK|uk-UA)\.json|candidate/tests/.+|candidate/README\.md|return/.+)')
for f in p.rglob('*'):
 if not f.is_file():continue
 path=f.relative_to(p).as_posix()
 if '__pycache__' in f.parts:continue
 if path not in m and path!='SHA256SUMS_PROTECTED.json' and not allowed.fullmatch(path):errors.append('outside allowlist: '+path)
print(json.dumps({'status':'FAIL' if errors else 'PASS','protected_files':len(m),'errors':errors},indent=2))
raise SystemExit(bool(errors))
