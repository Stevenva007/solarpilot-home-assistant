"""Actual Git/ZIP release provenance checks with fictitious disposable sources."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
import pytest

TOOL = Path(__file__).parents[1] / 'tools/check_release_packages.py'
spec = spec_from_file_location('release_package_proof', TOOL)
proof = module_from_spec(spec)
spec.loader.exec_module(proof)
VERSION = '1.0.0-beta.62'


def run(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def rebuild(repo, hacs, local):
    run(repo, 'archive', '--format=zip', '--output=' + str(hacs), 'HEAD')
    with zipfile.ZipFile(local, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((repo / 'custom_components/solar_pilot').rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(repo).as_posix())


@pytest.fixture
def release(tmp_path):
    repo = tmp_path / 'source'; repo.mkdir();run(repo, 'init', '-q')
    content = {
        'README.md': 'Fictitious release\n',
        'custom_components/solar_pilot/manifest.json': '{"version":"' + VERSION + '"}',
        'custom_components/solar_pilot/const.py': 'VERSION = "' + VERSION + '"\n',
        'custom_components/solar_pilot/frontend/solar-pilot-card.js': '/* SolarPilot ' + VERSION + '. */\n',
        'custom_components/solar_pilot/sg_boost.py': '# SG controller fixture\n',
    }
    for name in ('BETA62_INSTELLEN.md', 'TESTRESULTATEN_BETA62.md'):
        content['docs/' + name] = 'Fictitious public release document ' + name + '\n'
        content['custom_components/solar_pilot/docs/' + name] = content['docs/' + name]
    for name, body in content.items():
        path = repo / name; path.parent.mkdir(parents=True, exist_ok=True);path.write_text(body)
    run(repo, 'add', '.');run(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
    hacs = tmp_path / f'SolarPilot-v{VERSION}-GitHub-HACS.zip'
    local = tmp_path / f'SolarPilot-v{VERSION}-local.zip'
    rebuild(repo, hacs, local)
    return repo, hacs, local


def rewrite_zip(path, *, change=None, omit=None, extra=None, comment=None):
    with zipfile.ZipFile(path) as archive:
        entries = [(item.filename, archive.read(item.filename)) for item in archive.infolist()]
        original_comment = archive.comment
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.comment = original_comment if comment is None else comment
        for name, body in entries:
            if name != omit:
                archive.writestr(name, change[1] if change and name == change[0] else body)
        if extra:
            archive.writestr(*extra)


def test_actual_git_archive_and_local_install_assets_have_exact_source_and_four_digests(release, tmp_path):
    repo, hacs, local = release
    expected_sha = run(repo, 'rev-parse', 'HEAD').decode().strip()
    result = proof.verify_release(repo, 'HEAD', hacs, local, expected_sha=expected_sha)
    assert result['source_sha'] == expected_sha and result['version'] == VERSION
    assert len(result['assets']) == 4 and not result['download_verified']
    download = tmp_path / 'download';download.mkdir()
    for item in result['assets']:
        source = hacs if item['name'] == hacs.name else local if item['name'] == local.name else repo / 'docs' / item['name']
        shutil.copyfile(source, download / item['name'])
        assert item['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert item['size'] == source.stat().st_size
    assert proof.verify_release(repo, 'HEAD', hacs, local, download_dir=download)['download_verified']


@pytest.mark.parametrize('corruption', ['missing', 'changed', 'duplicate', 'retired', 'wrong_sha'])
def test_hacs_upload_is_rejected_for_missing_changed_duplicate_retired_or_wrong_source(release, corruption):
    repo, hacs, local = release
    member = 'custom_components/solar_pilot/sg_boost.py'
    if corruption == 'missing':rewrite_zip(hacs, omit=member)
    elif corruption == 'changed':rewrite_zip(hacs, change=(member, b'# stale source'))
    elif corruption == 'duplicate':
        with pytest.warns(UserWarning, match='Duplicate'):
            rewrite_zip(hacs, extra=(member, b'# duplicate'))
    elif corruption == 'retired':rewrite_zip(hacs, extra=('custom_components/solar_pilot/dhw_runtime.py', b'# old writer'))
    else:rewrite_zip(hacs, comment=b'0' * 40)
    with pytest.raises(proof.PackageError):proof.verify_release(repo, 'HEAD', hacs, local)


def test_local_install_archive_must_have_exact_component_tree(release):
    repo, hacs, local = release
    rewrite_zip(local, extra=('README.md', b'wrong install header/tree'))
    with pytest.raises(proof.PackageError, match='file set differs'):
        proof.verify_release(repo, 'HEAD', hacs, local)


@pytest.mark.parametrize('source', ['const', 'frontend', 'retired'])
def test_even_byte_matching_archives_cannot_publish_inconsistent_version_or_retired_source(release, source):
    repo, hacs, local = release
    path = repo / 'custom_components/solar_pilot' / ('const.py' if source == 'const' else 'frontend/solar-pilot-card.js' if source == 'frontend' else 'dhw.py')
    path.write_text('VERSION = "1.0.0-beta.61"\n' if source == 'const' else '/* SolarPilot 1.0.0-beta.61. */' if source == 'frontend' else '# old writer')
    run(repo, 'add', '.');run(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'invalid release fixture')
    rebuild(repo, hacs, local)
    with pytest.raises(proof.PackageError):proof.verify_release(repo, 'HEAD', hacs, local)


def test_downloaded_document_corruption_fails_post_upload_proof(release, tmp_path):
    repo, hacs, local = release
    result = proof.verify_release(repo, 'HEAD', hacs, local)
    download = tmp_path / 'download';download.mkdir()
    for item in result['assets']:
        source = hacs if item['name'] == hacs.name else local if item['name'] == local.name else repo / 'docs' / item['name']
        shutil.copyfile(source, download / item['name'])
    (download / 'BETA62_INSTELLEN.md').write_text('wrong uploaded document')
    with pytest.raises(proof.PackageError, match='differs from verified upload'):
        proof.verify_release(repo, 'HEAD', hacs, local, download_dir=download)


def test_publishing_existing_tag_always_builds_and_verifies_exact_four_assets(release):
    workflow = (TOOL.parents[1] / '.github/workflows/validate.yml').read_text()
    steps = {part.splitlines()[0]: part for part in workflow.split('      - name: ')[1:]}
    for name in ('Create release packages', 'Verify exact source and four release assets before upload',
                 'Download and verify published four assets against the exact tag'):
        assert '        if:' not in steps[name], name
    assert "if: steps.existing.outputs.exists != 'true'" in steps['Create tag and GitHub prerelease']
    download = steps['Download and verify published four assets against the exact tag']
    assert '--source-ref "${TAG}" --expected-sha "${SOURCE_SHA}"' in download
    assert '--download-dir "${release_download_dir}"' in download
    assert download.count('--pattern ') == 4
    assert 'mktemp -d' in download

    # Run the actual shipped local-package builder twice. Worktree changes,
    # untracked files and checkout mtimes cannot alter its committed payload.
    repo, hacs, _local = release
    embedded = steps['Create release packages'].split("          python - <<'PY'\n", 1)[1].split('          PY\n', 1)[0]
    code = '\n'.join(line[10:] for line in embedded.splitlines())
    environment = dict(os.environ, VERSION=VERSION)
    subprocess.check_call([sys.executable, '-c', code], cwd=repo, env=environment)
    built = repo / f'SolarPilot-v{VERSION}-local.zip'
    original = built.read_bytes()
    (repo / 'custom_components/solar_pilot/const.py').write_text('uncommitted wrong source')
    (repo / 'custom_components/solar_pilot/untracked.py').write_text('not release source')
    subprocess.check_call([sys.executable, '-c', code], cwd=repo, env=environment)
    assert built.read_bytes() == original
    assert proof.verify_release(repo, 'HEAD', hacs, built)['version'] == VERSION


def test_existing_version_tag_with_another_commit_fails_without_overwriting_tag(release):
    repo, hacs, local = release
    original = run(repo, 'rev-parse', 'HEAD').decode().strip()
    tag = 'v' + VERSION
    run(repo, 'tag', tag)
    (repo / 'README.md').write_text('later source with same manifest version\n')
    run(repo, 'add', '.')
    run(repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-qm', 'later source')
    current = run(repo, 'rev-parse', 'HEAD').decode().strip()
    rebuild(repo, hacs, local)
    with pytest.raises(proof.PackageError, match='differs from expected source SHA'):
        proof.verify_release(repo, tag, hacs, local, expected_sha=current)
    assert run(repo, 'rev-parse', tag).decode().strip() == original
