"""Data models — participants, meetings, config, and session records."""

from dataclasses import dataclass, field
from enum import Enum, auto

FOOD_ICONS = [
    "🍕",
    "🍔",
    "🌮",
    "🍣",
    "🍜",
    "🥗",
    "🌯",
    "🍩",
    "🍎",
    "🧆",
    "🥪",
    "🌽",
    "🍇",
    "🥑",
    "🍦",
]


class MeetingState(Enum):
    """Possible states of the meeting timer."""

    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()


@dataclass
class Participant:
    """A person who can attend meetings, optionally linked to a Jira account."""

    id: int
    name: str
    is_jefote: bool
    food_icon: str = ""
    jira_account_id: str = ""
    avatar_path: str = ""


@dataclass
class MeetingParticipant:
    """A participant's runtime state within an active meeting."""

    participant: Participant
    allocated_seconds: int = 0
    actual_seconds: int = 0
    done: bool = False


@dataclass
class MeetingConfig:
    """Persisted meeting configuration (duration, name, bell settings)."""

    duration_minutes: int = 15
    meeting_name: str = "Polaris Rising [Ab+B]"
    bell_enabled: bool = True
    bell_volume: int = 70


@dataclass
class SessionRecord:
    """A saved meeting session with per-participant time data."""

    id: int
    date: str
    planned_duration: int
    actual_duration: int
    participants: list = field(default_factory=list)
