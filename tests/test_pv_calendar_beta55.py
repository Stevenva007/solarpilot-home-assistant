"""Relative native energy roles expire at HA-local calendar boundaries."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.pv_forecast import PVForecast
from custom_components.solar_pilot.pv_forecast_source import PowerSeries
from test_runtime import build


BRUSSELS=ZoneInfo("Europe/Brussels")
ENERGY_ROLES={
    "today_entity":"raw_today_kwh",
    "remaining_entity":"raw_remaining_today_kwh",
    "tomorrow_entity":"raw_tomorrow_kwh",
    "current_hour_entity":"raw_current_hour_kwh",
    "next_hour_entity":"raw_next_hour_kwh",
}


def native_forecast(now, reported, values=None, unit="kWh"):
    runtime,hass=build()
    hass.config=NS(time_zone="Europe/Brussels",latitude=51,longitude=4)
    runtime.entry.options["pv_forecast"]={role:f"sensor.{role}" for role in ENERGY_ROLES}
    values=values or {role:2.5 for role in ENERGY_ROLES}
    for role,value in values.items():
        entity_id=f"sensor.{role}"
        hass.states.set(entity_id,value,{"unit_of_measurement":unit})
        obj=hass.states.get(entity_id)
        obj.last_reported=reported
        obj.last_updated=reported
    return PVForecast(runtime),hass


def test_after_midnight_yesterdays_native_day_roles_are_unknown_not_relabelled():
    now=datetime(2026,10,5,0,26,tzinfo=BRUSSELS)
    reported=datetime(2026,10,4,23,28,tzinfo=BRUSSELS)
    forecast,hass=native_forecast(now,reported,{
        "today_entity":60.269,"tomorrow_entity":30.371,"remaining_entity":0,
        "current_hour_entity":0,"next_hour_entity":0,
    })

    forecast.update(now)

    assert not forecast.error
    # Reports are younger than stale_s; their calendar roles have still expired.
    assert forecast.cached["source_age_s"]==58*60
    assert forecast.source.scalars["today_entity"]==60.269
    assert forecast.source.scalars["tomorrow_entity"]==30.371
    assert all(forecast.cached[key] is None for key in ENERGY_ROLES.values())
    assert forecast.cached["corrected_remaining_today_kwh"] is None
    assert forecast.cached["corrected_tomorrow_kwh"] is None
    assert not hass.services.calls
    assert forecast.settings["panel_peak_wp"]==13800
    assert forecast.settings["inverter_limit_w"]==10000


def test_midnight_expires_native_roles_inside_one_minute_update_cache():
    reported=datetime(2026,10,4,23,59,40,tzinfo=BRUSSELS)
    before=reported+timedelta(seconds=10)
    forecast,hass=native_forecast(before,reported)
    forecast.update(before)
    assert all(forecast.cached[key]==2.5 for key in ENERGY_ROLES.values())

    forecast.update(before+timedelta(seconds=20))

    assert all(forecast.cached[key] is None for key in ENERGY_ROLES.values())
    assert not forecast.error


@pytest.mark.parametrize("before",[
    datetime(2026,10,4,23,59,50,tzinfo=BRUSSELS),
    datetime(2026,10,5,12,59,50,tzinfo=BRUSSELS),
    datetime(2026,3,29,1,59,50,tzinfo=BRUSSELS),
    datetime(2026,10,25,2,59,50,tzinfo=BRUSSELS,fold=0),
])
@pytest.mark.parametrize("value",[2.5,3.75])
def test_boundary_rereads_fresh_native_values_inside_source_minute_cache(before,value):
    reported=datetime.fromtimestamp(before.timestamp()-10,BRUSSELS)
    forecast,hass=native_forecast(before,reported)
    forecast.update(before)
    after=datetime.fromtimestamp(before.timestamp()+20,BRUSSELS)
    for role in ENERGY_ROLES:
        obj=hass.states.get(f"sensor.{role}")
        obj.state=str(value)
        obj.last_reported=after
        # An unchanged value need not update last_updated, including at midnight.

    forecast.update(after)

    assert forecast.source.last_refresh==after.timestamp()
    assert all(forecast.cached[key]==value for key in ENERGY_ROLES.values())
    assert all(forecast.source.scalars[role]==value for role in ENERGY_ROLES)
    assert not forecast.error
    assert not hass.services.calls


def test_fresh_after_midnight_report_restores_roles_without_learning_or_rebasing():
    now=datetime(2026,10,5,0,26,tzinfo=BRUSSELS)
    old=datetime(2026,10,4,23,28,tzinfo=BRUSSELS)
    forecast,hass=native_forecast(now,old)
    forecast.update(now)
    fresh=now+timedelta(minutes=2)
    for role in ENERGY_ROLES:
        obj=hass.states.get(f"sensor.{role}")
        obj.last_reported=fresh
        obj.state="30.371" if role=="today_entity" else "0"
        # last_updated may remain on the previous date when a value is unchanged.
    forecast.update(fresh)

    assert forecast.cached["raw_today_kwh"]==30.371
    assert all(forecast.cached[key]==0 for role,key in ENERGY_ROLES.items() if role!="today_entity")
    assert forecast.cached["factor"]==1
    assert forecast.cached["confidence"]==0


@pytest.mark.parametrize("now,reported",[
    (datetime(2026,10,5,13,0,10,tzinfo=BRUSSELS),datetime(2026,10,5,12,59,40,tzinfo=BRUSSELS)),
    (datetime(2026,3,29,3,1,tzinfo=BRUSSELS),datetime(2026,3,29,1,59,tzinfo=BRUSSELS)),
    (datetime(2026,10,25,2,30,tzinfo=BRUSSELS,fold=1),datetime(2026,10,25,2,30,tzinfo=BRUSSELS,fold=0)),
])
def test_hour_roles_expire_on_elapsed_hour_change_including_dst(now,reported):
    forecast,hass=native_forecast(now,reported)
    forecast.update(now)

    assert all(forecast.cached[ENERGY_ROLES[role]]==2.5 for role in (
        "today_entity","remaining_entity","tomorrow_entity"))
    assert forecast.cached["raw_current_hour_kwh"] is None
    assert forecast.cached["raw_next_hour_kwh"] is None
    assert not forecast.error


@pytest.mark.parametrize("now",[
    datetime(2026,3,29,1,30,tzinfo=BRUSSELS),
    datetime(2026,10,25,2,30,tzinfo=BRUSSELS,fold=0),
    datetime(2026,10,25,2,30,tzinfo=BRUSSELS,fold=1),
])
def test_same_elapsed_hour_roles_remain_available_during_dst(now):
    reported=datetime.fromtimestamp(now.timestamp()-60,BRUSSELS)
    forecast,hass=native_forecast(now,reported)
    forecast.update(now)

    assert all(forecast.cached[key]==2.5 for key in ENERGY_ROLES.values())


def test_hour_rollover_expires_only_hour_roles_inside_minute_cache():
    reported=datetime(2026,10,5,12,59,40,tzinfo=BRUSSELS)
    before=reported+timedelta(seconds=10)
    forecast,hass=native_forecast(before,reported)
    forecast.update(before)
    forecast.update(before+timedelta(seconds=20))

    assert forecast.cached["raw_today_kwh"]==2.5
    assert forecast.cached["raw_tomorrow_kwh"]==2.5
    assert forecast.cached["raw_current_hour_kwh"] is None
    assert forecast.cached["raw_next_hour_kwh"] is None


@pytest.mark.parametrize("unit,value",[("Wh",2500),("kWh",2.5)])
def test_relative_roles_use_ha_timezone_and_keep_source_energy_units(unit,value):
    local=datetime(2026,10,5,0,26,tzinfo=BRUSSELS)
    now=local.astimezone(timezone.utc)
    reported=(local-timedelta(minutes=1)).astimezone(timezone.utc)
    forecast,hass=native_forecast(now,reported,{role:value for role in ENERGY_ROLES},unit)
    forecast.update(now)

    assert all(forecast.cached[key]==2.5 for key in ENERGY_ROLES.values())
    assert datetime.fromisoformat(forecast.cached["updated"]).date()==local.date()


def test_last_updated_is_timestamp_fallback_when_last_reported_is_missing():
    now=datetime(2026,10,5,0,26,tzinfo=BRUSSELS)
    forecast,hass=native_forecast(now,now-timedelta(minutes=1))
    for role in ENERGY_ROLES:
        hass.states.get(f"sensor.{role}").last_reported=None
    forecast.update(now)

    assert all(forecast.cached[key]==2.5 for key in ENERGY_ROLES.values())


@pytest.mark.parametrize("reported",[
    None,"invalid","2026-10-05T00:25:00",
    datetime(2026,10,5,0,27,tzinfo=BRUSSELS),
    datetime(2026,10,4,21,0,tzinfo=BRUSSELS),
])
def test_unknown_naive_future_or_age_expired_reports_stay_unknown(reported):
    now=datetime(2026,10,5,0,26,tzinfo=BRUSSELS)
    forecast,hass=native_forecast(now,reported)
    forecast.update(now)

    assert all(forecast.cached[key] is None for key in ENERGY_ROLES.values())
    assert not forecast.error


def test_five_second_future_tolerance_cannot_cross_native_role_day_boundary():
    now=datetime(2026,10,4,23,59,59,tzinfo=BRUSSELS)
    reported=now+timedelta(seconds=2)
    forecast,hass=native_forecast(now,reported)
    forecast.update(now)

    assert forecast.source.scalars["tomorrow_entity"]==2.5
    assert all(forecast.cached[key] is None for key in ENERGY_ROLES.values())


def test_dated_curve_remains_usable_when_native_scalar_calendar_roles_expire():
    now=datetime(2026,10,5,0,26,tzinfo=BRUSSELS)
    forecast,hass=native_forecast(now,datetime(2026,10,4,23,28,tzinfo=BRUSSELS))
    start=now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
    forecast.source.refresh(now.timestamp())
    points=[(start+i*3600,1000) for i in range(49)]
    forecast.source.series=PowerSeries(points)
    forecast.source.refresh=lambda ts:None
    forecast.update(now)

    assert forecast.cached["raw_today_kwh"] is None
    assert forecast.cached["raw_remaining_today_kwh"]==pytest.approx(23+34/60,abs=.0001)
    assert forecast.cached["raw_tomorrow_kwh"]==24
    assert forecast.cached["raw_current_hour_kwh"]==1
    assert forecast.cached["raw_next_hour_kwh"]==1
    assert forecast.source.series.points==points
    assert forecast.cached["energy_methods"]["tomorrow"]=="Geïntegreerde vermogenscurve (tijdstempels, kWh)"
