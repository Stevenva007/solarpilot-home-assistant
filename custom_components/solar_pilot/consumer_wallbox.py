"""Per-consumer, read-only EV priority with a bounded small-surplus fallback.

EV watts and releasable own loads are used only to decide WHEN to yield. They
never increase physical grid headroom or authorise a lower-priority start.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from .wallbox import Reading, state_set

PRIORITY_DEFAULTS = {
    "priority_min_power_w": 1380.0,  # Confirmed one-phase Full Solar minimum for this installation; remains editable.
    "priority_start_margin_w": 150.0,
    "priority_stable_s": 120,
    "priority_release_s": 300,
    "priority_hysteresis_w": 300.0,
    "priority_start_timeout_s": 600,
    "priority_retry_s": 1800,
    "connected_entity": "",
}


def follows_wallbox(config: dict, others_first: bool) -> bool:
    choice = config.get("wallbox_precedence", "global")
    return choice == "wallbox_first" or (choice == "global" and not others_first)


@dataclass(frozen=True)
class PriorityResult:
    state: str = "disabled"
    reason: str = "Geen toestellen met afzonderlijke Wallbox-voorrang"
    block_starts: bool = False
    yield_loads: bool = False
    potential_w: float | None = None
    minimum_w: float | None = None
    max_increase_w: float | None = None
    remaining_s: int = 0


class ConsumerWallboxPriority:
    """Hysteretic EV opportunity gate. No services, no network and no clocks inside."""

    def __init__(self, settings):
        self.settings = {**PRIORITY_DEFAULTS, **settings}
        self.result = PriorityResult()
        self.ready_since = None
        self.low_since = None
        self.priority_active = False
        self.wait_since = None
        self.retry_until = 0.0
        self.fallback_ids: set[str] = set()
        self.watch = None
        self.last_now = None

    def _reset(self):
        self.ready_since = self.low_since = self.wait_since = None
        self.priority_active = False
        self.retry_until = 0.0
        self.fallback_ids.clear()
        self.watch = None

    def note_action(self, now, wall_time, device_id, old_w, new_w, reading):
        if new_w > old_w + .5 and self.result.state == "charging_residual" and reading.valid:
            self.watch = (wall_time, float(reading.power_w or 0), new_w - old_w)

    def update(self, *, now, reading: Reading, grid_w, filtered_grid_w,
               discharge_w, owned_lower: dict[str, float], has_lower: bool,
               sample_gap_s=30) -> PriorityResult:
        c = self.settings
        if not c.get("enabled") or not has_lower:
            self._reset()
            self.result = PriorityResult()
            return self.result
        if self.last_now is not None and (now < self.last_now or now - self.last_now > sample_gap_s):
            self.ready_since = self.low_since = None
        self.last_now = now
        # A snapshot's lack of EV demand is not the same as a valid unplug signal.
        # Unknown/offline data blocks new lower-priority starts, without cutting
        # an already running compressor or inventing an EV demand.
        if (not reading.valid or grid_w is None or not math.isfinite(grid_w)
                or filtered_grid_w is None or not math.isfinite(filtered_grid_w)):
            self.ready_since = self.low_since = None
            self.result = PriorityResult("unknown", "Wallbox/netmeting onzeker: geen nieuwe lagere start", True)
            return self.result
        charging = (reading.power_w or 0) >= float(c.get("charging_threshold_w", 50))
        no_request_status = (reading.status or "").casefold() in state_set(c.get("idle_states", ""))
        if not charging and (reading.connected is False or reading.demand is False or no_request_status):
            self._reset()
            self.result = PriorityResult("no_request", "Geen actieve Wallbox-laadvraag: gewoon zonneoverschot gebruiken")
            return self.result
        full_solar = (reading.mode or "").casefold() in state_set(c.get("full_solar_states", "full_solar"))
        if not full_solar and not charging:
            self._reset()
            self.result = PriorityResult("not_solar", "Wallbox staat niet op Full Solar: geen zonnestartvermogen reserveren")
            return self.result

        own = sum(max(0.0, float(v)) for v in owned_lower.values())
        potential = max(0.0, -max(grid_w, filtered_grid_w) - max(0.0, discharge_w)
                        + max(0.0, reading.power_w or 0) + own)
        minimum = max(0.0, float(c["priority_min_power_w"]))
        margin = max(0.0, float(c["priority_start_margin_w"]))
        # EV precedence is not justified solely by cable presence: demand and
        # usable solar mode are required. Actual charging proves usable demand.
        if not charging and reading.demand is not True:
            self.ready_since = self.low_since = None
            self.result = PriorityResult("unknown", "Auto mogelijk aangesloten, maar laadvraag niet bevestigd", True)
            return self.result
        if minimum <= 0 and not charging:
            self.result = PriorityResult("unconfigured", "Stel eerst het minimum zonnelaadvermogen van de Wallbox in", True)
            return self.result

        self.fallback_ids.intersection_update(owned_lower)
        if charging:
            self.ready_since = self.low_since = self.wait_since = None
            self.priority_active = True
            self.retry_until = 0.0
            if self.watch and reading.stamp > self.watch[0]:
                # Conservative interaction signal, not causal proof. A cloud can
                # also produce this drop. Release only our own lower loads.
                if self.watch[1] - (reading.power_w or 0) >= max(50.0, self.watch[2] * .5):
                    self.fallback_ids.update(owned_lower)
                self.watch = None
            if self.fallback_ids:
                self.result = PriorityResult("yield", "Wallbox laadt: lagere lasten vrijgeven na hun minimumlooptijd", True, True, potential, minimum)
            else:
                self.result = PriorityResult("charging_residual", "Wallbox laadt; lagere lasten alleen op stabiel echt restoverschot", False, False, potential, minimum)
            return self.result

        if now < self.retry_until:
            self.fallback_ids.update(owned_lower)
            self.result = PriorityResult("retry_wait", "Auto startte niet: klein verbruik opnieuw toegestaan; Wallbox later opnieuw beoordelen", False, False, potential, minimum, None, math.ceil(self.retry_until-now))
            return self.result
        self.retry_until = 0.0
        if not self.priority_active:
            self.fallback_ids.update(owned_lower)
            if potential >= minimum + margin:
                if self.ready_since is None:
                    self.ready_since = now
                left = max(0, float(c["priority_stable_s"]) - (now - self.ready_since))
                if left > 0:
                    self.result = PriorityResult("threshold_delay", "Genoeg voor Wallbox: stabiliteit afwachten, geen nieuwe lagere start", True, False, potential, minimum, None, math.ceil(left))
                    return self.result
                self.priority_active = True
            else:
                self.ready_since = None
                self.result = PriorityResult("small_surplus", "Nog te weinig voor Wallbox: lagere lasten mogen het overschot gebruiken", False, False, potential, minimum)
                return self.result

        # A lower load's OFF transition must not collapse the potential pool:
        # its measured watts disappear but reappear in actual net export.
        low_threshold = max(0.0, minimum - float(c["priority_hysteresis_w"]))
        if potential < low_threshold:
            if self.low_since is None:
                self.low_since = now
            if now - self.low_since >= float(c["priority_release_s"]):
                self.priority_active = False
                self.ready_since = self.low_since = self.wait_since = None
                self.fallback_ids.update(owned_lower)
                self.result = PriorityResult("small_surplus", "Wallbox-minimum langdurig niet haalbaar: lagere lasten weer toegestaan", False, False, potential, minimum)
                return self.result
        else:
            self.low_since = None
        # Do not start an EV timeout until the lower loads have really stopped;
        # a protected 30-minute run is a valid, explicitly explained wait.
        if owned_lower:
            self.wait_since = None
            self.result = PriorityResult("yield", "Genoeg voor Wallbox: lagere lasten vrijgeven na hun minimumlooptijd", True, True, potential, minimum)
            return self.result
        if self.wait_since is None:
            self.wait_since = now
        remaining = max(0.0, float(c["priority_start_timeout_s"]) - (now-self.wait_since))
        if remaining <= 0:
            self.priority_active = False
            self.ready_since = self.low_since = self.wait_since = None
            self.retry_until = now + float(c["priority_retry_s"])
            self.result = PriorityResult("retry_wait", "Auto startte niet binnen wachttijd: overschot weer vrijgeven", False, False, potential, minimum, None, int(c["priority_retry_s"]))
        else:
            self.result = PriorityResult("wait_ev_start", "Vermogen vrijgehouden: wacht op autonome start van de Wallbox", True, False, potential, minimum, None, math.ceil(remaining))
        return self.result
