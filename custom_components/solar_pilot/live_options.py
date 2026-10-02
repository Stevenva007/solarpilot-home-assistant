"""Transactional hot options, per-device deferred edits and retirement.

The config entry always holds the EFFECTIVE bindings. Deferred proposals live in
_live_pending, so a restart cannot accidentally bind a running cycle to new
entities. This module issues no actuator commands. All mutations run under the
same lock as dispatch; the dishwasher event listener remains installed.
"""
from __future__ import annotations

from copy import deepcopy
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from uuid import uuid4

from homeassistant.exceptions import HomeAssistantError

from .const import DEVICE_DEFAULTS
from .dishwasher import normalize_config
from .dishwasher_app import deadline_time
from .engine import State

PENDING = "_live_pending"
ARCHIVED = "_archived_devices"
SCHEDULE_KEYS = frozenset({"dishwasher_start_deadline", "dishwasher_monday_start_deadline",
    "dishwasher_after_deadline",
    "dishwasher_deadline_grid_allowed", "dishwasher_deadline_grace_min"})
# Running devices keep all source/permission/protection and programme settings.
# Only display identity and relative future allocation can change in place.
RUNNING_LIVE_KEYS = frozenset({"name", "priority", "appliance_type"})
REFERENCE_KEYS = frozenset({"control_entity", "active_entity", "number_entity", "start_script",
    "stop_script", "power_entity", "condition_entity", "interlock_entity", "start_button",
    "dishwasher_state_entity", "dishwasher_remote_entity", "dishwasher_door_entity",
    "dishwasher_connection_entity", "dishwasher_phase_entity", "dishwasher_alert_entity",
    "cycle_program_entity", "dishwasher_delay_entity"})
DISPLAY_GROUPS = {"priority_board", "economy", "forecast", "planner", "local_pv", "pv_forecast", "analysis", "battery_analysis"}
SENSITIVE_GROUPS = {"settings", "capacity", "phase", "wallbox", "dhw", "smart_climate", "batteries", "battery_fleet", "_private_bundle"}


def keyed(rows):
    return {x["id"]: deepcopy(x) for x in rows or [] if isinstance(x, dict) and x.get("id")}


def changed_keys(a, b):
    return {k for k in set(a) | set(b) if a.get(k) != b.get(k)}


def merge_three(base, desired, current, path=""):
    """Only apply edited leaves; reject concurrent edits to the SAME leaf.

    Lists of device/battery profiles are keyed by stable identity. Other lists are
    atomic values (e.g. a set of zone sources must not be partially interleaved).
    """
    out = deepcopy(current)
    missing = object()
    for k in set(base) | set(desired):
        if str(k).startswith("_live_") or k == ARCHIVED:
            continue
        a, b, c = base.get(k, missing), desired.get(k, missing), current.get(k, missing)
        if a == b:
            continue
        p = f"{path}.{k}".strip(".")
        if all(isinstance(v, dict) for v in (a, b, c)):
            out[k] = merge_three(a, b, c, p)
        elif k in ("devices", "batteries") and all(v is missing or isinstance(v, list) for v in (a,b,c)):
            out[k] = list(merge_three(keyed([] if a is missing else a), keyed([] if b is missing else b),
                                    keyed([] if c is missing else c), p).values())
        else:
            if c != a and c != b:
                raise HomeAssistantError(f"Instelling intussen elders gewijzigd: {p}. Heropen dit scherm.")
            if b is missing:
                out.pop(k, None)
            else:
                out[k] = deepcopy(b)
    return out


def replacement_profile(old):
    """Carry preferences, NOT endpoints, meter-derived values or permissions."""
    carry = {"name", "kind", "appliance_type", "priority", "start_delay_s", "stop_delay_s",
        "daily_deadline", "deadline_grid_allowed", "time_window_enabled", "time_window_start",
        "time_window_end", "wallbox_precedence", "wallbox_power_policy", "dishwasher_arming_mode",
        "dishwasher_start_deadline", "dishwasher_monday_start_deadline",
        "dishwasher_after_deadline", "dishwasher_deadline_grid_allowed",
        "dishwasher_deadline_grace_min", "dishwasher_priority_enabled", "dishwasher_ev_solar_priority"}
    result = {**DEVICE_DEFAULTS, **{k: deepcopy(v) for k,v in old.items() if k in carry}, "id": uuid4().hex}
    if result.get("kind") == "dishwasher":
        result = normalize_config(result)
        result.update(nominal_w=2000, ack_timeout_s=300, max_on_s=21600,
                      dishwasher_mapping_confirmed=False, non_interruptible=True)
    result["replaces_device_id"] = old["id"]
    return result


class LiveOptions:
    def __init__(self, runtime):
        self.r = runtime
        self.applied = deepcopy(dict(runtime.entry.options))
        self.archives = {}
        self.last_message = "Instellingen kunnen tijdens Zonnestroom worden geopend."
        self.error = ""

    def restore(self, data):
        if isinstance(data, dict):
            self.archives = deepcopy(data.get("archives", {}))
            self.last_message = str(data.get("last_message", self.last_message))

    def snapshot(self):
        return {"archives": deepcopy(self.archives), "last_message": self.last_message}

    def needs_request_choice(self, base, desired):
        a, b = keyed(base.get("devices")), keyed(desired.get("devices"))
        return [i for i in a.keys() & b.keys() if changed_keys(a[i], b[i]) & SCHEDULE_KEYS
                and self.r.dishwasher_app.data.get(i, {}).get("request")]

    def device_block(self, i, old, new=None):
        r, s = self.r, self.r.states.get(i)
        if s is None:
            return ""
        pending = r.pending or {}
        if pending.get("device_id", pending.get("id")) == i or (r.handover and getattr(r.handover, "device_id", None) == i):
            return "Opdracht/overdracht wacht op terugmelding"
        if i in r.recovery or i in r.faults:
            return "Onzekere toestand: toestelcontrole vereist"
        if old.get("kind") == "dishwasher":
            if i in r.dishwasher_priority.watches:
                return "Wallbox-overdracht voor deze afwasbeurt wordt nog bevestigd"
            t = r.dishwasher.tickets.get(i, {})
            d = r.dishwasher_app.data.get(i, {})
            if t.get("attempted") or t.get("in_flight"):
                return "START-uitkomst nog niet bevestigd"
            if d.get("end_pending"):
                return "Bevestigd einde wordt eerst in de historiek verwerkt"
            if d.get("cycle", {}).get("status") in ("running", "end_unconfirmed"):
                return "Beschermde was-/droogcyclus loopt of einde is nog niet bevestigd"
        actual = r._active(old)
        if s.owned or s.on or actual is True:
            return "Toestel is nog actief; huidige koppelingen en bescherming blijven gelden"
        if actual is None and (s.observed_once or old.get("kind") == "dishwasher"):
            # A recorded end is stronger evidence than a later offline cloud state.
            d = r.dishwasher_app.data.get(i, {})
            if d.get("cycle", {}).get("status") != "completed":
                return "Geen betrouwbare rust-/eindstatus; nog niet toepassen"
        return ""

    def group_block(self, group, old, new):
        r = self.r
        keys = changed_keys(old if isinstance(old, dict) else {}, new if isinstance(new, dict) else {})
        if group in DISPLAY_GROUPS:
            return ""
        if r.pending or r.handover or r.dhw.pending or r.battery_fleet.busy:
            return "Wacht op de al verstuurde opdracht/overdracht"
        if group == "wallbox" and (r.dishwasher_priority.watches or r.handover):
            return "Wallbox-vermogensoverdracht wordt nog bevestigd"
        if group == "dhw":
            binding = any(k.endswith("entity") or k.endswith("entities") for k in keys)
            if binding and (r.dhw.busy or r.dhw.reading.protected):
                return "Boilerkoppeling wacht op gerichte vrijgave/hygiëne-einde; andere toestellen blijven werken"
        if group == "smart_climate":
            if any(k.endswith("entity") or k.endswith("entities") for k in keys) and r.smart_climate.removal_blocked():
                return "Klimaatkoppeling wacht op vrijgave van de bestaande zones"
        if group in ("batteries", "battery_fleet") and r.battery_fleet.removal_blocked():
            return "Batterijbinding wacht op bevestigde neutrale toestand"
        if group == "_private_bundle" and not r.editable:
            return "Privé-import vereist tijdelijk een vrijgegeven regeling"
        return ""

    def prepare(self, base, desired):
        current = deepcopy(dict(self.r.entry.options))
        target = merge_three(base, desired, current)
        out = deepcopy(current)
        queue = deepcopy(current.get(PENDING, {}))
        effects = []
        old, new = keyed(current.get("devices")), keyed(target.get("devices"))
        effective = deepcopy(old)
        replacements = {v.get("replaces_device_id"): i for i,v in new.items()
                        if v.get("replaces_device_id") in old and i not in old}
        if self.r.priority_board.active:
            priority_keys = {"priority", "wallbox_precedence", "wallbox_power_policy", "allow_wallbox_reclaim",
                             "dishwasher_priority_enabled", "dishwasher_ev_solar_priority"}
            for i in old.keys() & new.keys():
                before = normalize_config({**DEVICE_DEFAULTS, **old[i]})
                after = normalize_config({**DEVICE_DEFAULTS, **new[i]})
                if before.get("kind") == after.get("kind") and any(before.get(k) != after.get(k) for k in priority_keys):
                    raise HomeAssistantError("Gebruik Voorrang → Volgorde aanpassen voor de volgorde en toestemming om autoladen te verminderen. Sluit een oude instellingenpagina en open deze opnieuw.")
        self._validate_bindings(old, new, queue)
        self._validate_meter_scopes(current, target)
        for i in old.keys() | new.keys():
            if i in replacements.values():
                continue
            a, b = old.get(i), new.get(i)
            if a == b and i not in replacements:
                continue
            queue_key = "device:" + i
            if queue_key in queue:
                raise HomeAssistantError("Voor dit toestel staat al een wijziging klaar. Annuleer die eerst bij Wachtende wijzigingen.")
            replacement = new.get(replacements.get(i))
            if replacement is not None:
                b = replacement
            blocker = self.device_block(i, a, b) if a else ""
            delta = changed_keys(a or {}, b or {})
            # Name/priority can be edited while active; every other active edit waits.
            if a and b and not replacement and delta <= RUNNING_LIVE_KEYS:
                blocker = ""
            if blocker:
                queue[queue_key] = {"kind": "device", "id": i, "old": a, "new": b,
                    "replacement": bool(replacement), "created": time.time(), "reason": blocker}
                if replacement:
                    effective.pop(b["id"], None)
                effects.append(f'{a["name"]}: opgeslagen — wacht tot toestel vrij is')
            else:
                if b is None or replacement:
                    effective.pop(i, None)
                    archives = keyed(out.get(ARCHIVED))
                    archives[i] = {**a, "archived_at": time.time(), "replaced_by": b["id"] if b else None}
                    out[ARCHIVED] = list(archives.values())
                if b is not None:
                    effective[b["id"]] = deepcopy(b)
                effects.append(f'{(b or a)["name"]}: direct toepassen zonder herladen')
        if old != new or replacements:
            out["devices"] = list(effective.values())
        for group in (set(current) | set(target)) - {"devices", ARCHIVED, PENDING}:
            if group.startswith("_live_") or current.get(group) == target.get(group):
                continue
            queue_key = "group:" + group
            if queue_key in queue:
                raise HomeAssistantError("Voor deze functiegroep staat al een wijziging klaar; annuleer die eerst.")
            block = self.group_block(group, current.get(group, {}), target.get(group, {}))
            if block:
                queue[queue_key] = {"kind": "group", "group": group, "old": current.get(group),
                    "new": target.get(group), "created": time.time(), "reason": block}
                effects.append(f"{group}: opgeslagen — {block}")
            else:
                if group in target: out[group] = deepcopy(target[group])
                else: out.pop(group, None)
                effects.append(f"{group}: direct toepassen zonder herladen")
        if len(queue) > 100:
            raise HomeAssistantError("Te veel wachtende wijzigingen; rond deze eerst af.")
        out[PENDING] = queue
        return out, effects

    def _validate_bindings(self, old, new, queue):
        """Recheck the merged transaction, including endpoints reserved by queued edits.

        Existing legacy configurations are not retroactively rejected for unrelated
        display edits. Newly edited actuators/meters cannot be bound twice.
        """
        def refs(c):
            kind=c.get("kind")
            keys=("start_button", "dishwasher_state_entity") if kind=="dishwasher" else (
                ("start_script", "stop_script", "active_entity") if kind=="script" else
                ("control_entity", "number_entity") if kind=="number" else ("control_entity",))
            return {c[k] for k in keys if c.get(k)}
        proposals=[v.get("new") for v in queue.values() if v.get("kind")=="device" and v.get("new")]
        for i,c in new.items():
            previous=old.get(i,{})
            if i in old and not (changed_keys(previous,c)&REFERENCE_KEYS or c.get("kind")!=previous.get("kind")):
                continue
            for j,other in new.items():
                if i==j:continue
                if refs(c)&refs(other):
                    raise HomeAssistantError("Een actuator/statusbron is al aan een ander SolarPilot-toestel gekoppeld.")
                if c.get("power_entity") and c.get("power_entity")==other.get("power_entity"):
                    raise HomeAssistantError("Een exclusieve vermogensmeter mag niet bij twee toestellen staan.")
            for other in proposals:
                if other["id"] in (i,c.get("replaces_device_id")):continue
                if refs(c)&refs(other) or (c.get("power_entity") and c.get("power_entity")==other.get("power_entity")):
                    raise HomeAssistantError("Deze bron is al gereserveerd door een wachtende toestelwijziging.")

    def _validate_meter_scopes(self, before, after):
        """Detect newly introduced shared meter scopes, including concurrent tabs."""
        def conflicts(options):
            site={**self.r.entry.data,**options.get("settings",{})}
            reserved={site.get(k) for k in ("grid_entity","export_entity","pv_entity","battery_power_entity")}
            reserved.update(options.get(g,{}).get("power_entity") for g in ("dhw","wallbox"))
            reserved.update(b.get("power_entity") for b in options.get("batteries",[]))
            return {(c["id"],c.get("power_entity")) for c in options.get("devices",[])
                    if c.get("power_entity") and c["power_entity"] in reserved}
        if conflicts(after)-conflicts(before):
            raise HomeAssistantError("Een toestelmeter mag niet tegelijk de net-, PV-, batterij-, boiler- of Wallbox-meter zijn.")

    def _change_current_requests(self, before, after, ids):
        devices = keyed(after.get("devices"))
        for i in ids:
            q = self.r.dishwasher_app.data.get(i, {}).get("request")
            if not q or i not in devices:
                continue  # The same belading may already have started while editing.
            cfg = devices[i]
            day = datetime.fromisoformat(q["planned_day"]).date()
            zone = ZoneInfo(q.get("zone", self.r.dishwasher_app.zone))
            deadline = datetime.combine(day, deadline_time(cfg, day), zone)
            # Explicit choice updates this fixed planned day, never re-arms/re-dates it.
            q.update(deadline=deadline.timestamp(), expires=deadline.timestamp()+max(1,int(cfg.get("dishwasher_deadline_grace_min",120)))*60,
                     grid_allowed=bool(cfg.get("dishwasher_deadline_grid_allowed",True)), policy_locked=True)
            ticket = self.r.dishwasher.tickets.get(i)
            if ticket and not ticket.get("attempted"):
                ticket.update(q)
            self.r.note(f'{cfg["name"]}: aangepaste deadline/nettoestemming geldt ook voor de huidige aanvraag; plandag behouden.')

    async def submit(self, base, desired, request_scope="future"):
        if request_scope not in ("future", "current"):
            raise HomeAssistantError("Kies huidige aanvraag of alleen volgende beurten")
        out, effects = self.prepare(base, desired)
        ids = self.needs_request_choice(base, desired)
        before = deepcopy(dict(self.r.entry.options))
        request_before = {i: deepcopy(self.r.dishwasher_app.data[i].get("request")) for i in ids}
        request_objects = {i: self.r.dishwasher_app.data[i].get("request") for i in ids}
        old_message = self.last_message
        if ids and request_scope == "future":
            for i in ids:
                q = self.r.dishwasher_app.data.get(i, {}).get("request")
                if q: q["policy_locked"] = True
        elif ids:
            queued=[i for i in ids if "device:"+i in out.get(PENDING,{})]
            if queued:
                raise HomeAssistantError("De huidige aanvraag kan nog niet veilig worden aangepast. Kies alleen volgende beurten of wacht tot de startuitkomst bekend is.")
            self._change_current_requests(before, out, ids)
        self.last_message = "; ".join(effects) or "Geen gewijzigde instellingen"
        # Persist request choices before returning; no commands are sent by saving.
        try:
            await self.r.store.async_save(self.r._snapshot())
            self._persist(out)
        except Exception as err:
            for i,q in request_objects.items():
                if q is self.r.dishwasher_app.data.get(i,{}).get("request"):
                    for key in ("deadline","expires","grid_allowed","policy_locked"):
                        if key in request_before[i]:q[key]=request_before[i][key]
                        else:q.pop(key,None)
                    ticket=self.r.dishwasher.tickets.get(i)
                    if ticket and not ticket.get("attempted"):
                        for key in ("deadline","expires","grid_allowed","policy_locked"):
                            if key in q:ticket[key]=q[key]
                            else:ticket.pop(key,None)
            self.last_message=old_message
            self.error="Opslaan mislukt; actieve configuratie bleef behouden"
            raise HomeAssistantError(self.error) from err
        self.error=""
        await self.accept(out)
        self.r.note("Instellingen: " + self.last_message)
        self.r.publish()
        return out

    def _persist(self, options):
        ce = getattr(self.r.hass, "config_entries", None)
        if ce is not None and hasattr(ce, "async_update_entry"):
            ce.async_update_entry(self.r.entry, options=deepcopy(options))
        else:  # Explicit test doubles only.
            self.r.entry.options = deepcopy(options)

    def _archive(self, i, cfg):
        r = self.r
        self.archives[i] = {"id": i, "name": cfg.get("name",i), "archived_at": time.time(),
            "dishwasher": deepcopy(r.dishwasher_app.data.get(i, {})),
            "power_profile": deepcopy(r.learning.profiles.get(i, {})),
            "measured_programmes": deepcopy(r.dishwasher.profiles.get(i, {})),
            "phase_profile": deepcopy(r.phase_learning.profiles.get(i, {})),
            "cycle_profile": deepcopy(r.cycle_learning.profiles.get(i, {})),
            "last_reason": r.result.reasons.get(i, ""),
            "note": "Afgesloten toestel; geen bediening. Historiek binnen bestaande bewaartermijn."}
        # Old measurements remain only in archive, never under the replacement ID.
        for mapping in (r.dishwasher.tickets, r.dishwasher.readings, r.dishwasher.live, r.dishwasher.previous, r.dishwasher.profiles,
                        r.learning.profiles, r.cycle_learning.profiles, r.phase_learning.profiles, r.priorities,
                        r.device_modes, r.reclaim_blocks, r.planner_hold_since):
            mapping.pop(i, None)
        r.dishwasher_app.data.pop(i, None)
        r.dishwasher_app._seeded.discard(i)
        r.dishwasher_app._need_remote_baseline.discard(i)

    async def accept(self, options):
        """Apply persisted effective options under the existing dispatch lock."""
        r = self.r
        previous = self.applied
        if options == previous:
            return
        old, new = keyed(previous.get("devices")), keyed(options.get("devices"))
        wiring_changed = False
        for i in old.keys() - new.keys():
            self._archive(i, old[i])
            r.configs.pop(i, None); r.states.pop(i, None)
            r.result.reasons.pop(i, None); r.result.targets.pop(i, None)
            wiring_changed = True
        for i, cfg in new.items():
            normalized = normalize_config({**DEVICE_DEFAULTS, **cfg})
            if i not in old:
                r.configs[i] = normalized
                r.states[i] = State(last_off=time.monotonic(), cycle_armed=cfg.get("kind") != "dishwasher")
                r.device_modes[i] = "disabled"
                wiring_changed = True
            elif cfg != old[i]:
                delta = changed_keys(old[i], cfg)
                if delta & REFERENCE_KEYS or "kind" in delta:
                    # Binding edits cannot carry meter-derived learning into a new source.
                    self._archive(i, old[i])
                    if old[i].get("kind") == "dishwasher":
                        r.dishwasher_app.cancel(old[i], "Koppeling gewijzigd; nieuwe APP-vrijgave nodig")
                    r.dishwasher_app._seeded.discard(i)
                    r.dishwasher.tickets.pop(i, None)
                    r.states[i] = State(last_off=time.monotonic(), cycle_armed=False)
                    r.device_modes[i] = "disabled"  # New wiring requires explicit release.
                    wiring_changed = True
                r.configs[i] = normalized
                if "priority" in delta:
                    r.priorities.pop(i, None)
        if any(changed_keys(old.get(i,{}),new.get(i,{})) & {"kind","wallbox_precedence","dishwasher_priority_enabled","wallbox_power_policy"} for i in old.keys()|new.keys()):
            r.wallbox_guard=r._make_wallbox_guard()
        r.consumer_history.configs = {**keyed(options.get(ARCHIVED)), **r.configs}
        for group in (set(previous) | set(options)) - {"devices", ARCHIVED, PENDING}:
            if group.startswith("_live_") or previous.get(group) == options.get(group):
                continue
            self._apply_group(group, options.get(group), previous.get(group))
        # Rebind only when sources/IDs changed; already known APP baselines survive.
        if wiring_changed:
            r.dishwasher_app.close(); r.dishwasher_app.start()
        self.applied = deepcopy(dict(options))
        if previous.get("_private_bundle") != options.get("_private_bundle"):
            # Reload only the private prior, not the runtime or its listeners.
            from .private_bundle import load_private_bundle
            from .historical import load_bundled_seed
            from .unified_planner import BaseLoadModel
            import asyncio
            execute=getattr(r.hass,"async_add_executor_job",asyncio.to_thread)
            bundle=await execute(load_private_bundle)
            seed=await execute(load_bundled_seed,bundle)
            r.historical_seed=seed; r.local_pv.seed=seed; r.battery_analysis.seed=seed
            r.battery_analysis.update_settings(r.battery_analysis_settings)
            baseline=BaseLoadModel(seed)
            r.unified_planner.base_load.seed_hour=baseline.seed_hour
            r.unified_planner.base_load.seed_daytype=baseline.seed_daytype
            r.unified_plan=None; r.unified_planner.plan=None; r.unified_planner.last_plan_wall=0
        if hasattr(r, "platforms"):
            await r.platforms.refresh()
        r.store.async_delay_save(r._snapshot, 1)

    def _apply_group(self, group, value, previous):
        r = self.r
        value = deepcopy(value or {})
        if group == "priority_board":
            # Preserve timers/history for an existing house-first guard. A legacy
            # global EV-first guard must adopt per-device arbitration conservatively.
            from .house_first import HouseFirstGuard
            if not isinstance(r.wallbox_guard, HouseFirstGuard):
                r.wallbox_guard = r._make_wallbox_guard()
            r.unified_plan = None
            r.unified_planner.plan = None
            r.unified_planner.last_plan_wall = 0
        elif group == "settings":
            from .const import DEFAULTS
            old = r.settings
            r.settings = {**DEFAULTS, **r.entry.data, **value}
            if any(old.get(k) != r.settings.get(k) for k in ("grid_entity","grid_sign","export_entity","pv_entity","battery_power_entity","battery_sign")):
                r.filtered = None; r.invalid_since = None
                for s in r.states.values(): s.start_since = None
            if old.get("interval_s") != r.settings["interval_s"] and r._remove_timer:
                from datetime import timedelta
                from homeassistant.helpers.event import async_track_time_interval
                r._remove_timer()
                r._remove_timer = async_track_time_interval(r.hass,r.tick,timedelta(seconds=r.settings["interval_s"]))
            r.consumer_history.interval_s = float(r.settings["interval_s"])
            r.consumer_history.max_gap_s = max(30, r.settings["interval_s"]*2)
        elif group in ("capacity","economy","forecast","phase"):
            from .ems import CAPACITY_DEFAULTS, ECONOMY_DEFAULTS, FORECAST_DEFAULTS, PHASE_DEFAULTS
            defaults={"capacity":CAPACITY_DEFAULTS,"economy":ECONOMY_DEFAULTS,"forecast":FORECAST_DEFAULTS,"phase":PHASE_DEFAULTS}[group]
            setattr(r, group+"_settings", {**defaults, **value})
            if group == "phase": r.phase_learning.settings = r.phase_settings
        elif group == "planner":
            from .unified_planner import UNIFIED_PLANNER_DEFAULTS
            r.planner_settings = {**UNIFIED_PLANNER_DEFAULTS, **value}
            r.unified_planner.settings = r.planner_settings
            r.unified_plan = None; r.unified_planner.plan = None; r.unified_planner.last_plan_wall = 0
            r.unified_planner.quality.retention_days = r.planner_settings["quality_retention_days"]
            r.unified_planner.replay.retention_days = r.planner_settings["replay_retention_days"]
        elif group == "local_pv":
            from .pv_model import LOCAL_PV_DEFAULTS
            r.local_pv_settings={**LOCAL_PV_DEFAULTS,**value}; r.local_pv.settings=r.local_pv_settings; r.local_pv.enabled=bool(r.local_pv_settings["enabled"])
        elif group == "pv_forecast":
            from .pv_forecast_source import PV_FORECAST_DEFAULTS
            m=r.pv_forecast
            m.settings={**PV_FORECAST_DEFAULTS, **value};m.source.settings=m.settings;m.model.settings=m.settings
            m.last_update=None;m.hourly_cache={}
            m.source.last_scan=None;m.source.last_refresh=None
            m.source.coordinator_signature=None;m.source.coordinator_seen=None
        elif group == "battery_analysis":
            from .battery_analysis import BATTERY_ANALYSIS_DEFAULTS
            r.battery_analysis_settings={**BATTERY_ANALYSIS_DEFAULTS,**value}
            r.battery_analysis.update_settings(r.battery_analysis_settings)
        elif group == "analysis":
            from .analysis_export import ANALYSIS_DEFAULTS, AnalysisLogHandler
            was_enabled = bool(r.analysis.settings.get("enabled"))
            r.analysis.settings={**ANALYSIS_DEFAULTS,**value}
            is_enabled = bool(r.analysis.settings.get("enabled"))
            # Analysis can be enabled/disabled live. Keep the log hook in sync;
            # changing this setting must not require an integration reload.
            if is_enabled and not was_enabled and r.analysis.log_handler is None:
                r.analysis.log_handler = AnalysisLogHandler(r.analysis)
                logging.getLogger("custom_components.solar_pilot").addHandler(r.analysis.log_handler)
            elif was_enabled and not is_enabled and r.analysis.log_handler is not None:
                logging.getLogger("custom_components.solar_pilot").removeHandler(r.analysis.log_handler)
                r.analysis.log_handler = None
        elif group == "wallbox":
            from .wallbox import WALLBOX_DEFAULTS
            from .house_first import HOUSE_DEFAULTS
            from .consumer_wallbox import PRIORITY_DEFAULTS
            from .wallbox_profile import PROFILE_DEFAULTS
            from .wallbox_policy import SESSION_DEFAULTS
            r.wallbox_settings={**WALLBOX_DEFAULTS,**HOUSE_DEFAULTS,**PRIORITY_DEFAULTS,**PROFILE_DEFAULTS,**SESSION_DEFAULTS,**value}
            r.wallbox_profile.settings=r.wallbox_settings
            r.wallbox_profile.next_discovery=0;r.wallbox_profile.sources={};r.wallbox_profile.cached={}
            r.consumer_wallbox.settings=r.wallbox_settings
            r.wallbox_guard=r._make_wallbox_guard()
        elif group == "dhw":
            from .dhw import normalized_settings
            m=r.dhw;c=normalized_settings(value)
            keys=changed_keys(previous or {}, value)
            for k in keys: m.tunables.pop(k,None)
            m.config=c;m.settings={**c,**m.tunables};m.policy.settings=m.settings
            if "enabled" in keys: m.auto_enabled=bool(c["enabled"])
            m._comfort_forecast_stamp=None;m._prediction_check_wall=None
            m.policy.reset_stability()
        elif group == "smart_climate":
            from .thermal_climate import SMART_CLIMATE_DEFAULTS
            r.smart_climate.settings={**SMART_CLIMATE_DEFAULTS,**value}
        elif group in ("batteries","battery_fleet"):
            from .battery_fleet import BATTERY_DEFAULTS, BATTERY_FLEET_DEFAULTS
            if group=="batteries":r.battery_fleet.configs={b["id"]:{**BATTERY_DEFAULTS,**b} for b in (value or [])}
            else:r.battery_fleet.settings={**BATTERY_FLEET_DEFAULTS,**value}
        # _private_bundle is metadata. Existing import side-effects remain local.

    async def process_pending(self):
        """Retry only when a normal tick observes a safe boundary; never stop a device."""
        options=deepcopy(dict(self.r.entry.options)); queue=options.get(PENDING,{})
        if not queue:return
        changed=False
        for key,item in list(queue.items()):
            if item.get("kind")=="device":
                i=item["id"];old=keyed(options.get("devices")).get(i)
                if old != item["old"]:
                    item["reason"]="Actieve configuratie gewijzigd; voorstel eerst annuleren/herzien";continue
                block=self.device_block(i,old,item.get("new"))
                if block:item["reason"]=block;continue
                devices=keyed(options.get("devices"));new=item.get("new")
                if not new or item.get("replacement"):
                    devices.pop(i,None);ar=keyed(options.get(ARCHIVED))
                    ar[i]={**old,"archived_at":time.time(),"replaced_by":new["id"] if new else None};options[ARCHIVED]=list(ar.values())
                if new:devices[new["id"]]=new
                self._validate_bindings(keyed(options.get("devices")), devices, {k:v for k,v in queue.items() if k!=key})
                options["devices"]=list(devices.values())
            else:
                group=item["group"]
                if options.get(group) != item.get("old"):
                    item["reason"]="Actieve instellingen gewijzigd; voorstel eerst herzien";continue
                block=self.group_block(group,item.get("old"),item.get("new"))
                if block:item["reason"]=block;continue
                if item.get("new") is None:options.pop(group,None)
                else:options[group]=item["new"]
            queue.pop(key,None);changed=True
        if changed:
            options[PENDING]=queue
            self._validate_meter_scopes(dict(self.r.entry.options), options)
            self.last_message="Wachtende wijzigingen veilig toegepast; overige regeling bleef actief."
            self._persist(options);await self.accept(options);self.r.note(self.last_message)

    async def cancel_pending(self, keys):
        options=deepcopy(dict(self.r.entry.options));queue=options.get(PENDING,{})
        for key in keys:queue.pop(key,None)
        options[PENDING]=queue
        self._persist(options);await self.accept(options)
        self.last_message="Geselecteerde wachtende wijzigingen geannuleerd; actieve instellingen behouden."
        self.r.publish()
        return options

    def overview(self):
        pending=self.r.entry.options.get(PENDING,{})
        rows=[]
        for i,c in self.r.configs.items():
            rows.append({"id":i,"name":c.get("name",i),"kind":c.get("kind"),"appliance_type":c.get("appliance_type","dishwasher" if c.get("kind")=="dishwasher" else "other"),
                "mode":self.r.device_modes.get(i,"disabled"),"on":self.r.states[i].on,
                "pending":pending.get("device:"+i,{}).get("reason","")})
        return {"editable_while_active":True,"status":self.last_message,"error":self.error,
                "pending":[{"key":k,"name":v.get("old",{}).get("name",v.get("group",k)) if isinstance(v.get("old"),dict) else v.get("group",k),"reason":v.get("reason","")} for k,v in pending.items()],
                "devices":rows,"archives":[{"id":c["id"],"name":c.get("name",c["id"]),"archived_at":c.get("archived_at"),"replaced_by":c.get("replaced_by")} for c in self.r.entry.options.get(ARCHIVED,[])]}
