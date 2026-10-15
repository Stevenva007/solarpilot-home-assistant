#!/usr/bin/env python3
"""Fail closed when reviewed public Aquarea source pins no longer match GitHub.

This is a development/release gate, never an installed runtime updater. It does
not approve compatibility, merge PRs, install a dependency, or modify review pins.
--offline validates the local schema only and cannot establish freshness.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORIES = ("wpatrik14/home-assistant-aquarea", "wpatrik14/aioaquarea")
CHECKPOINT = Path(__file__).resolve().parents[1] / "docs" / "upstream_review.json"
API_ORIGIN = "https://api.github.com"
MAX_RESPONSE_BYTES = 1024 * 1024
REQUEST_TIMEOUT_S = 10
TOTAL_TIMEOUT_S = 90
MAX_TAG_DEPTH = 5
SHA = re.compile(r"[0-9a-f]{40}\Z")
REF = re.compile(r"[A-Za-z0-9_./-]{1,200}\Z")


class ReviewError(Exception):
    """Messages contain only controlled fields, never HTTP bodies or tokens."""


def require(condition, message):
    if not condition:
        raise ReviewError(message)


def valid_ref(value):
    return (isinstance(value, str) and REF.fullmatch(value) is not None
            and not value.startswith(("/", ".")) and not value.endswith(("/", "."))
            and ".." not in value and "//" not in value)


def timestamp(value, field):
    require(isinstance(value, str) and value.endswith("Z"), f"{field}: expected a UTC timestamp ending in Z")
    try:
        result = datetime.fromisoformat(value[:-1] + "+00:00")
    except (TypeError, ValueError):
        raise ReviewError(f"{field}: invalid UTC timestamp") from None
    require(result.tzinfo is not None and result.utcoffset() == timedelta(0), f"{field}: invalid UTC timestamp")
    return result


def fields(value, expected, name):
    require(isinstance(value, dict) and set(value) == set(expected), f"{name}: missing or unsupported schema fields")


def sha(value, field):
    require(isinstance(value, str) and SHA.fullmatch(value) is not None, f"{field}: expected a full lowercase commit SHA")
    return value


def validate_checkpoint(data, now=None):
    fields(data, ("schema", "reviewed_at", "assessment", "repositories"), "checkpoint")
    require(type(data["schema"]) is int and data["schema"] == 1, "checkpoint: unsupported schema version")
    reviewed = timestamp(data["reviewed_at"], "reviewed_at")
    require(reviewed <= (now or datetime.now(timezone.utc)) + timedelta(minutes=5), "reviewed_at: review cannot be in the future")
    assessment = data["assessment"]
    fields(assessment, ("status", "summary", "compatibility_claim", "evidence_document"), "assessment")
    require(assessment["status"] == "complete_no_unprocessed_changes", "assessment: upstream review remains incomplete")
    require(isinstance(assessment["summary"], str) and 20 <= len(assessment["summary"]) <= 3000,
            "assessment: a concrete source-review summary is required")
    require(assessment["compatibility_claim"] is False, "assessment: source freshness is not compatibility approval")
    require(assessment["evidence_document"] == "docs/UPSTREAM_BRONNEN.md", "assessment: expected the public source register")
    rows = data["repositories"]
    require(isinstance(rows, list) and len(rows) == len(REPOSITORIES), "checkpoint: both required upstream repositories must be reviewed")
    seen = set()
    for row in rows:
        fields(row, ("repository", "default_branch", "head_commit", "latest_release", "reviewed_base_commit", "review_result"), "repository review")
        repo = row["repository"]
        require(isinstance(repo, str) and repo in REPOSITORIES and repo not in seen,
                "checkpoint: unsupported or duplicate upstream repository")
        seen.add(repo)
        require(valid_ref(row["default_branch"]), f"{repo}: invalid reviewed default branch")
        sha(row["head_commit"], f"{repo} head_commit")
        sha(row["reviewed_base_commit"], f"{repo} reviewed_base_commit")
        require(row["review_result"] in ("no_additional_changes", "relevant_changes_processed"), f"{repo}: source changes remain unreviewed")
        if row["review_result"] == "no_additional_changes":
            require(row["reviewed_base_commit"] == row["head_commit"], f"{repo}: unchanged review must compare identical source commits")
        release = row["latest_release"]
        fields(release, ("tag", "commit", "target_commitish", "published_at", "selection"), f"{repo} latest_release")
        require(valid_ref(release["tag"]) and valid_ref(release["target_commitish"]), f"{repo}: invalid release tag or target")
        sha(release["commit"], f"{repo} release commit")
        require(timestamp(release["published_at"], f"{repo} published_at") <= reviewed, f"{repo}: release is newer than its review")
        require(release["selection"] == "github_latest_published_stable", f"{repo}: unsupported release selection")
    require(seen == set(REPOSITORIES), "checkpoint: required upstream repository missing")
    return data


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Refuse before a bearer token can be forwarded to any other endpoint.
        raise ReviewError("GitHub redirected a source request; review the public repository location before retrying")


class GitHubReader:
    def __init__(self, token=None):
        require(token is None or isinstance(token, str) and all(32 < ord(char) < 127 for char in token),
                "invalid GITHUB_TOKEN format")
        self._token = token
        self._deadline = time.monotonic() + TOTAL_TIMEOUT_S
        self._opener = build_opener(NoRedirect())

    def __call__(self, repo, suffix):
        require(repo in REPOSITORIES, "unsupported upstream repository")
        require(isinstance(suffix, str) and not suffix.startswith("/") and "?" not in suffix and "#" not in suffix,
                "unsupported GitHub source path")
        remaining = self._deadline - time.monotonic()
        require(remaining > 0, "GitHub source checks exceeded the total timeout; retry the job, do not bypass this gate")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "SolarPilot-upstream-review", "Cache-Control": "no-cache"}
        if self._token:
            headers["Authorization"] = "Bearer " + self._token
        url = f"{API_ORIGIN}/repos/{repo}" + ("/" + suffix if suffix else "")
        request = Request(url, headers=headers, method="GET")
        try:
            with self._opener.open(request, timeout=min(REQUEST_TIMEOUT_S, remaining)) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            if error.code in (403, 429):
                raise ReviewError(f"{repo}: GitHub HTTP {error.code} (permission or rate limit); retry after recovery, do not bypass the review gate") from None
            raise ReviewError(f"{repo}: GitHub source request failed (HTTP {error.code}); retry or review the upstream endpoint") from None
        except (URLError, TimeoutError, socket.timeout, OSError, HTTPException):
            # Exception reason/body can contain credentials in third-party
            # transports. Never include their repr, headers or response body.
            raise ReviewError(f"{repo}: GitHub network request failed or timed out; retry the job, do not bypass the review gate") from None
        require(len(payload) <= MAX_RESPONSE_BYTES, f"{repo}: GitHub source response exceeded the size limit")
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ReviewError(f"{repo}: GitHub returned invalid source JSON") from None
        require(isinstance(data, dict), f"{repo}: GitHub source response must be an object")
        return data


def release_commit(repo, tag, fetch):
    ref = fetch(repo, "git/ref/tags/" + quote(tag, safe=""))
    require(ref.get("ref") == "refs/tags/" + tag, f"{repo}: release tag identity mismatch")
    obj = ref.get("object")
    seen = set()
    for _ in range(MAX_TAG_DEPTH + 1):
        require(isinstance(obj, dict), f"{repo}: missing release tag target")
        ident = sha(obj.get("sha"), f"{repo} release tag target")
        if obj.get("type") == "commit":
            return ident
        require(obj.get("type") == "tag" and ident not in seen and len(seen) < MAX_TAG_DEPTH,
                f"{repo}: unsupported, cyclic or excessive annotated release tag chain")
        seen.add(ident)
        tag_object = fetch(repo, "git/tags/" + ident)
        require(tag_object.get("sha") == ident, f"{repo}: annotated tag identity mismatch")
        obj = tag_object.get("object")
    raise ReviewError(f"{repo}: excessive annotated release tag chain")


def current_state(repo, fetch):
    meta = fetch(repo, "")
    require(meta.get("full_name") == repo and meta.get("private") is False, f"{repo}: public repository identity mismatch")
    branch = meta.get("default_branch")
    require(valid_ref(branch), f"{repo}: GitHub default branch is missing or invalid")
    head = fetch(repo, "branches/" + quote(branch, safe=""))
    require(head.get("name") == branch and isinstance(head.get("commit"), dict), f"{repo}: default branch response mismatch")
    commit = sha(head["commit"].get("sha"), f"{repo} default branch HEAD")
    release = fetch(repo, "releases/latest")
    require(release.get("draft") is False and release.get("prerelease") is False,
            f"{repo}: latest release is not a published stable release")
    tag = release.get("tag_name"); target = release.get("target_commitish")
    require(valid_ref(tag) and valid_ref(target), f"{repo}: GitHub release identity is missing or invalid")
    timestamp(release.get("published_at"), f"{repo} latest release published_at")
    return {"repository": repo, "default_branch": branch, "head_commit": commit,
            "latest_release": {"tag": tag, "commit": release_commit(repo, tag, fetch),
                               "target_commitish": target, "published_at": release["published_at"],
                               "selection": "github_latest_published_stable"}}


def check_online(checkpoint, fetch):
    for reviewed in checkpoint["repositories"]:
        repo = reviewed["repository"]
        current = current_state(repo, fetch)
        changed = [key for key in ("default_branch", "head_commit", "latest_release") if current[key] != reviewed[key]]
        require(not changed, f"{repo}: unreviewed upstream change in {', '.join(changed)}; inspect the public source diff, process relevant changes and tests, then update docs/upstream_review.json")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--offline", action="store_true", help="validate local review schema only; freshness remains unchecked")
    args = parser.parse_args(argv)
    try:
        try:
            checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise ReviewError("cannot read a valid upstream review checkpoint") from None
        validate_checkpoint(checkpoint)
        if args.offline:
            print("Upstream review schema OK; freshness_not_checked (--offline). This is not a release freshness gate.")
        else:
            check_online(checkpoint, GitHubReader(os.environ.get("GITHUB_TOKEN") or None))
            print("Upstream review OK: both current default-branch HEADs and latest published stable release tags/commits match reviewed pins. Source freshness only; no compatibility or installation approval.")
    except ReviewError as error:
        print(f"Upstream review FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
