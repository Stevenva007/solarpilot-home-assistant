"""Bounded SG priority while a read-only solar charger reacts.

This is a software import-policy exception, never measured free export or a
phase/quarter/battery override. The caller supplies freshly checked sources.
Only observe can create/rearm a window; formatting and final checks are pure.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re

_IDENTITY = re.compile(r"[0-9a-f]{64}\Z")
_RECOVERY_GAP_S = 30.0


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except (OverflowError, TypeError, ValueError):
        return None


def _identity(value):
    return value if isinstance(value, str) and _IDENTITY.fullmatch(value) else None


class SGWallboxTransfer:
    def __init__(self):
        self._identity = None
        self._armed = False
        self._episode = None
        self._deadline = None
        self._recovery = None
        self._last_now = None
        self._last_wall = None
        self._restored_remaining_cap = None
        self._recovery_stamp = None
        self._grid_stamp = None
        self._report_current = False

    def _remaining(self, now, wall):
        now, wall = _number(now), _number(wall)
        episode = self._episode
        if (episode is None or episode["expired"] or episode["invalidated"]
                or self._deadline is None or now is None or wall is None
                or wall < episode["started_at"]
                or self._last_now is not None and now < self._last_now):
            return 0.0
        return max(0.0, min(episode["expires_at"]-wall, self._deadline-now))

    def observe(self, *, now, wall, grid_w, grid_stamp, limit_w, recovery_w,
                eligible_w, duration_s, confirm_s, identity, live):
        """Advance one observed episode; return whether persisted facts changed."""
        before = self._facts()
        self._report_current = False
        now, wall = _number(now), _number(wall)
        if now is None or wall is None or now < 0 or wall <= 0:
            self._armed = False
            self._recovery = None
            if self._episode is not None:
                self._episode["invalidated"] = True
            return self._facts() != before
        if self._last_now is not None and now < self._last_now:
            self._armed = False
            self._recovery = None
            if self._episode is not None:
                self._episode["invalidated"] = True
        self._last_now = now
        self._last_wall = max(wall, self._last_wall or wall)
        current_identity = _identity(identity)
        if current_identity != self._identity:
            self._identity = current_identity
            self._armed = False
            self._recovery = None
            if self._episode is not None:
                self._episode["invalidated"] = True
        episode = self._episode
        if episode is not None:
            if self._deadline is None:
                # Restore gets the original wall remainder once. An older
                # wall clock cannot create a longer or fresh reaction window.
                if wall < episode["started_at"] or wall < self._last_wall:
                    episode["invalidated"] = True
                self._deadline = now + min(max(0.0, episode["expires_at"]-wall),
                    self._restored_remaining_cap)
            if self._remaining(now, wall) <= 0:
                episode["expired"] = True
        grid, stamp, limit, recovery, eligible, duration, confirm = (
            _number(value) for value in (grid_w, grid_stamp, limit_w, recovery_w,
                                         eligible_w, duration_s, confirm_s))
        valid = (current_identity is not None and grid is not None and stamp is not None
            and 0 < stamp <= wall+5 and limit is not None and limit >= 0
            and recovery is not None and recovery >= 0
            and eligible is not None and eligible >= 0
            and duration is not None and 1 <= duration <= 600
            and confirm is not None and 1 <= confirm <= 300 and confirm < duration)
        if not valid:
            self._armed = False
            self._recovery = None
            return self._facts() != before
        if self._grid_stamp is not None and stamp < self._grid_stamp:
            self._armed = False
            self._recovery = None
            if self._episode is not None:
                self._episode["invalidated"] = True
            return self._facts() != before
        self._grid_stamp = stamp
        self._report_current = True
        recovery = min(recovery, limit)
        if grid <= recovery:
            candidate = self._recovery
            if (candidate is None or now-candidate["last_seen"] > _RECOVERY_GAP_S
                    or stamp < candidate["last_stamp"]):
                candidate = {"since": now, "first_stamp": stamp,
                    "last_stamp": stamp, "last_seen": now, "reports": 1}
                self._recovery = candidate
            else:
                if stamp > candidate["last_stamp"]:
                    candidate["reports"] += 1
                    candidate["last_stamp"] = stamp
                candidate["last_seen"] = now
            if now-candidate["since"] >= confirm and candidate["reports"] >= 2:
                self._armed = True
                self._episode = self._deadline = None
                self._restored_remaining_cap = None
                self._recovery_stamp = candidate["last_stamp"]
            return self._facts() != before
        self._recovery = None
        if grid > limit and self._episode is None:
            if (self._armed and live is True and eligible > 0 and grid-eligible <= limit
                    and self._recovery_stamp is not None and stamp >= self._recovery_stamp):
                started_at = min(wall, stamp)
                self._episode = {"schema": 1, "identity": current_identity,
                    "started_at": started_at, "expires_at": started_at+duration,
                    "limit_w": limit, "credit_cap_w": eligible,
                    "expired": False, "invalidated": False}
                self._deadline = now+max(0.0, duration-(wall-started_at))
            # An uncovered existing overload cannot gain a new window merely
            # because an EV report or SG state subsequently becomes usable.
            self._armed = False
        return self._facts() != before

    def allowed(self, *, now, wall, grid_w, projected_w, limit_w, eligible_w,
                identity, live):
        """True only for the bounded exception, never for ordinary net room."""
        grid, projected, limit, eligible = (
            _number(value) for value in (grid_w, projected_w, limit_w, eligible_w))
        now, wall = _number(now), _number(wall)
        identity = _identity(identity)
        if (identity is None or identity != self._identity
                or not self._report_current
                or now is None or wall is None or now < 0 or wall <= 0
                or self._last_now is not None and now < self._last_now
                or any(value is None for value in (grid, projected, limit, eligible))
                or limit < 0 or eligible <= 0 or projected <= limit or projected < grid):
            return False
        episode = self._episode
        active = (episode is not None and identity == episode["identity"]
            and limit == episode["limit_w"] and self._remaining(now, wall) > 0)
        if grid > limit:
            if live is not True or not active:
                return False
        elif not self._armed and not active:
            return False
        credit = min(eligible, episode["credit_cap_w"]) if active else eligible
        return projected-credit <= limit

    def _facts(self):
        return {"schema": 1, "identity": self._identity,
            "armed": self._armed, "episode": deepcopy(self._episode)}

    def snapshot(self):
        episode = self._episode
        remaining = (self._remaining(self._last_now, self._last_wall)
            if self._deadline is not None else self._restored_remaining_cap)
        return {**self._facts(),
            "observed_at": self._last_wall if episode is not None else None,
            "remaining_cap_s": remaining if episode is not None else None,
            "grid_reported_at": self._grid_stamp if episode is not None else None}

    def restore(self, value):
        """Restore an original deadline, never saved recovery or ready evidence."""
        self.__init__()
        if not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1:
            return
        episode = value.get("episode")
        if not isinstance(episode, dict) or type(episode.get("schema")) is not int or episode["schema"] != 1:
            return
        start, end, limit, credit = (_number(episode.get(key)) for key in
            ("started_at", "expires_at", "limit_w", "credit_cap_w"))
        observed, remaining = (_number(value.get(key)) for key in ("observed_at", "remaining_cap_s"))
        grid_stamp = _number(value.get("grid_reported_at"))
        identity = _identity(episode.get("identity"))
        if (identity is None or identity != value.get("identity")
                or any(number is None for number in (start, end, limit, credit, observed, remaining, grid_stamp))
                or start <= 0 or not 1 <= end-start <= 600 or limit < 0 or credit <= 0
                or observed < start or not 0 <= remaining <= max(0.0, end-observed)
                or not 0 < grid_stamp <= observed+5
                or type(episode.get("expired")) is not bool
                or type(episode.get("invalidated")) is not bool):
            return
        self._identity = identity
        self._last_wall = observed
        self._restored_remaining_cap = remaining
        self._grid_stamp = grid_stamp
        self._episode = {"schema": 1, "identity": identity,
            "started_at": start, "expires_at": end, "limit_w": limit,
            "credit_cap_w": credit, "expired": episode["expired"],
            "invalidated": episode["invalidated"]}

    def overview(self, *, now, wall):
        remaining = self._remaining(now, wall)
        episode = self._episode
        return {"state": "active" if remaining > 0 else "exhausted" if episode is not None
                    else "ready" if self._armed else "waiting_recovery",
                "active": remaining > 0, "remaining_s": math.ceil(remaining),
                "started_at": episode["started_at"] if episode is not None else None,
                "expires_at": episode["expires_at"] if episode is not None else None}
