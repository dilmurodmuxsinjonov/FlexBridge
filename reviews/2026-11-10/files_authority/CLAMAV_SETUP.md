# Local antivirus tooling follow-up2026-11-10

Existing ClamAV1.4.6 tools had no signature databases. Official freshclam used
D:/Codex/ClamAV/freshclam.conf and completed exit0, creating main/daily/bytecode.cvd
under D:/Codex/ClamAV/database. Raw updater logs stay in D:/Codex/ClamAV/logs and
are not public evidence (network identifiers omitted).

D:/Codex/Setup/check_clamav_local.py started only its own temporary clamd process
on127.0.0.1 random port using those databases. The actual app.adapters.antivirus
INSTREAM adapter accepted a generated benign431-byte PDF; PING/PONG passed. The
owned daemon was stopped in finally. No system service installed, no Windows
security setting changed, no sample malware or sensitive upload transmitted.
This proves local adapter/dependency setup with benign data only, not detection
coverage, ongoing updates, Linux production sandbox, actual full pipeline/live/pilot.
PR58's prior7 S3 integration tests explicitly used AV doubles and remain so; this
separate observation does not rewrite their scope.
