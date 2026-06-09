"""Meeting timer — state machine managing turn queue, time allocation, and bell alerts."""

import random
from typing import Callable, Optional

from app.models import (
    FOOD_ICONS,
    MeetingConfig,
    MeetingParticipant,
    MeetingState,
    Participant,
)


class MeetingTimer:
    """State machine + tick logic. UI-agnostic — no tkinter imports here."""

    def __init__(
        self,
        on_tick: Callable[[], None],
        on_finished: Callable[[], None],
        on_bell: Callable[[], None] | None = None,
    ) -> None:
        self._on_tick = on_tick
        self._on_finished = on_finished
        self._on_bell = on_bell

        self.state: MeetingState = MeetingState.IDLE
        self.config: MeetingConfig = MeetingConfig()

        # Ordered participant queue (non-jefotes first, then jefotes — each group shuffled)
        self._queue: list[MeetingParticipant] = []
        self._current_index: int = -1

        # Total elapsed seconds for the whole meeting
        self.meeting_elapsed: int = 0
        # Seconds elapsed for the current participant's turn
        self._turn_elapsed: int = 0

    # ── Setup ─────────────────────────────────────────────────────────────────

    def setup(self, participants: list[Participant], config: MeetingConfig) -> None:
        """Call before start. Builds the queue and assigns allocated times."""
        total = len(participants)
        if total == 0:
            return
        allocated = (config.duration_minutes * 60) // total

        # Re-randomize food icons on every meeting start
        icons = random.sample(FOOD_ICONS, min(len(participants), len(FOOD_ICONS)))
        for i, p in enumerate(participants):
            p.food_icon = icons[i % len(icons)]

        non_jefotes = [p for p in participants if not p.is_jefote]
        jefotes = [p for p in participants if p.is_jefote]
        ordered = random.sample(non_jefotes, len(non_jefotes)) + random.sample(
            jefotes, len(jefotes)
        )

        self._queue = [
            MeetingParticipant(p, allocated_seconds=allocated) for p in ordered
        ]
        self._current_index = -1
        self.meeting_elapsed = 0
        self._turn_elapsed = 0
        self.config = config

    # ── State transitions ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Transition from IDLE to RUNNING and advance to first participant."""
        if self.state != MeetingState.IDLE:
            return
        self.state = MeetingState.RUNNING
        self._advance()

    def pause(self) -> None:
        """Toggle between RUNNING and PAUSED states."""
        if self.state == MeetingState.RUNNING:
            self.state = MeetingState.PAUSED
        elif self.state == MeetingState.PAUSED:
            self.state = MeetingState.RUNNING

    def next_participant(self) -> None:
        """Mark current as done and advance to next (or finish if no more)."""
        if self.state not in (MeetingState.RUNNING, MeetingState.PAUSED):
            return
        if self._current_index >= 0:
            self._queue[self._current_index].done = True
        if not self._has_next():
            self._finish()
            return
        self.state = MeetingState.RUNNING
        self._advance()

    def stop(self) -> None:
        """End the meeting early, marking it as FINISHED."""
        if self.state in (MeetingState.RUNNING, MeetingState.PAUSED):
            if self._current_index >= 0:
                self._queue[self._current_index].done = True
            self._finish()

    def reset(self) -> None:
        """Clear all state and return to IDLE."""
        self.state = MeetingState.IDLE
        self._queue = []
        self._current_index = -1
        self.meeting_elapsed = 0
        self._turn_elapsed = 0

    # ── Tick (called every second by the UI scheduler) ────────────────────────

    def tick(self) -> None:
        """Advance timers by 1 second (only current turn advances when not paused)."""
        if self.state not in (MeetingState.RUNNING, MeetingState.PAUSED):
            return
        # Meeting total always advances
        self.meeting_elapsed += 1
        # Participant turn only advances when not paused
        if self.state == MeetingState.RUNNING:
            self._turn_elapsed += 1
            if self._current_index >= 0:
                self._queue[self._current_index].actual_seconds = self._turn_elapsed
                current = self._queue[self._current_index]
                remaining = current.allocated_seconds - self._turn_elapsed
                if 0 <= remaining < 10 and self._on_bell:
                    self._on_bell()
        self._on_tick()

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def current(self) -> Optional[MeetingParticipant]:
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index]
        return None

    @property
    def queue(self) -> list[MeetingParticipant]:
        return self._queue

    @property
    def non_jefotes(self) -> list[MeetingParticipant]:
        return [mp for mp in self._queue if not mp.participant.is_jefote]

    @property
    def jefotes(self) -> list[MeetingParticipant]:
        return [mp for mp in self._queue if mp.participant.is_jefote]

    def has_next(self) -> bool:
        """Check if there are more participants to speak after current."""
        return self._has_next()

    @property
    def planned_seconds(self) -> int:
        return self.config.duration_minutes * 60

    # ── Internals ─────────────────────────────────────────────────────────────

    def _advance(self) -> None:
        """Move to next participant in queue and reset turn timer."""
        self._current_index += 1
        self._turn_elapsed = 0

    def _has_next(self) -> bool:
        """Return True if there are more participants after current."""
        return self._current_index + 1 < len(self._queue)

    def _finish(self) -> None:
        """Mark meeting as FINISHED and trigger callback."""
        self.state = MeetingState.FINISHED
        self._on_finished()

    def build_session_payload(self) -> list[dict]:
        """Build participant times for session saving."""
        return [
            {
                "name": mp.participant.name,
                "is_jefote": mp.participant.is_jefote,
                "allocated_time": mp.allocated_seconds,
                "actual_time": mp.actual_seconds,
            }
            for mp in self._queue
        ]
