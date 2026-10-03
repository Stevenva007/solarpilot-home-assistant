"""An explicit ordinary manual run still yields to its safety interlock."""
from dataclasses import replace

import pytest

from custom_components.solar_pilot.engine import plan
from test_engine import dev, owned, site


@pytest.mark.parametrize("changes,reason", [
    ({"interlock": False}, "Vrijgave ontbreekt"),
    ({"fault": "Bereik van vermogensregelaar is gewijzigd"},
     "Bereik van vermogensregelaar is gewijzigd"),
])
def test_ordinary_manual_run_releases_when_safety_guard_is_lost(changes, reason):
    state = owned(manual_forced=True, **changes)
    result = plan(site(500), [dev()], {"a": state})
    assert result.action is not None
    assert result.action.watts == 0 and result.action.reason == reason


@pytest.mark.parametrize("protected", ["minimum_on", "non_interruptible"])
@pytest.mark.parametrize("changes", [{"interlock": False}, {"fault": "bron onbekend"}])
def test_manual_run_guard_fix_preserves_existing_cycle_and_minimum_locks(protected, changes):
    device = dev(non_interruptible=protected == "non_interruptible")
    if protected == "minimum_on":
        device = replace(device, min_on_s=1200)
    state = owned(manual_forced=True, **changes)
    result = plan(site(500), [device], {"a": state})
    assert result.action is None and result.targets["a"] == 1000
