"""Read-only publication hygiene gate. Not a security/acceptance certification."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    paths=subprocess.run(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT,
        capture_output=True,check=True).stdout.decode('utf-8').split('\0')
    errors=[];checked=0
    patterns={
        'provider credential':re.compile(r'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{24,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16})'),
        'private key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'captured secret':re.compile(r'''(?i)["'](?:access_token|mfa_ticket|verification_token|reset_token|totp_secret|ceremony_token)["']\s*:\s*["']([^"'\r\n]{12,})["']'''),
    }
    for name in sorted(set(paths)):
        if not name:continue
        file=ROOT/name
        if not file.is_file():continue
        if '.data' in file.parts or file.name=='.env' or (file.name.startswith('.env.') and file.name!='.env.example'):
            errors.append({'file':name,'reason':'runtime environment/state in publish set'});continue
        if file.suffix.lower() not in ('.py','.md','.json','.txt','.xml','.yaml','.yml','.toml','.ini','.example','.sql','.csv'):continue
        try:source=file.read_text(encoding='utf-8')
        except UnicodeError:continue
        checked+=1
        for reason,pattern in patterns.items():
            for match in pattern.finditer(source):
                value=match.group(1) if reason=='captured secret' else ''
                if reason=='captured secret' and any(x in value.upper() for x in ('REDACTED','PLACEHOLDER','EXAMPLE','TEST-','DUMMY','INVALID')):continue
                errors.append({'file':name,'line':source.count('\n',0,match.start())+1,'reason':reason})
        if name.startswith('backend/app/') and file.suffix=='.py':
            for node in ast.walk(ast.parse(source)):
                if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value in {
                    'child-org','VALID_PROVIDER_WEBHOOK_SIGNATURE','broken non-PDF'}:
                    errors.append({'file':name,'line':node.lineno,'reason':'runtime probe-specific literal'})
    manifest=ROOT/'reviews/2026-11-07/codex_fix/legacy_tests/manifest.json'
    for entry in json.loads(manifest.read_text(encoding='utf-8')):
        archive=ROOT/Path(entry['archive'].replace('\\','/'))
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=entry['sha256']:
            errors.append({'file':entry['archive'],'reason':'legacy archive hash mismatch'})
    result={'files_checked':checked,'errors':errors,'scope':'publication hygiene only; no live credential rotation or acceptance certification'}
    print(json.dumps(result,indent=2))
    return 1 if errors else 0


if __name__=='__main__':raise SystemExit(main())
