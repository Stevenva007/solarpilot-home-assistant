#!/usr/bin/env python3
"""Validate SolarPilot's release-bound technical handoff dossier."""
from __future__ import annotations
import json, os, re, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HANDOFF=ROOT/'OVERDRACHT.md'
MANIFEST=ROOT/'custom_components/solar_pilot/manifest.json'
CURRENT_GUIDE=ROOT/'docs/ACTUELE_WERKING.md'
errors=[]
text=HANDOFF.read_text(encoding='utf-8') if HANDOFF.exists() else ''
if not text: errors.append('OVERDRACHT.md ontbreekt')
version=str(json.loads(MANIFEST.read_text(encoding='utf-8')).get('version') or '').strip()
vm=re.search(r'<!--\s*solarpilot-handoff-version:\s*([^\s]+)\s*-->',text)
sm=re.search(r'<!--\s*solarpilot-handoff-schema:\s*(\d+)\s*-->',text)
if not sm: errors.append('machineleesbare solarpilot-handoff-schema ontbreekt')
if not vm: errors.append('machineleesbare solarpilot-handoff-version ontbreekt')
elif vm.group(1)!=version: errors.append(f'OVERDRACHT.md versie {vm.group(1)!r} != manifest versie {version!r}')
if version and f'**v{version}**' not in text: errors.append('zichtbare actuele productieversie ontbreekt of is verouderd')
required=(
'## 1. Projectdoel in gewone taal','## 2. Actuele basis','## 3. Absolute ontwerpregels',
'## 4. Actuele werking','## 5. Configuratie, integraties en belangrijke entiteiten',
'## 6. Belangrijke ontwerpbeslissingen + waarom','## 7. Automatische processen',
'## 8. Geheimenbeleid','## 9. Testprocedure + actuele teststatus','## 10. Bekende problemen / beperkingen',
'## 11. Concrete openstaande ontwikkeling','## 12. Installatie/upgrade en rollback',
'## 13. Belangrijkste bestanden','## 14. Release-checklist','## 15. AI-handoff')
for section in required:
    if section not in text: errors.append(f'verplicht onderdeel ontbreekt: {section}')
if CURRENT_GUIDE.exists() and version and f'**Versie:** {version}' not in CURRENT_GUIDE.read_text(encoding='utf-8'):
    errors.append('ACTUELE_WERKING.md loopt niet gelijk met manifestversie')

def usable_sha(v):
    v=(v or '').strip(); return bool(re.fullmatch(r'[0-9a-fA-F]{40}',v)) and set(v)!={'0'}
base=(os.getenv('HANDOFF_PR_BASE') or os.getenv('HANDOFF_BASE') or '').strip(); head=(os.getenv('HANDOFF_HEAD') or '').strip()
if usable_sha(base) and usable_sha(head):
    try:
        subprocess.run(['git','cat-file','-e',f'{base}^{{commit}}'],cwd=ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        changed={x.strip() for x in subprocess.check_output(['git','diff','--name-only',base,head],cwd=ROOT,text=True).splitlines() if x.strip()}
        functional={p for p in changed if p.startswith('custom_components/solar_pilot/') or p=='hacs.json'}
        if functional and 'OVERDRACHT.md' not in changed:
            errors.append('functionele SolarPilot-wijziging zonder bijgewerkt OVERDRACHT.md: '+', '.join(sorted(functional)[:8]))
    except (subprocess.CalledProcessError,OSError) as err:
        errors.append(f'git-diffcontrole overdrachtsdossier mislukt: {err}')
if errors: raise SystemExit('\n'.join('ERROR: '+e for e in errors))
print(f'OK: overdrachtsdossier {version}')
