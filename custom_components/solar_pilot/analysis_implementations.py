"""Read-only implementation status from a trusted, public release catalog.

An imported proposal is never implementation evidence. Developers may add a
generic proposal ID here only after its change is implemented and tested in
the stated release. Only the proposal-text fingerprint and public metadata
belong in the catalog; private reports and export identities stay out.
"""
from __future__ import annotations

import hashlib
import json
import re

from .const import VERSION


IMPLEMENTED_PROPOSALS = {}
_PART = r"(?:0|[1-9][0-9]*)"
_RELEASE = re.compile(rf"({_PART})\.({_PART})\.({_PART})(?:-beta\.({_PART}))?\Z")
_PROPOSAL_ID = re.compile(r"[a-z0-9][a-z0-9._:-]{0,119}\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")


def _release_key(value):
    if type(value) is not str or len(value) > 80:
        return None
    match = _RELEASE.fullmatch(value)
    if match is None:
        return None
    core = tuple(int(match[index]) for index in (1, 2, 3))
    # Stable is newer than every beta of the same core release.
    stage = (1, 0) if match[4] is None else (0, int(match[4]))
    return (*core, *stage)


def proposal_digest(row):
    """Fingerprint proposal meaning, excluding mutable evidence/status fields."""
    if (not isinstance(row, dict) or row.get("category") != "logic_update"
            or type(row.get("proposal_id")) is not str or not _PROPOSAL_ID.fullmatch(row["proposal_id"])
            or type(row.get("text")) is not str or not row["text"].strip() or len(row["text"]) > 8000):
        raise ValueError("A logic proposal requires a valid stable ID and nonempty text")
    meaning = {key: row[key] for key in ("category", "proposal_id", "text")}
    try:
        text = json.dumps(meaning, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError as err:
        raise ValueError("A logic proposal requires valid UTF-8 text") from err


def logic_update_status(recommendations, release=VERSION):
    """Return display data only; neither imports nor applies any proposal.

    Numeric core versions and beta sequence numbers are compared separately.
    The catalog in the installed code proves continued inclusion; an unknown
    version format never creates an optimistic implementation claim.
"""
    if isinstance(recommendations, dict):
        recommendations = recommendations.get("recommendations", [])
    if not isinstance(recommendations, (list, tuple)):
        return []
    installed = _release_key(release)
    result = []
    for index, row in enumerate(recommendations):
        if not isinstance(row, dict) or row.get("category") != "logic_update":
            continue
        proposal = row.get("proposal_id") if type(row.get("proposal_id")) is str else None
        catalog = IMPLEMENTED_PROPOSALS.get(proposal)
        introduced_release = catalog.get("introduced_release") if isinstance(catalog, dict) else None
        introduced = _release_key(introduced_release)
        tracked = (type(catalog) is dict and set(catalog) == {"proposal_sha256", "introduced_release", "title"}
                   and introduced is not None and type(catalog["title"]) is str and bool(catalog["title"].strip())
                   and len(catalog["title"]) <= 200 and type(catalog["proposal_sha256"]) is str
                   and _DIGEST.fullmatch(catalog["proposal_sha256"]) is not None)
        content_matches = False
        if tracked:
            try:
                content_matches = proposal_digest(row) == catalog["proposal_sha256"]
            except ValueError:
                pass
        implemented = tracked and content_matches and installed is not None and installed >= introduced
        reason = ("no_proposal_id" if proposal is None else "not_in_catalog" if catalog is None else "invalid_catalog") if not tracked else (
            "proposal_content_changed" if not content_matches else "release_not_recognized" if installed is None else
            "trusted_catalog_match" if implemented else "release_not_reached")
        result.append({"proposal_id": proposal, "status": "implemented" if implemented else "pending" if tracked else "untracked",
                       "introduced_release": introduced_release if tracked else None,
                       "summary": row.get("text") if type(row.get("text")) is str else "",
                       "installed_release": release, "reason": reason, "recommendation_index": index})
    return result
