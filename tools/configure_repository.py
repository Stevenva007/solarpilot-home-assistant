#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path

if len(sys.argv) < 2:
    raise SystemExit(
        "Gebruik: python tools/configure_repository.py GITHUB_OWNER [REPOSITORY]\n"
        "Voorbeeld: python tools/configure_repository.py jouwnaam solarpilot-home-assistant"
    )

owner = sys.argv[1].strip().lstrip('@')
repo = sys.argv[2].strip() if len(sys.argv) > 2 else 'solarpilot-home-assistant'
if not re.fullmatch(r'[A-Za-z0-9_.-]+', owner):
    raise SystemExit('Ongeldige GitHub owner')
if not re.fullmatch(r'[A-Za-z0-9_.-]+', repo):
    raise SystemExit('Ongeldige repositorynaam')

root = Path(__file__).resolve().parents[1]
manifest_path = root / 'custom_components/solar_pilot/manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
base = f'https://github.com/{owner}/{repo}'
manifest['documentation'] = base + '#readme'
manifest['issue_tracker'] = base + '/issues'
manifest['codeowners'] = [f'@{owner}']
manifest_path.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
)

readme = root / 'README.md'
t = readme.read_text(encoding='utf-8')
marker = '## Open direct in HACS'
block = (
    f"{marker}\n\n"
    f"[![Open your Home Assistant instance and open SolarPilot in HACS]"
    f"(https://my.home-assistant.io/badges/hacs_repository.svg)]"
    f"(https://my.home-assistant.io/redirect/hacs_repository/?owner={owner}&repository={repo}&category=integration)\n\n"
    f"Repository: `{base}`\n\n"
)
heading = re.search(r'^' + re.escape(marker) + r'[ \t]*$', t, re.MULTILINE)
if heading:
    # Own the generated badge/repository lines, not the rest of this section
    # or every section which follows it. Reconfiguration must preserve prose.
    next_heading = re.search(r'^## ', t[heading.end():], re.MULTILINE)
    end = heading.end() + next_heading.start() if next_heading else len(t)
    body = t[heading.end():end]
    tail = t[end:]
    body = re.sub(
        r'^\[!\[Open your Home Assistant instance and open SolarPilot in HACS\]'
        r'\(https://my\.home-assistant\.io/badges/hacs_repository\.svg\)\]'
        r'\(https://my\.home-assistant\.io/redirect/hacs_repository/\?[^\n]*\)\s*$',
        '', body, flags=re.MULTILINE,
    )
    body = re.sub(r'^Repository: `https://github\.com/[^`\n]+`[ \t]*$', '', body, flags=re.MULTILINE)
    extra = body.strip('\n')
    t = t[:heading.start()].rstrip() + '\n\n' + block
    if extra:
        t += extra + '\n\n'
    t += tail.lstrip('\n')
else:
    t = t.rstrip() + '\n\n' + block
readme.write_text(t, encoding='utf-8')
print(f'Klaar: {base}')
