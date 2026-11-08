"""Capture existing pytest and its REV-002 diagnostic, preserving committed review data."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
old_relative="reviews/2026-11-07/recheck_984fec5/recheck_results.json"
old_file=ROOT/old_relative
committed=subprocess.run(["git","cat-file","--filters","HEAD:"+old_relative],cwd=ROOT,capture_output=True,check=True).stdout
env=dict(os.environ,FLEXBRIDGE_DATABASE_URL="sqlite:///"+(ROOT/"backend/.data"/f"rev003_suite_{uuid4().hex}.sqlite3").as_posix(),PYTHONIOENCODING="utf-8")
try:
    result=subprocess.run([sys.executable,"-m","pytest","-q"],cwd=ROOT/"backend",env=env,
        capture_output=True,text=True,encoding="utf-8")
    (OUT/"pytest_stdout.txt").write_text(result.stdout,encoding="utf-8")
    (OUT/"pytest_stderr.txt").write_text(result.stderr,encoding="utf-8")
    old_data=json.loads(old_file.read_text(encoding="utf-8"))
    (OUT/"previous_30_checks.json").write_text(json.dumps(old_data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    summary={"commit":"1460ab8","pytest_exit":result.returncode,
        "pytest_summary":re.findall(r"^.*\d+ passed.*$",result.stdout,re.M),
        "previous_diagnostic_checks":old_data["checks"],"previous_diagnostic_defects_observed":old_data["defects_observed"],
        "previous_diagnostic_improvements_confirmed":old_data["improvements_confirmed"],
        "note":"Existing suite includes REV-002 diagnostic; original assertions unchanged. Generated historical report restored to committed content using Git checkout filters."}
    (OUT/"suite_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
finally:
    old_file.write_bytes(committed)
