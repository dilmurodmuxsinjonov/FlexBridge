"""Capture current pytest evidence without overwriting prior reviews."""
from pathlib import Path
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
OUTPUT=Path(__file__).resolve().parent

if __name__=='__main__':
    started=time.time()
    result=subprocess.run([sys.executable,'-m','pytest',str(ROOT/'backend'),'-q','--tb=short',
        '--junitxml='+str(OUTPUT/'junit.xml')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (OUTPUT/'pytest_stdout.txt').write_text(result.stdout,encoding='utf-8')
    (OUTPUT/'pytest_stderr.txt').write_text(result.stderr,encoding='utf-8')
    summary={'exit_code':result.returncode,'elapsed_seconds':round(time.time()-started,2)}
    if (OUTPUT/'junit.xml').exists():
        suites=list(ET.parse(OUTPUT/'junit.xml').getroot().iter('testsuite'))
        for key in ('tests','errors','failures','skipped'):summary[key]=sum(int(s.get(key,0)) for s in suites)
    (OUTPUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(result.stdout[-7000:]);print(json.dumps(summary))
    raise SystemExit(result.returncode)
