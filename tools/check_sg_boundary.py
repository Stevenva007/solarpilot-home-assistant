"""Fail CI when a native Panasonic writer is reintroduced into beta.62."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'custom_components/solar_pilot'
RETIRED = ('dhw.py', 'dhw_config.py', 'dhw_runtime.py', 'dhw_schedule.py',
           'thermal_runtime.py', 'thermal_climate.py')
errors = []
for name in RETIRED:
    if (CODE / name).exists():
        errors.append('Retired controller returned: ' + name)
for path in CODE.glob('*.py'):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[-1] in {n[:-3] for n in RETIRED}:
            errors.append('Retired controller import: ' + path.name)
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == 'async_call' and node.args:
            domain = node.args[0]
            if isinstance(domain, ast.Constant) and domain.value in {'climate', 'water_heater', 'aquarea', 'panasonic_cc'}:
                errors.append('Native service writer: ' + path.name)
        if node.func.attr == 'call_rpc' and path.name != 'sg_transport.py':
            errors.append('Unreviewed native contact RPC route: ' + path.name)
for name, function in [('runtime.py', '_call'), ('battery_runtime.py', '_send')]:
    source = (CODE / name).read_text(encoding='utf-8')
    methods = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.AsyncFunctionDef) and n.name == function]
    if len(methods) != 1 or 'assert_allowed' not in ast.get_source_segment(source, methods[0]):
        errors.append('Missing central command authority: ' + name)
card = (CODE / 'frontend/solar-pilot-card.js').read_text(encoding='utf-8')
for operation in ('set_dhw_setting', 'set_climate_setting', 'set_climate_override'):
    if operation in card:
        errors.append('Retired frontend writer: ' + operation)
if errors:
    raise SystemExit('\n'.join(errors))
print('SG authority boundary OK: retired native writers absent; ordinary/battery dispatch guarded; SG RPC isolated.')
