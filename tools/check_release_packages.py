#!/usr/bin/env python3
"""Verify release assets against an exact Git commit without extracting ZIPs."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = 'custom_components/solar_pilot/'
RETIRED = {COMPONENT + name for name in (
    'dhw.py', 'dhw_config.py', 'dhw_runtime.py', 'dhw_schedule.py',
    'thermal_runtime.py', 'thermal_climate.py')}


class PackageError(ValueError):
    """A package cannot be proven to contain the requested source."""


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def tracked_source(repo, source_ref):
    sha = git(repo, 'rev-parse', '--verify', source_ref + '^{commit}').decode().strip()
    source = {}
    for row in git(repo, 'ls-tree', '-rz', '--full-tree', sha).split(b'\0'):
        if not row:
            continue
        metadata, raw_path = row.split(b'\t', 1)
        _mode, kind, blob = metadata.split()
        if kind != b'blob':
            raise PackageError('Unverifiable non-blob tracked source: ' + raw_path.decode())
        path = raw_path.decode('utf-8')
        source[path] = git(repo, 'cat-file', 'blob', blob.decode())
    return sha, source


def version_from_source(source):
    try:
        version = json.loads(source[COMPONENT + 'manifest.json'])['version']
        constants = ast.parse(source[COMPONENT + 'const.py'].decode())
        declared = [ast.literal_eval(n.value) for n in constants.body
                    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'VERSION' for t in n.targets)]
        first = source[COMPONENT + 'frontend/solar-pilot-card.js'].decode().splitlines()[0]
    except (KeyError, ValueError, SyntaxError, UnicodeError, TypeError) as err:
        raise PackageError('Missing or invalid source version declarations') from err
    if not isinstance(version, str) or declared != [version] or not first.startswith('/* SolarPilot ' + version + '.'):
        raise PackageError('Manifest/const/frontend header versions differ')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z]+\.\d+)?', version):
        raise PackageError('Invalid release version')
    if RETIRED & source.keys():
        raise PackageError('Retired native Panasonic controller in tracked release source')
    return version


def digest(path):
    body = path.read_bytes()
    return {'name': path.name, 'size': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def verify_zip(path, expected, sha, *, require_source_comment=False):
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            names = [item.filename for item in members]
            if len(names) != len(set(names)):
                raise PackageError('Duplicate ZIP members: ' + path.name)
            directories = {str(parent) + '/' for name in expected for parent in PurePosixPath(name).parents if str(parent) != '.'}
            for item in members:
                name = item.filename
                if name.startswith('/') or '..' in PurePosixPath(name).parts:
                    raise PackageError('Unsafe ZIP member path: ' + name)
                if item.is_dir() and name not in directories:
                    raise PackageError('Unexpected ZIP directory: ' + name)
            actual = {item.filename for item in members if not item.is_dir()}
            if RETIRED & actual:
                raise PackageError('Retired native Panasonic controller in ZIP: ' + path.name)
            if actual != expected.keys():
                missing, extra = sorted(expected.keys() - actual), sorted(actual - expected.keys())
                raise PackageError(f'ZIP source file set differs: {path.name}; missing={missing}; extra={extra}')
            if (require_source_comment and archive.comment != sha.encode()) or (archive.comment and archive.comment != sha.encode()):
                raise PackageError('ZIP source SHA header differs: ' + path.name)
            for name, body in expected.items():
                if archive.read(name) != body:
                    raise PackageError('ZIP member bytes differ from Git source: ' + name)
    except (zipfile.BadZipFile, OSError, RuntimeError) as err:
        raise PackageError('Unreadable release ZIP: ' + str(path)) from err
    return digest(path)


def verify_release(repo, source_ref, hacs, local, *, download_dir=None, expected_sha=None):
    sha, source = tracked_source(repo, source_ref)
    if expected_sha is not None and sha != expected_sha:
        raise PackageError('Resolved source commit differs from expected source SHA')
    version = version_from_source(source)
    if source_ref.startswith('v') and source_ref != 'v' + version:
        raise PackageError('Release tag differs from declared version')
    label = version.split('-')[-1].upper().replace('.', '')
    doc_names = [label + '_INSTELLEN.md', 'TESTRESULTATEN_' + label + '.md']
    packages = {
        f'SolarPilot-v{version}-GitHub-HACS.zip': Path(hacs),
        f'SolarPilot-v{version}-local.zip': Path(local),
    }
    for name, path in packages.items():
        if path.name != name:
            raise PackageError('Package filename differs from release version: ' + path.name)
    local_source = {name: body for name, body in source.items() if name.startswith(COMPONENT)
                    and not {'userfiles', '__pycache__', '.pytest_cache'} & set(PurePosixPath(name).parts)}
    assets = [verify_zip(Path(hacs), source, sha, require_source_comment=True),
              verify_zip(Path(local), local_source, sha)]
    for name in doc_names:
        source_name = 'docs/' + name
        embedded_name = COMPONENT + source_name
        if source_name not in source or source.get(embedded_name) != source[source_name]:
            raise PackageError('Standalone documentation or exact component mirror missing: ' + name)
        path = Path(repo) / source_name
        if path.read_bytes() != source[source_name]:
            raise PackageError('Standalone documentation differs from Git source: ' + name)
        assets.append(digest(path))
    if download_dir is not None:
        directory = Path(download_dir)
        files = [p for p in directory.iterdir() if p.is_file()]
        expected_names = {item['name'] for item in assets}
        if {p.name for p in files} != expected_names or any(p.is_symlink() for p in files):
            raise PackageError('Downloaded release must contain the exact four assets')
        verify_zip(directory / Path(hacs).name, source, sha, require_source_comment=True)
        verify_zip(directory / Path(local).name, local_source, sha)
        downloaded = []
        for item in assets:
            proof = digest(directory / item['name'])
            if proof != item:
                raise PackageError('Downloaded asset differs from verified upload: ' + item['name'])
            downloaded.append(proof)
        assets = downloaded
    return {'source_sha': sha, 'version': version, 'download_verified': download_dir is not None,
            'assets': assets}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--source-ref', default='HEAD')
    parser.add_argument('--expected-sha')
    parser.add_argument('--hacs', type=Path, required=True)
    parser.add_argument('--local', type=Path, required=True)
    parser.add_argument('--download-dir', type=Path)
    args = parser.parse_args()
    try:
        proof = verify_release(args.repo, args.source_ref, args.hacs, args.local,
                               download_dir=args.download_dir, expected_sha=args.expected_sha)
    except (PackageError, subprocess.CalledProcessError, OSError) as err:
        raise SystemExit('RELEASE PROOF FAILED: ' + str(err)) from err
    print(json.dumps(proof, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
