#!/usr/bin/env python3
from pathlib import Path
import json, sys
root=Path(__file__).resolve().parents[1]
errors=[]
cc=root/'custom_components'
subdirs=[p for p in cc.iterdir() if p.is_dir()] if cc.exists() else []
if len(subdirs)!=1 or subdirs[0].name!='solar_pilot':
    errors.append('Er moet exact één integration staan onder custom_components/solar_pilot')
manifest_path=cc/'solar_pilot/manifest.json'
try:
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
except Exception as e:
    errors.append(f'manifest.json ongeldig: {e}'); manifest={}
for key in ('domain','documentation','issue_tracker','codeowners','name','version'):
    if key not in manifest:
        errors.append(f'manifest mist {key}')
if manifest.get('domain')!='solar_pilot': errors.append('manifest domain moet solar_pilot zijn')
try:
    h=json.loads((root/'hacs.json').read_text(encoding='utf-8'))
    if not h.get('name'): errors.append('hacs.json mist name')
except Exception as e: errors.append(f'hacs.json ongeldig: {e}')
if not (cc/'solar_pilot/brand/icon.png').exists(): errors.append('brand/icon.png ontbreekt')
if not (root/'README.md').exists(): errors.append('README.md ontbreekt')
if 'OWNER/REPOSITORY' in manifest.get('documentation',''):
    print('WAARSCHUWING: GitHub owner/repository nog niet ingevuld; voer tools/configure_repository.py uit vóór publicatie.')
if errors:
    print('\n'.join('FOUT: '+e for e in errors)); sys.exit(1)
print('Repositorystructuur OK')
