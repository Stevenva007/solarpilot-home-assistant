"""Rendering/privacy check in ordinary Jinja, not the full HA template environment."""
from pathlib import Path
from types import SimpleNamespace
from jinja2.sandbox import SandboxedEnvironment


def test_inventory_exports_only_allowlisted_attributes():
    template=Path(__file__).resolve().parents[1]/'examples/boiler_inventaris.jinja'
    items=[
      SimpleNamespace(entity_id='water_heater.tank',name='Warm water',state='heat_pump',attributes={'temperature':50,'current_temperature':44,'access_token':'SECRET','entity_picture':'TOKEN_URL'}),
      SimpleNamespace(entity_id='climate.salon',name='Salon',state='cool',attributes={'hvac_action':'cooling','temperature':22,'min_temp':16,'max_temp':30}),
      SimpleNamespace(entity_id='sensor.pv',name='Zonneopbrengst',state='3456',attributes={'unit_of_measurement':'W','device_class':'power'}),
      SimpleNamespace(entity_id='image.roomba',name='Boiler camerakaart',state='x',attributes={'access_token':'SECRET'}),
      SimpleNamespace(entity_id='switch.powerful',name='Krachtige modus',state='off',attributes={}),
      SimpleNamespace(entity_id='switch.roomba_eco_charge',name='Roomba opladen',state='off',attributes={})]
    out=SandboxedEnvironment().from_string(template.read_text(encoding="utf-8")).render(states=items)
    for text in ('water_heater.tank','climate.salon','cooling','3456','switch.powerful'):
        assert text in out
    for text in ('SECRET','TOKEN_URL','image.roomba','switch.roomba_eco_charge'):
        assert text not in out
