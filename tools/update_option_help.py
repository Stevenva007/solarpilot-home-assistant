"""Generate release-bound option help and native data descriptions; no HA import."""
from pathlib import Path
import importlib.util, json, sys, types
ROOT=Path(__file__).resolve().parents[1]; C=ROOT/'custom_components/solar_pilot'
pkg=types.ModuleType('solarpilot_help_build');pkg.__path__=[str(C)];sys.modules[pkg.__name__]=pkg

def load(name):
    full=f'{pkg.__name__}.{name}';spec=importlib.util.spec_from_file_location(full,C/f'{name}.py')
    m=importlib.util.module_from_spec(spec);sys.modules[full]=m;spec.loader.exec_module(m);return m

def build():
    helpmod=load('option_help');thermal=load('thermal_climate');planner=load('unified_planner');guide=load('current_guide')
    j=json.loads((C/'translations/nl.json').read_text(encoding='utf-8'))
    steps=j['options']['step']; entries={}
    for step,data in steps.items():
        for key,label in data.get('data',{}).items():
            specs=thermal.CLIMATE_SETTING_SPECS if step.startswith('smart_climate') else planner.PLANNER_SETTING_SPECS if step=='planner' else {}
            entries[f'{step}.{key}']=helpmod.help_for(step,key,label,specs.get(key))
    # Direct climate dashboard exposes more model parameters than the short wizard.
    for key,spec in thermal.CLIMATE_SETTING_SPECS.items():
        entries.setdefault(f'smart_climate.{key}',helpmod.help_for('smart_climate',key,spec['label'],spec))
    for key,spec in planner.PLANNER_SETTING_SPECS.items():
        entries.setdefault(f'planner.{key}',helpmod.help_for('planner',key,spec['label'],spec))
    for key,label in [('learning_hub','Leren & vragen'),('participation','Automatisch / Uitgesloten'),('others_first','Globale Wallbox-voorkeur'),('manual_start','Manueel starten'),('manual_stop','Manueel stoppen'),('boost','Boost 30 minuten'),('analysis_export','Analyse-export'),('dishwasher_arm','Afwasbeurt klaarzetten'),('dishwasher_cancel','Klaarzetten annuleren')]:
        entries[f'dashboard.{key}']=helpmod.help_for('dashboard',key,label)
    for key,label in [('sampling','Brongebruik voor leren'),('adaptation','Recente voorspellingen aanpassen'),('notifications','Vragen als HA-melding')]:
        entries[f'learning_hub.{key}']=helpmod.help_for('learning_hub',key,label)
    return {'version':guide.GUIDE_VERSION,'language':'nl','steps':steps,'errors':j['options'].get('error',{}),'abort':j['options'].get('abort',{}),'entries':entries}

if __name__=='__main__':
    data=build()
    for step,definition in data['steps'].items():
        if definition.get('data'):
            definition['data_description']={key:data['entries'][f'{step}.{key}']['short'] for key in definition['data']}
    j=json.loads((C/'translations/nl.json').read_text(encoding='utf-8'));j['options']['step']=data['steps'];(C/'translations/nl.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (C/'frontend/option-help.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Optiehulp: {len(data["entries"])} instellingen · {data["version"]}')
