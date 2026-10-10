"""One command boundary: Panasonic is read-only; SG has one relay adapter.

The ordinary/battery routes never acquire authority over native heat-pump
entities or the reserved SG contact. Indirect scripts are admitted only when
their loaded Home Assistant sequence proves static, independent targets.
No cached proof survives changed script contents, bindings or registry data.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import re

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")
TARGET_KEYS = frozenset({"entity_id", "device_id", "area_id", "floor_id", "label_id", "target"})
NATIVE_DOMAINS = frozenset({"climate", "water_heater"})
NATIVE_PLATFORMS = frozenset({"aquarea", "aquarea_heat_pump", "panasonic_aquarea", "panasonic_cc"})
DIRECT_SERVICES = {
    "switch": frozenset({"turn_on", "turn_off"}),
    "input_boolean": frozenset({"turn_on", "turn_off"}),
    "number": frozenset({"set_value"}),
    "input_number": frozenset({"set_value"}),
    "button": frozenset({"press"}),
    "light": frozenset({"turn_on", "turn_off"}),
}
PURE_STEPS = frozenset({"condition", "delay", "wait_template", "wait_for_trigger", "variables", "stop"})
META_KEYS = frozenset({"alias", "enabled", "continue_on_error", "response_variable"})


def _mapping(value):
    return value if isinstance(value, Mapping) else {}


def _entity(value):
    return isinstance(value, str) and ENTITY.fullmatch(value) is not None


def _references(value, *, depth=0):
    """Only schema entity leaves, never prose or arbitrary user labels."""
    if depth > 8:
        return set()
    refs = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and (key.endswith("entity") or key.endswith("entities")):
                values = item if isinstance(item, (tuple, list)) else [item]
                refs.update(v for v in values if _entity(v))
            elif isinstance(item, Mapping):
                refs.update(_references(item, depth=depth + 1))
    return refs


class PanasonicCommandAuthority:
    def __init__(self, runtime):
        self.runtime = runtime

    def _registry(self):
        registry = er.async_get(self.runtime.hass)
        return registry, getattr(registry, "async_get", lambda _eid: None)

    def _current_config(self):
        return _mapping(_mapping(self.runtime.entry.options).get("sg_boost"))

    def _archive(self):
        archive = getattr(self.runtime, "panasonic_archive", None)
        if not isinstance(archive, Mapping):
            archive = _mapping(getattr(getattr(self.runtime, "store", None), "data", None)).get("panasonic_archive")
        return _mapping(archive)

    def native_references(self):
        config = self._current_config()
        refs = _references({k: v for k, v in config.items() if k != "entity_id"})
        options = _mapping(self.runtime.entry.options)
        backup = _mapping(self._archive().get("backup_options"))
        for source in (options, backup):
            refs.update(_references(_mapping(source.get("dhw"))))
            refs.update(_references(_mapping(source.get("smart_climate"))))
        return refs

    def _native_entry(self, row):
        platform = str(getattr(row, "platform", "")).casefold()
        if platform in NATIVE_PLATFORMS:
            return True
        entries = getattr(self.runtime.hass, "config_entries", None)
        lookup = getattr(entries, "async_get_entry", None)
        if callable(lookup):
            entry = lookup(getattr(row, "config_entry_id", None))
            if str(getattr(entry, "domain", "")).casefold() in NATIVE_PLATFORMS:
                return True
        return False

    def _native_device(self, device_id):
        if not device_id:
            return False
        try:
            from homeassistant.helpers import device_registry as dr
            device = dr.async_get(self.runtime.hass).async_get(device_id)
        except (ImportError, AttributeError, KeyError):
            return False
        if device is None:
            return False
        identifiers = getattr(device, "identifiers", set())
        if any(isinstance(v, tuple) and v and str(v[0]).casefold() in NATIVE_PLATFORMS
               for v in identifiers or ()):
            return True
        # A manufacturer alone could describe a television or unrelated device.
        description = str(getattr(device, "model", "")).casefold()
        return ("panasonic" in str(getattr(device, "manufacturer", "")).casefold()
                and any(word in description for word in ("aquarea", "heat pump", "heatpump", "t-cap")))

    def is_native(self, entity_id):
        if not _entity(entity_id):
            return True
        if entity_id.split(".", 1)[0] in NATIVE_DOMAINS:
            return True
        refs = self.native_references()
        if entity_id in refs:
            return True
        registry, lookup = self._registry()
        row = lookup(entity_id)
        if row is not None and self._native_entry(row):
            return True
        device_id = getattr(row, "device_id", None)
        if device_id and (self._native_device(device_id)
                          or any(getattr(lookup(ref), "device_id", None) == device_id for ref in refs)):
            return True
        # Native sibling entities may establish a known device even when no
        # configured sensor happens to be on that same device.
        entities = getattr(registry, "entities", {})
        if device_id and isinstance(entities, Mapping):
            return any(getattr(other, "device_id", None) == device_id
                       and (self._native_entry(other) or
                            str(getattr(other, "entity_id", "")).split(".", 1)[0] in NATIVE_DOMAINS)
                       for other in entities.values())
        return False

    def is_sg(self, entity_id):
        relay = self._current_config().get("entity_id")
        if not _entity(relay):
            return False
        if entity_id == relay:
            return True
        _registry, lookup = self._registry()
        relay_row, target_row = lookup(relay), lookup(entity_id)
        device_id = getattr(relay_row, "device_id", None)
        return bool(device_id and getattr(target_row, "device_id", None) == device_id)

    def _direct_target(self, domain, service, entity_id):
        if not _entity(entity_id) or entity_id.split(".", 1)[0] != domain:
            raise HomeAssistantError("Opdrachtdoel ongeldig; geen bediening verzonden")
        if self.is_native(entity_id):
            raise HomeAssistantError("Panasonic is alleen-lezen; alleen de aparte SG-contactadapter mag zonneboost aanvragen")
        if self.is_sg(entity_id):
            raise HomeAssistantError("SG-contact heeft één eigenaar; gewone toestel- en batterijbediening is geblokkeerd")
        if domain == "script":
            if service not in {"turn_on", "turn_off"}:
                raise HomeAssistantError("Scriptactie kan niet veilig worden gecontroleerd")
            self._inspect_script(entity_id, set(), [0])
        elif service not in DIRECT_SERVICES.get(domain, frozenset()):
            raise HomeAssistantError("Deze actuatoractie hoort niet bij de toegestane toestelbediening")

    def assert_allowed(self, domain, service, entity_id, extra=None):
        """Return a detached payload whose exact target cannot be overwritten."""
        if extra is not None and not isinstance(extra, Mapping):
            raise HomeAssistantError("Opdrachtgegevens ongeldig")
        payload = dict(extra or {})
        if TARGET_KEYS & payload.keys():
            raise HomeAssistantError("Opdrachtgegevens mogen het gecontroleerde doel niet wijzigen of uitbreiden")
        self._direct_target(domain, service, entity_id)
        return {"entity_id": entity_id, **deepcopy(payload)}

    def _script_sequence(self, entity_id):
        # HA Core 2026.10 ScriptEntity owns script.sequence; the EntityComponent
        # stored at hass.data['script'] provides get_entity(entity_id).
        data = getattr(self.runtime.hass, "data", {})
        component = _mapping(data).get("script")
        lookup = getattr(component, "get_entity", None)
        entity = lookup(entity_id) if callable(lookup) else None
        sequence = getattr(getattr(entity, "script", None), "sequence", None)
        if not isinstance(sequence, (list, tuple)):
            raise HomeAssistantError("Scriptinhoud niet controleerbaar; koppel een rechtstreeks toestel of controleer dit script")
        return sequence

    def _inspect_script(self, entity_id, visiting, budget):
        if entity_id in visiting or len(visiting) >= 12:
            raise HomeAssistantError("Recursieve scriptbediening kan niet veilig worden gecontroleerd")
        visiting = visiting | {entity_id}
        self._inspect_sequence(self._script_sequence(entity_id), visiting, budget)

    def _inspect_sequence(self, sequence, visiting, budget):
        if not isinstance(sequence, (list, tuple)):
            raise HomeAssistantError("Scriptvolgorde ongeldig of dynamisch")
        for step in sequence:
            budget[0] += 1
            if budget[0] > 500 or not isinstance(step, Mapping):
                raise HomeAssistantError("Script te complex of niet controleerbaar")
            keys = set(step) - META_KEYS
            service_key = "action" if "action" in step else "service" if "service" in step else None
            if service_key:
                if keys - {service_key, "target", "data", "data_template"}:
                    raise HomeAssistantError("Scriptactie bevat een verborgen of tweede uitvoeringspad")
                self._inspect_action(step, service_key, visiting, budget)
            elif keys & PURE_STEPS:
                if len(keys & PURE_STEPS) != 1 or keys - PURE_STEPS - {"timeout", "continue_on_timeout"}:
                    raise HomeAssistantError("Scriptstap bevat een niet controleerbare actie")
            elif "choose" in step:
                if keys - {"choose", "default"}:
                    raise HomeAssistantError("Scriptkeuze bevat een verborgen uitvoeringspad")
                choices = step["choose"]
                if not isinstance(choices, (list, tuple)):
                    raise HomeAssistantError("Scriptkeuze niet controleerbaar")
                for choice in choices:
                    if (not isinstance(choice, Mapping) or "sequence" not in choice
                            or set(choice) - {"conditions", "sequence", "alias"}):
                        raise HomeAssistantError("Scriptkeuze niet controleerbaar")
                    self._inspect_sequence(choice["sequence"], visiting, budget)
                self._inspect_sequence(step.get("default", []), visiting, budget)
            elif "if" in step:
                if keys - {"if", "then", "else"}:
                    raise HomeAssistantError("Scriptvoorwaarde bevat een verborgen uitvoeringspad")
                self._inspect_sequence(step.get("then", []), visiting, budget)
                self._inspect_sequence(step.get("else", []), visiting, budget)
            elif "repeat" in step:
                repeat = step["repeat"]
                if (keys != {"repeat"} or not isinstance(repeat, Mapping)
                        or set(repeat) - {"count", "while", "until", "for_each", "sequence"}):
                    raise HomeAssistantError("Scriptherhaling niet controleerbaar")
                self._inspect_sequence(repeat.get("sequence", []), visiting, budget)
            elif "parallel" in step:
                parallel = step["parallel"]
                if keys != {"parallel"} or not isinstance(parallel, (list, tuple)):
                    raise HomeAssistantError("Parallel script niet controleerbaar")
                for branch in parallel:
                    if isinstance(branch, Mapping) and "sequence" in branch:
                        if set(branch) - {"sequence"} - META_KEYS:
                            raise HomeAssistantError("Parallel script bevat een verborgen uitvoeringspad")
                        self._inspect_sequence(branch["sequence"], visiting, budget)
                    else:
                        self._inspect_sequence([branch], visiting, budget)
            elif "sequence" in step:
                if keys != {"sequence"}:
                    raise HomeAssistantError("Scriptvolgorde bevat een verborgen uitvoeringspad")
                self._inspect_sequence(step["sequence"], visiting, budget)
            else:
                raise HomeAssistantError("Script kan verborgen bediening bevatten; automatische uitvoering geblokkeerd")

    def _inspect_action(self, step, service_key, visiting, budget):
        action = step.get(service_key)
        if not isinstance(action, str) or not ENTITY.fullmatch(action):
            raise HomeAssistantError("Dynamische scriptactie kan niet worden gecontroleerd")
        domain, service = action.split(".", 1)
        if domain == "script" and service not in {"turn_on", "turn_off"}:
            # A direct script.some_name invocation has no target payload.
            script_id = f"script.{service}"
            if self.is_native(script_id) or self.is_sg(script_id):
                raise HomeAssistantError("Script verwijst naar een beschermde actuator")
            self._inspect_script(script_id, visiting, budget)
            return
        target = step.get("target", {})
        data = step.get("data", {})
        if not isinstance(target, Mapping) or not isinstance(data, Mapping) or step.get("data_template"):
            raise HomeAssistantError("Dynamische scriptdoelen of gegevens niet toegestaan")
        if (set(target) - {"entity_id"}) or (TARGET_KEYS - {"entity_id"}) & data.keys():
            raise HomeAssistantError("Scriptdoelen via apparaat, ruimte of proxy zijn niet controleerbaar")
        target_ids = target.get("entity_id", data.get("entity_id"))
        if "entity_id" in target and "entity_id" in data:
            raise HomeAssistantError("Script bevat dubbele commandodoelen")
        ids = [target_ids] if isinstance(target_ids, str) else target_ids
        if not isinstance(ids, (list, tuple)) or not ids or not all(_entity(eid) for eid in ids):
            raise HomeAssistantError("Script vereist vaste expliciete entity-doelen")
        for eid in ids:
            target_domain = eid.split(".", 1)[0]
            routed_domain = target_domain if domain == "homeassistant" and service in {"turn_on", "turn_off"} else domain
            if routed_domain != target_domain or self.is_native(eid) or self.is_sg(eid):
                raise HomeAssistantError("Script probeert Panasonic of het gereserveerde SG-contact te bedienen")
            if routed_domain == "script":
                self._inspect_script(eid, visiting, budget)
            elif service not in DIRECT_SERVICES.get(routed_domain, frozenset()):
                raise HomeAssistantError("Scriptactie kan een ongecontroleerde proxy bedienen")

