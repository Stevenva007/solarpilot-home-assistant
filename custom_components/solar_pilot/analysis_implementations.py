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


IMPLEMENTED_PROPOSALS = {'sp.hp.task-presentation.v1': {'proposal_sha256': '4c476362c5748d15799df46b23c3bb043184ad629f01ecb554b76740428fb48f',
                                'introduced_release': '1.0.0-beta.69',
                                'title': 'Taakbereik en tankroute bij native OFF'},
 'sp.hp.context-and-learning.v1': {'proposal_sha256': '2c58cbcdf31739d02d295490d40a489a13bd6b23ffcac2c6cae7dcdafaaa98aa',
                                   'introduced_release': '1.0.0-beta.69',
                                   'title': 'Native en afgeleide leercontext scheiden'},
 'sp.meters.source-quality-evidence.v1': {'proposal_sha256': 'da7fc941830028211d8449d27aa18577c847006186b1f1af794388082f191ae3',
                                          'introduced_release': '1.0.0-beta.69',
                                          'title': 'Bewijs en afkeurreden per vermogensbron'},
 'sp.electrical.budget-versus-limits.v1': {'proposal_sha256': '8f26454092497698718bd732cd1727916886e3ce0c061e97684d450e5c3d0828',
                                           'introduced_release': '1.0.0-beta.69',
                                           'title': 'Kwartierbudget en fysieke grenzen onderscheiden'},
 'sp.sg.reassessment-progress.v1': {'proposal_sha256': 'd564b03bcc3c9916629fc94e65566476fa9c0eb9dc7d6500999772e2d345f0b5',
                                    'introduced_release': '1.0.0-beta.71',
                                    'title': 'Actuele SG-bevestiging en startvertraging zichtbaar'},
 'sp.hp.history-export-window.v1': {'proposal_sha256': '05a6a9c7ce72df91e83244a2a8c63881cc3d596d3a7fc142ec30e15b4c35587c',
                                    'introduced_release': '1.0.0-beta.71',
                                    'title': 'Bewaartermijn en overlappende exportdagen scheiden'},
 'sp.sg.minimum-request-duration.v1': {'proposal_sha256': 'c4e8f9335b405eb89a6ca2df2a7b38765a88d03fd496f9adaeaff7ceecf1be9a',
                                       'introduced_release': '1.0.0-beta.72',
                                       'title': 'Minimale SG-aanvraagduur van twintig minuten'},
 'sp.sg.cloud-import-buffer.v1': {'proposal_sha256': '9a57311e0f6eb6f376f1ef4916a78aaf624af31d955b7c8437bea1334eba8ed1',
                                  'introduced_release': '1.0.0-beta.73',
                                  'title': 'SG-wolkenbuffer van 600 W en vijf minuten'},
 'sp.sg.confirmed-reset-display.v1': {'proposal_sha256': '65827961bb1b068354c5840c3b0e7a881f4025f3d32df4a9552fda3292bf3b0e',
                                      'introduced_release': '1.0.0-beta.74',
                                      'title': 'Al bevestigde SG-reset zonder herhaalde teller'},
 'sp.wallbox.session-source-diagnostics.v1': {'proposal_sha256': 'b3fd3fb152aeab63d061ff95fabc0bb9835a393c5078910944d9746130bdb455',
                                              'introduced_release': '1.0.0-beta.74',
                                              'title': 'Gekoppelde Wallbox-sessiebron gericht beoordelen'},
 'sp.hp.inactive-scope-display.v1': {'proposal_sha256': 'cae613e96f6fa7e6001486a0f95f04de98b9d6a4cc436a7d42a47b7c45877b3a',
                                     'introduced_release': '1.0.0-beta.74',
                                     'title': 'Totale warmtepomprust vraagt passend bewijs'},
 'sp.learning.local-investigation.v1': {'proposal_sha256': '04ca112f432c402dccafe8a83e5894ac029c7da67f6608b546cea1e78b68267b',
                                        'introduced_release': '1.0.0-beta.75',
                                        'title': 'Lokaal automatisch brononderzoek en voorstellen'},
 'sp.sg.session-evidence.v1': {'proposal_sha256': 'eac331e8adc3447579aec47c035634bded8f9404f9b020ce330f4103f6195f13',
                               'introduced_release': '1.0.0-beta.75',
                               'title': 'Versie, policy en meetdekking van nieuwe SG-sessies'},
 'sp.analysis.recommendation-kind.v1': {'proposal_sha256': 'e798b2a3d5818381fc424f023d0bf8151c4c1f8d0c57cbd28522e15a164df834',
                                        'introduced_release': '1.0.0-beta.75',
                                        'title': 'Instellingsadvies en waarnemingen herkenbaar'},
 'sp.sg.research-timestamp-boundary.v1': {'proposal_sha256': '496da366b67f676ba3404a9eafe0e1fc9864c16fb116c15985946958bf4ba3c7',
                                          'introduced_release': '1.0.0-beta.81',
                                          'title': 'Werkelijke SG-onderzoeksinname met coherent tijdtype'},
 'sp.sg.interrupted-research-checkpoint.v1': {'proposal_sha256': 'eb90a01dfc149815531ebf5612fdd83142aab3dc160bfbc76f16ec571e14a267',
                                              'introduced_release': '1.0.0-beta.81',
                                              'title': 'Onderbroken SG-onderzoek als begrensde historische '
                                                       'waarneming'},
 'sp.sg.stop-evidence-transport-stage.v1': {'proposal_sha256': '9b1316be18de606aa779312e19b51ab407f6a9bbceb6aaa15121727665fb6f4f',
                                            'introduced_release': '1.0.0-beta.81',
                                            'title': 'Controllerstop, contactbewijs en transportfase '
                                                     'gescheiden'},
 'sp.wallbox.template-source-proof.v1': {'proposal_sha256': '8442a8232f4e4cd909da9b2ea9d9f0caa3f67237ef8ea37e79425a8373b9511f',
                                         'introduced_release': '1.0.0-beta.81',
                                         'title': 'Oorspronkelijke Wallbox-templatebronnen inspecteerbaar'},
 'sp.hp.native-programme-timeline.v1': {'proposal_sha256': '8fa4e4b680f26474e3b1fa64dd099a3cee111cd0c2d0ec25901baff929d6797b',
                                        'introduced_release': '1.0.0-beta.81',
                                        'title': 'Native programma en tankbewijs op eigen tijdlijn'},
 'sp.pv.forecast-issue-horizon-proof.v1': {'proposal_sha256': '1f755d708becb7450d6fc49c0e2aaf5c75b46ad9501de25533d64a4288848809',
                                           'introduced_release': '1.0.0-beta.81',
                                           'title': 'Vooruit vastgelegde forecast en oorspronkelijke '
                                                    'uitgiftestatus'},
 'sp.pv.quarter-rejection-evidence.v1': {'proposal_sha256': 'e479aec895af82a53f361ab73af47bda0c63b2982725b12f2d680bc688271ec8',
                                         'introduced_release': '1.0.0-beta.81',
                                         'title': 'Geldige en afgekeurde PV-kwartieronderdelen verklaard'},
 'sp.meters.solar-balance-time-coherence.v1': {'proposal_sha256': 'fd4d39eff53ad2c2d8081692ecbf2bcb0fc72fabc43baeebfab0b5f71fe31a49',
                                               'introduced_release': '1.0.0-beta.81',
                                               'title': 'Oorspronkelijke net/PV-tijden en onvolledige '
                                                        'bronbalans'},
 'sp.hp.short-electric-activity-display.v1': {'proposal_sha256': '6df2b1c64d0eb203fff70dff898ca3c917931a376ec3899e61a52e8da8f47c0f',
                                              'introduced_release': '1.0.0-beta.81',
                                              'title': 'Korte elektrische activiteit naast ongewijzigde ruwe '
                                                       'historie'}}
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
