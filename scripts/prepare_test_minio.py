"""Install a pinned publisher binary for isolated localhost tests, never a service.

This matches compose's existing version; it is not a production support assessment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
from urllib.request import Request, urlopen

RELEASE = 'RELEASE.2025-02-18T16-25-55Z'
SOURCES = {
    'Windows': ('minio.windows-amd64.' + RELEASE + '.exe',
        '54761eabfed872d1b977b9bc2cad4a105b5eedafbe2f810a951c2941fcc70e77'),
    'Linux': ('minio.linux-amd64.' + RELEASE,
        '46ee8ac67860b3816f80e47c2220dc06b12ee257e65689639aa74ada0c4ad5f3'),
}


def prepare(directory):
    system = platform.system()
    if system not in SOURCES or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('Pinned test binary supports only Windows/Linux AMD64')
    name, expected = SOURCES[system]
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / ('minio.exe' if system == 'Windows' else 'minio')
    url = f'https://github.com/minio/minio/releases/download/{RELEASE}/{name}'
    if not binary.exists() or hashlib.sha256(binary.read_bytes()).hexdigest() != expected:
        partial = directory / (binary.name + '.download')
        with urlopen(Request(url, headers={'User-Agent': 'FlexBridge-test-installer'}), timeout=60) as response, partial.open('wb') as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        if hashlib.sha256(partial.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Pinned MinIO test binary checksum mismatch; binary not installed')
        partial.replace(binary)
    if system == 'Linux':
        binary.chmod(0o700)
    (directory / 'download.json').write_text(json.dumps({
        'source': url, 'sha256': expected, 'release': RELEASE,
        'scope': 'localhost integration only; not a production support recommendation',
    }, indent=2) + '\n', encoding='utf-8')
    return binary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--github-env', action='store_true')
    args = parser.parse_args()
    binary = prepare(args.directory)
    if args.github_env:
        with Path(os.environ['GITHUB_ENV']).open('a', encoding='utf-8') as output:
            output.write(f'MINIO_TEST_BINARY={binary}\n')
    print(f'Prepared pinned localhost test binary: {binary}')
