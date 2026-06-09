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
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()


@dataclass
class Participant:
    id: int
    name: str
    is_jefote: bool
    food_icon: str = ""
    jira_account_id: str = ""
    avatar_path: str = ""


@dataclass
class MeetingParticipant:
    participant: Participant
    allocated_seconds: int = 0
    actual_seconds: int = 0
    done: bool = False


@dataclass
class MeetingConfig:
    duration_minutes: int = 15
    meeting_name: str = "Polaris Rising [Ab+B]"
    bell_enabled: bool = True
    bell_volume: int = 70


@dataclass
class SessionRecord:
    id: int
    date: str
    planned_duration: int
    actual_duration: int
    participants: list = field(default_factory=list)
