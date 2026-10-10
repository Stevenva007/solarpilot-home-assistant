"""Bounded, entry-local analysis advice. This module has no control operations.

Source association proves only that an advice file names a locally exported
artifact. It does not authenticate an analyst or approve a recommendation.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import re

from homeassistant.helpers.storage import Store

from .const import DOMAIN, VERSION

FEEDBACK_SCHEMA = "solarpilot.analysis_feedback"
FEEDBACK_VERSION = 1
MAX_FEEDBACK_BYTES = 1024 * 1024
MAX_KNOWN_EXPORTS = 50
MAX_JSON_DEPTH = 64
RECOMMENDATION_CATEGORIES = frozenset({
    "warmtepomp_setting", "solarpilot_setting", "logic_update", "observation",
})
CONFIDENCES = frozenset({"low", "medium", "high"})
SOURCE_FIELDS = frozenset({"export_id", "export_sha256", "release", "created_at"})
_EXPORT_ID = re.compile(r"export_[a-f0-9]{32}\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_REVISION = re.compile(r"[a-f0-9]{16}\Z")
_QUESTION_ID = re.compile(r"[a-zA-Z0-9_][a-zA-Z0-9_.:-]{0,159}\Z")
_PROPOSAL_ID = re.compile(r"[a-z0-9][a-z0-9._:-]{0,119}\Z")


class FeedbackValidationError(ValueError):
    """The advice file cannot be represented by the read-only schema."""


def storage_key(entry_id):
    return f"{DOMAIN}.{entry_id}.analysis_feedback"


def _object(value, fields, path):
    if type(value) is not dict or set(value) != fields:
        raise FeedbackValidationError(f"{path}: gebruik uitsluitend de vereiste velden van het adviesformaat")


def _text(value, path, limit=8000):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise FeedbackValidationError(f"{path}: tekst ontbreekt of is te lang")
    # Valid UTF-8 and plain text only; HTML-like text remains text in the UI.
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as err:
        raise FeedbackValidationError(f"{path}: ongeldige Unicode-tekst") from err
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise FeedbackValidationError(f"{path}: ongeldige teksttekens")


def _timestamp(value, path):
    _text(value, path, 80)
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as err:
        raise FeedbackValidationError(f"{path}: gebruik een UTC-datum in ISO8601-formaat") from err
    if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(stamp):
        raise FeedbackValidationError(f"{path}: gebruik een UTC-datum met tijdzone")


def _texts(value, path):
    if type(value) is not list or len(value) > 20:
        raise FeedbackValidationError(f"{path}: maximaal 20 tekstregels")
    for index, item in enumerate(value):
        _text(item, f"{path}[{index}]", 2000)


def validate_source_export(value):
    _object(value, SOURCE_FIELDS, "source_export")
    if type(value["export_id"]) is not str or not _EXPORT_ID.fullmatch(value["export_id"]):
        raise FeedbackValidationError("source_export.export_id: ongeldige exportidentiteit")
    if type(value["export_sha256"]) is not str or not _HASH.fullmatch(value["export_sha256"]):
        raise FeedbackValidationError("source_export.export_sha256: ongeldige SHA256")
    _text(value["release"], "source_export.release", 80)
    _timestamp(value["created_at"], "source_export.created_at")
    return deepcopy(value)


def validate_feedback(value):
    _object(value, {"schema", "schema_version", "source_export", "analyzed_at", "summary", "recommendations", "question_answers", "limitations"}, "rapport")
    if value["schema"] != FEEDBACK_SCHEMA or type(value["schema_version"]) is not int or value["schema_version"] != FEEDBACK_VERSION:
        raise FeedbackValidationError("Dit is geen ondersteund SolarPilot-adviesrapport (versie 1)")
    validate_source_export(value["source_export"])
    _timestamp(value["analyzed_at"], "analyzed_at")
    _text(value["summary"], "summary")
    _texts(value["limitations"], "limitations")
    rows = value["recommendations"]
    if type(rows) is not list or len(rows) > 100:
        raise FeedbackValidationError("recommendations: maximaal 100 adviezen")
    for index, row in enumerate(rows):
        path = f"recommendations[{index}]"
        required = {"category", "text", "evidence", "confidence", "limitations"}
        if type(row) is not dict or not required <= set(row) or set(row) - (required | {"proposal_id"}):
            raise FeedbackValidationError(f"{path}: gebruik uitsluitend de velden van het adviesformaat")
        if "proposal_id" in row and (type(row["proposal_id"]) is not str or not _PROPOSAL_ID.fullmatch(row["proposal_id"])):
            raise FeedbackValidationError(f"{path}.proposal_id: ongeldige voorstelidentiteit")
        if type(row["category"]) is not str or row["category"] not in RECOMMENDATION_CATEGORIES:
            raise FeedbackValidationError(f"{path}.category: onbekende adviescategorie")
        if type(row["confidence"]) is not str or row["confidence"] not in CONFIDENCES:
            raise FeedbackValidationError(f"{path}.confidence: kies low, medium of high")
        _text(row["text"], path + ".text")
        _texts(row["evidence"], path + ".evidence")
        _texts(row["limitations"], path + ".limitations")
    answers = value["question_answers"]
    if type(answers) is not list or len(answers) > 100:
        raise FeedbackValidationError("question_answers: maximaal 100 antwoorden")
    seen = set()
    for index, row in enumerate(answers):
        path = f"question_answers[{index}]"
        _object(row, {"question_id", "revision", "answer", "outcome"}, path)
        _question_ref({"question_id": row["question_id"], "revision": row["revision"]})
        identity = (row["question_id"], row["revision"])
        if identity in seen:
            raise FeedbackValidationError("Dubbele antwoorden op dezelfde bevinding zijn niet toegestaan")
        seen.add(identity)
        _text(row["answer"], path + ".answer")
        if type(row["outcome"]) is not str or row["outcome"] not in {"reviewed", "needs_more_data"}:
            raise FeedbackValidationError(f"{path}.outcome: kies reviewed of needs_more_data")
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeEncodeError) as err:
        raise FeedbackValidationError("Rapport bevat ongeldige JSON-waarden") from err
    if len(encoded) > MAX_FEEDBACK_BYTES:
        raise FeedbackValidationError("Adviesrapport is groter dan 1 MiB")
    return deepcopy(value)


def _question_ref(value):
    _object(value, {"question_id", "revision"}, "question_ref")
    if type(value["question_id"]) is not str or not _QUESTION_ID.fullmatch(value["question_id"]):
        raise FeedbackValidationError("Ongeldige bevindingidentiteit")
    if type(value["revision"]) is not str or not _REVISION.fullmatch(value["revision"]):
        raise FeedbackValidationError("Ongeldige bevindingversie")
    return deepcopy(value)


def _known_export(value):
    _object(value, {"source_export", "requested_hours", "question_refs"}, "known_export")
    validate_source_export(value["source_export"])
    if type(value["requested_hours"]) is not int or value["requested_hours"] not in {1, 24, 168}:
        raise FeedbackValidationError("Ongeldige exportperiode")
    if type(value["question_refs"]) is not list or len(value["question_refs"]) > 100:
        raise FeedbackValidationError("Ongeldige bevindingreferenties")
    refs = [_question_ref(row) for row in value["question_refs"]]
    if len({(row["question_id"], row["revision"]) for row in refs}) != len(refs):
        raise FeedbackValidationError("Dubbele bevindingreferenties")
    return deepcopy(value)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise FeedbackValidationError("Dubbele JSON-sleutels zijn niet toegestaan")
        value[key] = item
    return value


def _nonfinite(value):
    raise FeedbackValidationError(f"Ongeldige JSON-waarde: {value}")


def parse_feedback(content):
    """Bound the raw input before parsing; reject ambiguous and deep JSON."""
    if type(content) is not str or len(content) > MAX_FEEDBACK_BYTES:
        raise FeedbackValidationError("Upload uitsluitend een JSON-adviesbestand van maximaal 1 MiB")
    try:
        size = len(content.encode("utf-8"))
    except UnicodeEncodeError as err:
        raise FeedbackValidationError("Adviesbestand bevat ongeldige Unicode") from err
    if size > MAX_FEEDBACK_BYTES:
        raise FeedbackValidationError("Adviesrapport is groter dan 1 MiB")
    depth = 0
    quoted = escaped = False
    for char in content:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise FeedbackValidationError("Adviesbestand is te diep genest")
        elif char in "]}":
            depth -= 1
    try:
        value = json.loads(content, object_pairs_hook=_unique_object, parse_constant=_nonfinite)
    except (json.JSONDecodeError, RecursionError) as err:
        raise FeedbackValidationError("Adviesbestand bevat ongeldige JSON") from err
    return validate_feedback(value)


class AnalysisFeedbackStore:
    """Persist advice and export identities without modifying runtime settings."""

    def __init__(self, runtime):
        self.r = runtime
        self.store = Store(runtime.hass, 1, storage_key(runtime.entry.entry_id))
        self.known_exports = []
        self.report = None
        self.imported_at = None
        self.error = ""
        self.loaded = False
        self._lock = asyncio.Lock()
        self._closed = False

    async def start(self):
        try:
            data = await self.store.async_load() or {}
            if type(data) is not dict:
                raise FeedbackValidationError("Ongeldige adviesopslag")
            rows = data.get("known_exports", [])
            if type(rows) is not list:
                raise FeedbackValidationError("Ongeldige exportidentiteiten")
            self.known_exports = [_known_export(row) for row in rows[-MAX_KNOWN_EXPORTS:]]
            if data.get("report") is not None:
                self.report = validate_feedback(data["report"])
                _timestamp(data.get("imported_at"), "imported_at")
                self.imported_at = data["imported_at"]
            self.loaded = True
        except (ValueError, TypeError, OSError) as err:
            self.error = "Adviesopslag niet geladen: " + type(err).__name__
            self.report = None
            self.imported_at = None

    def _available(self):
        if self._closed or self.r._closed:
            raise FeedbackValidationError("SolarPilot is herladen; upload het advies opnieuw")

    async def _save(self, rows, report, imported_at):
        self._available()
        payload = {"schema_version": 1, "known_exports": rows, "report": report, "imported_at": imported_at}
        try:
            await self.store.async_save(deepcopy(payload))
        except Exception as err:
            self.error = "Adviesopslag niet bewaard: " + type(err).__name__
            raise
        self.known_exports, self.report, self.imported_at = deepcopy(rows), deepcopy(report), imported_at
        self.error = ""
        self.loaded = True

    async def note_export(self, provenance, *, requested_hours=168, question_refs=None):
        """Call only after the final JSON or compressed artifact was created."""
        if type(provenance) is not dict:
            raise FeedbackValidationError("Exportidentiteit ontbreekt")
        source = validate_source_export({key: provenance.get(key) for key in SOURCE_FIELDS})
        item = _known_export({"source_export": source, "requested_hours": requested_hours,
                              "question_refs": question_refs or []})
        async with self._lock:
            rows = [row for row in self.known_exports if row["source_export"]["export_id"] != source["export_id"]]
            rows.append(item)
            # Keep the current report's matching identity if later exports fill
            # the ledger, so reloads do not erase a previously shown association.
            protected = self.report.get("source_export") if self.report else None
            protected_row = next((row for row in rows[:-MAX_KNOWN_EXPORTS] if row["source_export"] == protected), None)
            if len(rows) > MAX_KNOWN_EXPORTS and protected_row:
                rows = [protected_row, *rows[-(MAX_KNOWN_EXPORTS - 1):]]
            else:
                rows = rows[-MAX_KNOWN_EXPORTS:]
            await self._save(rows, self.report, self.imported_at)

    async def import_content(self, content):
        execute = getattr(self.r.hass, "async_add_executor_job", None)
        report = await execute(parse_feedback, content) if execute else await asyncio.to_thread(parse_feedback, content)
        async with self._lock:
            known = self._matching_export(report)
            if known and report["question_answers"]:
                if known["requested_hours"] != 168:
                    raise FeedbackValidationError("Antwoorden op bevindingen vragen de bijbehorende export van 7 dagen")
                exported = {(row["question_id"], row["revision"]) for row in known["question_refs"]}
                if any((row["question_id"], row["revision"]) not in exported for row in report["question_answers"]):
                    raise FeedbackValidationError("Een antwoord verwijst niet naar een bevindingversie uit deze export")
            await self._save(self.known_exports, report, datetime.now(timezone.utc).isoformat())
        self.r.learning_hub.last_refresh = 0
        return self.status()

    async def remove(self):
        async with self._lock:
            await self._save(self.known_exports, None, None)
        self.r.learning_hub.last_refresh = 0
        return self.status()

    def _matching_export(self, report=None):
        report = self.report if report is None else report
        source = report.get("source_export") if report else None
        return next((row for row in self.known_exports if row["source_export"] == source), None)

    def question_review(self, question_id, revision):
        """Only presentation metadata; never answer a learning-policy question."""
        known = self._matching_export()
        if not known or known["requested_hours"] != 168:
            return None
        if {"question_id": question_id, "revision": revision} not in known["question_refs"]:
            return None
        current = getattr(self.r.learning_hub, "current_findings", [])
        if not any(row["id"] == question_id and row["revision"] == revision for row in current):
            return None
        return next((deepcopy(row) for row in self.report["question_answers"]
                     if row["question_id"] == question_id and row["revision"] == revision), None)

    def status(self):
        from .analysis_implementations import logic_update_status
        source = self.report.get("source_export") if self.report else None
        matching = self._matching_export()
        association = {"state": "matched" if matching else "unverified",
                       "reason": "exact_local_export" if matching else "no_matching_local_export" if source else "no_report",
                       "source_export": deepcopy(matching["source_export"]) if matching else None}
        current = {(row["id"], row["revision"]) for row in getattr(self.r.learning_hub, "current_findings", [])}
        reviews = []
        for row in self.report["question_answers"] if self.report else []:
            applied = (matching is not None and matching["requested_hours"] == 168
                       and {"question_id": row["question_id"], "revision": row["revision"]} in matching["question_refs"]
                       and (row["question_id"], row["revision"]) in current)
            reviews.append({**deepcopy(row), "status": row["outcome"] if applied else "ignored_unverified" if matching is None else "ignored_stale"})
        return {"report": deepcopy(self.report), "imported_at": self.imported_at,
                "association": association, "current_release": VERSION,
                "question_review": reviews,
                "logic_updates": logic_update_status(self.report["recommendations"] if self.report else [], release=VERSION),
                "source_release_matches_current": source["release"] == VERSION if source else None,
                "notice": "Advies wordt alleen weergegeven. Een bronkoppeling bevestigt het exportbestand, niet de juistheid van de analyse. Instellingen, code en apparaten worden niet aangepast.",
                "storage_error": self.error}

    async def close(self, *, persist=True):
        # All authorized writes were awaited immediately; never rewrite an
        # unread or malformed store on setup failure or ordinary unload.
        async with self._lock:
            self._closed = True
