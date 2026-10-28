"""Durable temporary Wallbox precedence; no actuator or configuration writes.

The general choice is a one-shot fan-out, not a master lock. Individual edits
remain independent until the general choice returns to Auto (also on expiry).
All deadlines are absolute UTC seconds, so a restart never grants extra time.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import time

from homeassistant.exceptions import HomeAssistantError

GROUP = "wallbox_priority"
DURATIONS = {"30m": 1800, "1h": 3600, "2h": 7200, "3h": 10800,
             "4h": 14400, "5h": 18000}
OPTIONS = ("auto", *DURATIONS, "until_auto")
GLOBAL = "global"
EXTRA = "dhw_extra"


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


class _Scope:
    """Private command token retains identities through remove/re-add (ABA)."""
    def __init__(self, wallbox_binding, bindings, objects):
        self.wallbox_binding, self.bindings, self.objects = wallbox_binding, bindings, objects

    def __eq__(self, other):
        return (isinstance(other, _Scope) and self.wallbox_binding == other.wallbox_binding
                and self.bindings == other.bindings and self.objects.keys() == other.objects.keys()
                and all(value is other.objects[key] for key, value in self.objects.items()))


class WallboxPriority:
    def __init__(self, runtime):
        self.r = runtime
        self._data = self._empty()

    def _empty(self):
        return {"schema": 1, "entry_id": self.r.entry.entry_id,
                "wallbox_binding": self._wallbox_binding(), "general": None, "targets": {}}

    def _wallbox_binding(self):
        settings = self.r.wallbox_settings
        return _digest({key: settings.get(key) for key in (
            "enabled", "power_entity", "status_entity", "mode_entity",
            "session_mode_entity", "connected_entity")})

    def eligible(self):
        """Bindings exclude labels and priorities but include physical identities."""
        bindings = {}
        for device_id, config in self.r.configs.items():
            if (config.get("kind", "switch") not in ("switch", "number", "script")
                    or config.get("appliance_type") == "dishwasher"):
                continue
            identity = {key: value for key, value in config.items() if (
                key.endswith("_entity") or key.endswith("_script") or key in (
                    "id", "kind", "control_unit", "profile_id", "profile", "non_interruptible"))}
            bindings["device:" + device_id] = _digest(identity)
        # SG has fixed precedence over confirmed autonomous solar charging.
        # Existing SG choices are filtered by _project; a general preference
        # continues to fan out only to the ordinary eligible devices.
        return bindings

    @staticmethod
    def _valid_choice(choice, wall, binding=None):
        if (not isinstance(choice, dict) or set(choice) != {
                "option", "created_at", "expires_at", "binding"}
                or choice.get("option") not in (*DURATIONS, "until_auto")
                or not _finite(choice.get("created_at"))
                or not 0 < choice["created_at"] <= wall
                or binding is not None and choice.get("binding") != binding):
            return False
        if choice["option"] == "until_auto":
            return choice["expires_at"] is None
        expiry = choice.get("expires_at")
        return (_finite(expiry) and expiry > wall and
                abs(expiry-choice["created_at"]-DURATIONS[choice["option"]]) < .001)

    def _project(self, data, wall):
        empty = self._empty()
        if (not isinstance(data, dict) or set(data) != set(empty)
                or data.get("schema") != 1 or type(data.get("schema")) is not int
                or data.get("entry_id") != self.r.entry.entry_id
                or data.get("wallbox_binding") != empty["wallbox_binding"]
                or not isinstance(data.get("targets"), dict)):
            return empty
        general = data.get("general")
        # General expiry/reset also clears later individual exceptions. A corrupt
        # or future general record cannot leave its children unexpectedly active.
        if general is not None and not self._valid_choice(general, wall, empty["wallbox_binding"]):
            return empty
        bindings = self.eligible()
        empty["general"] = deepcopy(general)
        empty["targets"] = {target: deepcopy(choice) for target, choice in data["targets"].items()
                            if target in bindings and self._valid_choice(choice, wall, bindings[target])}
        return empty

    def snapshot(self):
        # Snapshot the authoritative journal, not a projection. An expiry cleanup
        # is its own saved transaction, and read-only overview calls never edit it.
        return deepcopy(self._data)

    def restore(self, data, wall=None):
        self._data = self._project(data, time.time() if wall is None else wall)

    def scope(self, target):
        """Stable binding token for a trusted command across asynchronous waits."""
        bindings = self.eligible()
        selected = bindings if target == GLOBAL else ({target: bindings[target]} if isinstance(target, str) and target in bindings else {})
        objects = {key: self.r.configs[key[7:]] if key.startswith("device:") else self.r.sg_boost.settings
                   for key in selected}
        return _Scope(self._wallbox_binding(), selected, objects)

    def live(self):
        entries = getattr(self.r.hass, "config_entries", None)
        lookup = getattr(entries, "async_get_entry", None)
        current = lookup(self.r.entry.entry_id) if lookup is not None else self.r.entry
        return (not self.r._closed and not self.r.removal_requested
                and current is self.r.entry and getattr(current, "runtime_data", self.r) is self.r)

    def retire(self, device_id):
        """Committed live-options identity retirement; never grants a new hold."""
        self._data["targets"].pop("device:" + device_id, None)

    def active(self, target, wall=None):
        data = self._project(self._data, time.time() if wall is None else wall)
        return target in data["targets"]

    def any_active(self):
        return bool(self._project(self._data, time.time())["targets"])

    def effective_config(self, device_id, config):
        if not self.active("device:" + device_id):
            return config
        return {**config, "_wallbox_priority_override": True,
                "_priority_board_before_wallbox": False,
                "_priority_board_wallbox_power": False,
                "wallbox_precedence": "wallbox_first", "wallbox_power_policy": "never",
                "allow_wallbox_reclaim": False}

    def overlay_order(self, order):
        """Move only currently forced predecessors, preserving relative order."""
        if "wallbox" not in order:
            return list(order)
        data = self._project(self._data, time.time())
        position = order.index("wallbox")
        before, after = order[:position], order[position+1:]
        moved = [key for key in before if key in data["targets"]]
        return [key for key in before if key not in data["targets"]] + ["wallbox"] + moved + after

    def _choice_view(self, target, choice, wall, *, eligible=True):
        option = choice["option"] if choice else "auto"
        expiry = choice["expires_at"] if choice else None
        return {"target": target, "option": option,
                "mode": "wallbox_first" if choice else "auto", "active": bool(choice),
                "duration_s": DURATIONS.get(option), "expires_at": expiry,
                "remaining_s": max(0, math.ceil(expiry-wall)) if expiry is not None else 0,
                "indefinite": option == "until_auto", "eligible": eligible,
                "label": ("tot ik terug op automatisch zet" if option == "until_auto" else
                          "Automatisch" if option == "auto" else "Wallbox krijgt tijdelijk voorrang")}

    def overview(self):
        wall = time.time()
        data = self._project(self._data, wall)
        bindings = self.eligible()
        general = self._choice_view(GLOBAL, data["general"], wall)
        choices = {target: self._choice_view(target, data["targets"].get(target), wall)
                   for target in bindings}
        expected = data["general"]
        mixed = any((bool(choice) != bool(expected) or choice and expected and
                     (choice["option"], choice["created_at"], choice["expires_at"]) !=
                     (expected["option"], expected["created_at"], expected["expires_at"]))
                    for target in bindings for choice in (data["targets"].get(target),))
        return {"general": general,
                "devices": {target[7:]: value for target, value in choices.items() if target.startswith("device:")},
                "sg_boost": choices.get(EXTRA), "mixed": bool(mixed),
                "available": self.r.wallbox_settings.get("enabled") is True and bool(bindings or data["general"]),
                "durations_s": list(DURATIONS.values()), "options": list(OPTIONS), "observed_at": wall}

    async def _commit(self, desired, *, scope=None, target=None):
        if desired == self._data:
            return
        snapshot = self.r._snapshot()
        snapshot[GROUP] = deepcopy(desired)
        try:
            await self.r.store.async_save(snapshot)
        except Exception as err:
            raise HomeAssistantError("Wallbox-voorrang kon niet worden opgeslagen; de vorige keuze blijft behouden.") from err
        if scope is not None and (not self.live() or self.scope(target) != scope):
            # Remove this known-unapplied choice from the durable journal too.
            # Concurrent committed retirement has already removed its target
            # from _data and must not be resurrected by rollback.
            rollback = self.r._snapshot()
            rollback[GROUP] = self.snapshot()
            try:
                await self.r.store.async_save(rollback)
            except Exception as err:
                raise HomeAssistantError("De koppeling is gewijzigd en de vorige voorkeur kon niet opnieuw worden opgeslagen; controleer na herstart de Wallbox-voorrang.") from err
            raise HomeAssistantError("De toestelkoppeling is tijdens opslaan gewijzigd; vernieuw het overzicht.")
        # Save precedes activation; a failed or cancelled save grants no policy.
        self._data = desired

    async def expire(self):
        await self._commit(self._project(self._data, time.time()))

    async def set(self, target, option, *, expected_scope=None):
        """Caller owns runtime lock. This method never calls a device or ticks."""
        if not isinstance(target, str) or not isinstance(option, str) or option not in OPTIONS:
            raise HomeAssistantError("Kies Automatisch, een toegestane tijdsduur of tot handmatig automatisch.")
        scope = self.scope(target)
        if expected_scope is not None and expected_scope != scope:
            raise HomeAssistantError("De toestelkoppeling is gewijzigd; vernieuw het overzicht.")
        wall = time.time()
        desired = self._project(self._data, wall)
        bindings = self.eligible()
        if target != GLOBAL and target not in bindings:
            raise HomeAssistantError("Dit toestel ondersteunt geen tijdelijke Wallbox-voorrang.")
        if option != "auto" and self.r.wallbox_settings.get("enabled") is not True:
            raise HomeAssistantError("Schakel eerst de bestaande Wallbox-monitor in.")
        if option != "auto" and target == GLOBAL and not bindings:
            raise HomeAssistantError("Er is geen toestel waarvoor Wallbox-voorrang kan worden ingesteld.")
        def choice(binding):
            return {"option": option, "created_at": wall,
                    "expires_at": wall+DURATIONS[option] if option in DURATIONS else None,
                    "binding": binding}
        if target == GLOBAL:
            desired["general"] = None if option == "auto" else choice(desired["wallbox_binding"])
            desired["targets"] = {} if option == "auto" else {key: choice(binding) for key, binding in bindings.items()}
        elif option == "auto":
            desired["targets"].pop(target, None)
        else:
            desired["targets"][target] = choice(bindings[target])
        await self._commit(desired, scope=scope, target=target)
        return self.overview()
