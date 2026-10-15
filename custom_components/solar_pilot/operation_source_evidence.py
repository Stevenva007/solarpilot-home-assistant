"""Closed retained source semantics, without device identities or task claims.

The known SDK's DeviceAction describes specialStatus, including its OFF value.
Retaining that contract explains a raw historical field; it never rewrites the
old field, proves global OFF, proves compressor operation or grants control.
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import math
import re
import sys
import textwrap
from types import CodeType

CONTRACT_ID = "aioaquarea_ng_1_3_1_special_status"
# Only old stored records lack capability evidence. These labels validate that
# old historical format; they never admit a current loaded provider.
_LEGACY_SPECIAL_STATUS_VERSIONS = frozenset({"1.5.2", "1.5.3", "1.5.4"})
SEMANTIC_CONTRACT_ID = "aquarea_special_status_action_v1"
MAX_ZONES = 2
MAX_TIME = 4102444800
ACTIONS = frozenset({"OFF", "IDLE", "HEATING", "COOLING", "HEATING_WATER"})
MODES = {"OFF":"off", "HEAT":"heating", "COOL":"cooling",
         "AUTO_HEAT":"heating", "AUTO_COOL":"cooling"}
REASONS = frozenset({"provider_contract_unverified", "native_source_mapping_unverified",
                    "native_typed_snapshot_unverified", "native_poll_not_current",
                    "native_typed_value_unverified", "native_source_not_current",
                    "native_source_value_conflict", "known_special_status_action_mapping",
                    "provider_semantics_unavailable", "provider_semantics_changed"})



def valid_semantic_contract(value):
    """Closed capture-time capability proof; release numbers are diagnostic."""
    return (isinstance(value, dict) and set(value) == {"schema", "contract", "verified", "basis", "fingerprint"}
            and type(value.get("schema")) is int and value["schema"] == 1
            and value.get("contract") == SEMANTIC_CONTRACT_ID and value.get("verified") is True
            and value.get("basis") == "loaded_source" and isinstance(value.get("fingerprint"), str)
            and re.fullmatch(r"[0-9a-f]{64}", value["fingerprint"]) is not None)


def special_status_contract(raw):
    """Read capture-time semantics; never attach today's proof to old points."""
    if not isinstance(raw, dict):
        return False
    if "compatibility" in raw:
        return valid_semantic_contract(raw["compatibility"])
    provider = raw.get("provider") if isinstance(raw.get("provider"), dict) else {}
    version = provider.get("integration_version")
    return (provider.get("integration_domain") == "aquarea" and isinstance(version, str)
            and version in _LEGACY_SPECIAL_STATUS_VERSIONS
            and provider.get("library_distribution") == "aioaquarea-ng" and provider.get("library_version") == "1.3.1")


def _constant(value):
    if isinstance(value, CodeType):
        return ("code", _code_signature(value))
    if isinstance(value, tuple):
        return ("tuple", tuple(_constant(item) for item in value))
    if isinstance(value, frozenset):
        return ("frozenset", frozenset(_constant(item) for item in value))
    return type(value).__name__, value


def _code_signature(code):
    """Ignore source locations while retaining actual executable semantics."""
    return (code.co_code, tuple(_constant(value) for value in code.co_consts), code.co_names,
            code.co_varnames, code.co_freevars, code.co_cellvars, code.co_argcount,
            code.co_posonlyargcount, code.co_kwonlyargcount, code.co_flags & 0xFFF,
            code.co_stacksize, getattr(code, "co_exceptiontable", b""))


def _function_tree(function):
    source = inspect.getsource(function)
    if len(source) > 131072:
        raise ValueError("Native source exceeds inspection bound")
    tree = ast.parse(textwrap.dedent(source))
    node = next((item for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if node is None or sum(1 for _ in ast.walk(node)) > 8192:
        raise ValueError("Native function is not inspectable")
    compiled = compile(ast.Module(body=[node], type_ignores=[]), "<aquarea-semantic-contract>", "exec", dont_inherit=True)
    code = next((value for value in compiled.co_consts if isinstance(value, CodeType) and value.co_name == node.name), None)
    if code is None or _code_signature(code) != _code_signature(function.__code__):
        raise ValueError("Source does not match loaded native code")
    return node


def _body(node):
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False)


def _bound_method(function, arguments, data, critical=()):
    code = getattr(function, "__code__", None)
    if (not isinstance(code, CodeType) or code.co_argcount != len(arguments)
            or code.co_varnames[:len(arguments)] != arguments or code.co_kwonlyargcount
            or code.co_flags & (inspect.CO_VARARGS | inspect.CO_VARKEYWORDS)
            or code.co_freevars or code.co_cellvars
            or getattr(function, "__defaults__", None) or getattr(function, "__kwdefaults__", None)):
        return False
    for name in critical:
        expected = getattr(data, name, None)
        if (expected is None or function.__globals__.get(name) is not expected
                or name in code.co_varnames or name in code.co_freevars or name in code.co_cellvars):
            return False
    return True


def loaded_semantic_identity():
    """Cheap cache key, with no source read or native property execution."""
    identities = []
    for module_name, class_name, names in (
            ("aioaquarea.data", "Device", ("current_action", "operation_status")),
            ("aioaquarea.device_manager", "DeviceManager", ("get_device_status",)),
            ("aioaquarea.entities", "DeviceImpl", ("current_action", "operation_status")),
            ("aioaquarea.core", "DeviceImpl", ("current_action", "operation_status"))):
        module = sys.modules.get(module_name)
        cls = getattr(module, class_name, None)
        identities.extend((id(module), id(cls)))
        for name in names:
            try:
                value = inspect.getattr_static(cls, name)
                function = value.fget if isinstance(value, property) else value
                identities.extend((id(value), id(getattr(function, "__code__", None))))
                namespace = getattr(function, "__globals__", {})
                identities.extend(id(namespace.get(key)) for key in ("DeviceStatus", "OperationStatus", "DeviceAction", "DeviceDirection", "ExtendedOperationMode"))
            except (AttributeError, TypeError):
                identities.extend((None, None))
    return tuple(identities)


def _returned_status_calls(parser):
    """Every return must directly follow its own actual typed construction."""
    if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda))
           for node in ast.walk(parser) if node is not parser):
        return None
    returns, calls = [], []
    def visit(node):
        for _name, value in ast.iter_fields(node):
            if isinstance(value, list):
                for index, child in enumerate(value):
                    if isinstance(child, ast.Return):
                        previous = value[index-1] if index else None
                        if (not isinstance(previous, ast.Assign) or len(previous.targets) != 1
                                or not isinstance(previous.targets[0], ast.Name) or not isinstance(child.value, ast.Name)
                                or previous.targets[0].id != child.value.id or not isinstance(previous.value, ast.Call)
                                or not isinstance(previous.value.func, ast.Name) or previous.value.func.id != "DeviceStatus"):
                            raise ValueError("Returned status is not the inspected construction")
                        returns.append(child)
                        calls.append(previous.value)
                    if isinstance(child, ast.AST):
                        visit(child)
            elif isinstance(value, ast.AST):
                visit(value)
    visit(parser)
    constructors = [node for node in ast.walk(parser) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == "DeviceStatus"]
    if not returns or {id(node) for node in constructors} != {id(node) for node in calls}:
        return None
    # Keep the mapping bound to the actual unmodified response status dict.
    device_assignments = [node for node in ast.walk(parser) if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "device" for target in node.targets)]
    expected_device = ast.dump(ast.parse('json_response.get("status")', mode="eval").body, include_attributes=False)
    if (len(device_assignments) != 1 or len(device_assignments[0].targets) != 1
            or ast.dump(device_assignments[0].value, include_attributes=False) != expected_device):
        return None
    approved_target = device_assignments[0].targets[0]
    parents = {id(child): parent for parent in ast.walk(parser) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(parser):
        if isinstance(node, ast.Name) and node.id == "device":
            if isinstance(node.ctx, (ast.Store, ast.Del)) and node is not approved_target:
                return None
            if isinstance(node.ctx, ast.Load):
                parent = parents.get(id(node))
                call = parents.get(id(parent)) if parent is not None else None
                if (not isinstance(parent, ast.Attribute) or parent.value is not node or parent.attr != "get"
                        or not isinstance(call, ast.Call) or call.func is not parent):
                    return None
        if isinstance(node, ast.ExceptHandler) and node.name == "device":
            return None
        if isinstance(node, (ast.Global, ast.Nonlocal)) and "device" in node.names:
            return None
    for node in ast.walk(parser):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "device" and node.func.attr != "get":
                return None
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            targets = node.targets if isinstance(node, (ast.Assign, ast.Delete)) else [node.target]
            for target in targets:
                if isinstance(target, (ast.Subscript, ast.Attribute)) and isinstance(target.value, ast.Name) and target.value.id == "device":
                    return None
    return calls


def inspect_loaded_aquarea_semantics():
    """Inspect loaded code off-loop; never call a provider function or network.

    Release numbers, comments and formatting do not establish authority. The
    parser's real returned status, raw field and inherited action must retain
    their meaning. Unrecognised implementations stay unknown for source review.
    """
    unknown = {"compatibility": None, "compatibility_state": "unknown",
               "reason_code": "provider_semantics_unavailable", "compatibility_detail": "loaded_semantics_not_inspectable"}
    try:
        data = sys.modules.get("aioaquarea.data")
        manager = sys.modules.get("aioaquarea.device_manager")
        entities = sys.modules.get("aioaquarea.entities") or sys.modules.get("aioaquarea.core")
        device, implementation = getattr(data, "Device", None), getattr(entities, "DeviceImpl", None)
        action = inspect.getattr_static(device, "current_action")
        operation = inspect.getattr_static(device, "operation_status")
        parser_function = getattr(getattr(manager, "DeviceManager", None), "get_device_status")
        if (not isinstance(action, property) or not isinstance(operation, property)
                or inspect.getattr_static(implementation, "current_action") is not action
                or inspect.getattr_static(implementation, "operation_status") is not operation
                or not _bound_method(parser_function, ("self", "device_info"), data, ("DeviceStatus", "OperationStatus"))
                or not _bound_method(action.fget, ("self",), data, ("DeviceAction", "DeviceDirection", "ExtendedOperationMode", "OperationStatus"))
                or not _bound_method(operation.fget, ("self",), data)):
            return unknown
        parser = _function_tree(parser_function)
        calls = _returned_status_calls(parser)
        if not calls:
            return unknown
        fields = [next((field.value for field in call.keywords if field.arg == "operation_status"), None) for call in calls]
        expected_field = ast.dump(ast.parse('OperationStatus(device.get("specialStatus"))', mode="eval").body, include_attributes=False)
        field_dumps = [ast.dump(field, include_attributes=False) if field is not None else None for field in fields]
        if any(value != expected_field for value in field_dumps):
            global_field = ast.dump(ast.parse('OperationStatus(device.get("operationStatus"))', mode="eval").body, include_attributes=False)
            if any(value == global_field for value in field_dumps):
                return {**unknown, "compatibility_state": "incompatible", "reason_code": "provider_semantics_changed",
                        "compatibility_detail": "operation_status_no_longer_special_status"}
            return {**unknown, "compatibility_state": "incompatible", "reason_code": "provider_semantics_changed",
                    "compatibility_detail": "operation_status_mapping_changed"}
        action_tree, operation_tree = _function_tree(action.fget), _function_tree(operation.fget)
        expected_action = ast.parse('''def current_action(self):
    if self.operation_status == OperationStatus.OFF:
        return DeviceAction.OFF
    direction = self.current_direction
    if direction == DeviceDirection.IDLE:
        return DeviceAction.IDLE
    if self.has_tank and direction == DeviceDirection.WATER and self.tank.operation_status == OperationStatus.ON:
        return DeviceAction.HEATING_WATER
    mode = self.mode
    if direction == DeviceDirection.PUMP and mode != ExtendedOperationMode.OFF:
        return DeviceAction.HEATING if mode in (ExtendedOperationMode.HEAT, ExtendedOperationMode.AUTO_HEAT) else DeviceAction.COOLING
    return DeviceAction.IDLE
''').body[0]
        expected_operation = ast.parse('def operation_status(self):\n    return self._status.operation_status').body[0]
        if _body(action_tree) != _body(expected_action) or _body(operation_tree) != _body(expected_operation):
            return {**unknown, "compatibility_state": "incompatible", "reason_code": "provider_semantics_changed",
                    "compatibility_detail": "action_or_status_getter_semantics_changed"}
        fingerprint = hashlib.sha256((ast.dump(parser, include_attributes=False) + _body(action_tree) + _body(operation_tree)).encode()).hexdigest()
        proof = {"schema": 1, "contract": SEMANTIC_CONTRACT_ID, "verified": True,
                 "basis": "loaded_source", "fingerprint": fingerprint}
        return {"compatibility": proof, "compatibility_state": "compatible", "reason_code": "known_special_status_action_mapping",
                "compatibility_detail": "loaded_special_status_action_semantics", "_loaded_device_class": implementation}
    except (AttributeError, TypeError, ValueError, OSError, SyntaxError, RuntimeError):
        return unknown


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _time(value):
    value = _number(value)
    return value if value is not None and 0 < value <= MAX_TIME else None


def _enum(value, allowed, default=None):
    return value if isinstance(value, str) and value in allowed else default


def _version(value):
    return value if isinstance(value, str) and re.fullmatch(r"\d{1,4}\.\d{1,4}\.\d{1,4}(?:[-+][A-Za-z0-9.]{1,16})?", value) else None


def _dict(value):
    return value if isinstance(value, dict) else {}


def _project(raw, captured_at, stale_s, *, retained=False):
    if not isinstance(raw, dict):
        return None
    now = _time(captured_at)
    outer_stale, source_stale = _number(stale_s), _number(raw.get("stale_s"))
    stale = (min(outer_stale, source_stale) if outer_stale is not None and source_stale is not None
             and 0 < outer_stale <= 600 and 0 < source_stale <= 600 else None)
    def fresh(value):
        return bool(now is not None and value is not None and stale is not None and -5 <= now-value <= stale)
    def observed(row):
        stamp, native = _time(row.get("observed_at")), _time(row.get("native_observed_at"))
        return {"observed_at":stamp, "fresh":fresh(stamp),
                "native_observed_at":native, "native_fresh":fresh(native)}

    provider_raw = _dict(raw.get("provider"))
    provider = {"integration_domain":_enum(provider_raw.get("integration_domain"), {"aquarea"}),
                "integration_version":_version(provider_raw.get("integration_version")),
                "library_distribution":_enum(provider_raw.get("library_distribution"), {"aioaquarea-ng"}),
                "library_version":_version(provider_raw.get("library_version"))}
    provider_loaded = raw.get("provider_loaded") is True
    known = (type(raw.get("schema")) is int and raw["schema"] == 1 and raw.get("read_only") is True and provider_loaded
             and raw.get("contract_id") == CONTRACT_ID and raw.get("action_semantics") == "special_status"
             and provider["integration_domain"] == "aquarea" and special_status_contract(raw))
    pump_raw, direction_raw, program_raw, tank_raw = (_dict(raw.get(key)) for key in ("pump","direction","program","tank"))
    pump = {"state":_enum(pump_raw.get("state"), {"on","off"}, "unknown"), **observed(pump_raw)}
    direction = {"state":_enum(direction_raw.get("state"), {"IDLE","PUMP","WATER"}), **observed(direction_raw)}
    mode = _enum(program_raw.get("raw_mode"), MODES)
    program = {"state":_enum(program_raw.get("state"), {"heating","cooling","off"}),
               "raw_mode":mode, **observed(program_raw)}
    tank = {"enabled":tank_raw.get("enabled") if type(tank_raw.get("enabled")) is bool else None, **observed(tank_raw)}
    zones_raw = raw.get("zones")
    zones = []
    valid_zones = isinstance(zones_raw, list) and 1 <= len(zones_raw) <= MAX_ZONES and all(isinstance(row,dict) for row in zones_raw)
    if isinstance(zones_raw, list):
        for index, value in enumerate(zones_raw[:MAX_ZONES], 1):
            row = _dict(value)
            zones.append({"number":index,
                          "enabled":row.get("enabled") if type(row.get("enabled")) is bool else None,
                          "state":_enum(row.get("state"), {"heat","cool","auto","off"}), **observed(row)})
    original = _time(raw.get("observed_at"))
    registered = raw.get("native_device_registered") is True
    claimed = raw.get("verified") is True if retained else raw.get("status") == "verified"
    valid_optional = lambda row: (row.get("native_observed_at") is None or _time(row.get("native_observed_at")) is not None)
    typed_rows = (tank_raw.get("enabled") is None or type(tank_raw.get("enabled")) is bool)
    if valid_zones:
        typed_rows = typed_rows and all((row.get("enabled") is None or type(row.get("enabled")) is bool)
                                      and (row.get("state") is None or _enum(row.get("state"), {"heat","cool","auto","off"}) is not None)
                                      for row in zones_raw)
    all_rows = [pump_raw,direction_raw,program_raw,tank_raw,*zones_raw] if valid_zones else []
    verified = bool(known and claimed and provider_loaded and registered and fresh(original)
                    and pump["state"] != "unknown" and direction["state"] is not None and program["state"] is not None
                    and mode is not None and MODES[mode] == program["state"] and valid_zones and typed_rows
                    and all(valid_optional(row) for row in all_rows)
                    and all(row["fresh"] for row in (pump,direction,program,tank,*zones)))
    result = {"schema":1, "read_only":True, "provider":provider,
            "contract_id":CONTRACT_ID if known else None, "action_semantics":"special_status" if known else "unknown",
            "verified":verified, "provider_loaded":provider_loaded, "native_device_registered":registered,
            "observed_at":original, "stale_s":stale, "fresh":fresh(original),
            "raw_device_action":_enum(raw.get("raw_device_action"), ACTIONS),
            "reason_code":_enum(raw.get("reason_code"), REASONS, "provider_contract_unverified"),
            "pump":pump, "direction":direction, "program":program, "tank":tank, "zones":zones}
    if "compatibility" in raw:
        result["compatibility"] = dict(raw["compatibility"]) if valid_semantic_contract(raw["compatibility"]) else None
    return result


def contract_evidence(raw, captured_at, stale_s):
    """Project one current contract; absent legacy metadata remains absent."""
    return _project(raw, captured_at, stale_s)


def retained_contract_evidence(raw, captured_at, stale_s):
    """Validate closed stored fields and freshness at their original capture.

    No contemporary device, mapping or timestamp is read. Unknown contracts
    cannot be promoted by optimistic booleans, a new library version, private
    strings or a stale source marked fresh. Additional keys are rejected.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Ongeldig historisch broncontract")
    clean = _project(raw, captured_at, stale_s, retained=True)
    if clean != raw:
        raise ValueError("Tegenstrijdig historisch broncontract")
    # Equality treats 1 as True in Python; require actual booleans and schema
    # types separately before accepting persisted flags.
    if (type(raw.get("schema")) is not int or raw["schema"] != 1 or raw.get("read_only") is not True
            or any(type(raw.get(key)) is not bool for key in ("verified","provider_loaded","native_device_registered","fresh"))):
        raise ValueError("Ongeldig historisch broncontract")
    for row in [raw["pump"],raw["direction"],raw["program"],raw["tank"],*raw["zones"]]:
        if any(type(row.get(key)) is not bool for key in ("fresh","native_fresh")):
            raise ValueError("Ongeldig historisch broncontract")
        if "enabled" in row and row["enabled"] is not None and type(row["enabled"]) is not bool:
            raise ValueError("Ongeldig historisch broncontract")
    if any(type(row.get("number")) is not int for row in raw["zones"]):
        raise ValueError("Ongeldig historisch broncontract")
    return clean
