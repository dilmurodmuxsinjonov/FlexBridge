"""Run unchanged REV-001 probe logic with only its report destination redirected.

The original tool exits 1 whenever not all defects are observed; this is diagnostic
semantics, not a product regression-test pass/fail status.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
original = ROOT / "reviews/2026-11-07/reproduce_findings.py"
env = dict(os.environ, PYTHONPATH=str(ROOT / "backend"), PYTHONIOENCODING="utf-8",
    FLEXBRIDGE_DATABASE_URL="sqlite:///" + (ROOT / "backend/.data" / f"rev002_original_{uuid4().hex}.sqlite3").as_posix())
source = original.read_text(encoding="utf-8")
old = 'out = Path(__file__).with_name("probe_results.json")'
assert source.count(old) == 1
source = source.replace(old, 'out = Path(__file__).parent / "recheck_984fec5" / "original_probe_results.json"')
loader = "from pathlib import Path\np=" + repr(str(original)) + "\nsource=" + repr(source) + "\nexec(compile(source,p,'exec'),{'__file__':p,'__name__':'__main__'})"
result = subprocess.run([sys.executable,"-c",loader], cwd=ROOT, env=env, capture_output=True,text=True,encoding="utf-8")
(OUT / "original_probe_stdout.txt").write_text(result.stdout,encoding="utf-8")
(OUT / "original_probe_stderr.txt").write_text(result.stderr,encoding="utf-8")
report = json.loads((OUT / "original_probe_results.json").read_text(encoding="utf-8"))
summary = {"command":"original REV-001 probes; report destination redirected only", "exit_code":result.returncode,
    "probes":report["probes"],"defects_observed":report["defects_observed"],
    "note":"No probe conditions changed. A false observation can mean a precondition was no longer reached."}
(OUT / "original_run_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
