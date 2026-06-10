"""Main application window — orchestrates 5 tabs and meeting lifecycle."""

from datetime import datetime

import customtkinter as ctk

from app import db
from app.bell import play_bell
from app.meeting import MeetingTimer
from app.models import MeetingConfig, MeetingState
from app.ui.dialogs import askyesno, showinfo, showwarning
from app.ui.help_tab import HelpTab
from app.ui.meeting_tab import MeetingTab
from app.ui.participants_tab import ParticipantsTab
from app.ui.scroll_fix import apply as apply_scroll
from app.ui.settings_tab import SettingsTab
from app.ui.stats_tab import StatsTab


class AppWindow(ctk.CTk):
    """Root application window — orchestrates 5 tabs and meeting lifecycle."""

    def __init__(self):
        super().__init__()
        self.title("RBI Scrum Timer")
        self.geometry("1800x700")
        self.minsize(1400, 580)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        db.init_db()

        self._config: MeetingConfig = db.get_config()
        self._attendees: list = []
        self._session_saved: bool = False
        self.title(f"RBI Scrum Timer  —  {self._config.meeting_name}")

        self._timer = MeetingTimer(
            on_tick=self._on_timer_tick,
            on_finished=self._on_meeting_finished,
            on_bell=self._on_bell,
        )

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Build 5-tab layout and initialize scroll fix."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._tabs = ctk.CTkTabview(self, anchor="nw")
        self._tabs.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self._tabs.add("🕐  Meeting")
        self._tabs.add("👥  Participants")
        self._tabs.add("📊  Stats")
        self._tabs.add("⚙️  Settings")
        self._tabs.add("❓  Help")

        self._meeting_tab = MeetingTab(
            self._tabs.tab("🕐  Meeting"),
            timer=self._timer,
            get_config_cb=lambda: self._config,
            get_attendees_cb=lambda: self._attendees,
            save_cb=self._save_session,
        )
        self._meeting_tab.pack(fill="both", expand=True)

        self._participants_tab = ParticipantsTab(
            self._tabs.tab("👥  Participants"),
            get_state_cb=lambda: self._timer.state,
            get_attendees_cb=lambda: self._attendees,
            set_attendees_cb=self._update_attendees,
            get_config_cb=lambda: self._config,
            set_config_cb=self._update_config,
        )
        self._participants_tab.pack(fill="both", expand=True)

        self._stats_tab = StatsTab(self._tabs.tab("📊  Stats"))
        self._stats_tab.pack(fill="both", expand=True)

        self._settings_tab = SettingsTab(
            self._tabs.tab("⚙️  Settings"),
            on_participants_changed=self._on_participants_changed_from_settings,
        )
        self._settings_tab.pack(fill="both", expand=True)

        self._help_tab = HelpTab(self._tabs.tab("❓  Help"))
        self._help_tab.pack(fill="both", expand=True)

        self._tabs.configure(command=self._on_tab_change)
        self._stats_tab.load_data()

        # Initial scroll binding
        for sf in self._meeting_tab.scrollable_frames():
            apply_scroll(sf)
        for sf in self._participants_tab.scrollable_frames():
            apply_scroll(sf)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _update_attendees(self, attendees: list) -> None:
        """Refresh meeting tab when attendee list changes."""
        self._attendees = attendees
        self._session_saved = False  # new meeting setup
        self._meeting_tab.refresh_state()

    def _update_config(
        self,
        duration_minutes: int,
        meeting_name: str = "",
        bell_enabled: bool = True,
        bell_volume: int = 70,
    ) -> None:
        """Update meeting config and refresh UI."""
        name = meeting_name or self._config.meeting_name
        self._config = MeetingConfig(
            duration_minutes=duration_minutes,
            meeting_name=name,
            bell_enabled=bell_enabled,
            bell_volume=bell_volume,
        )
        self.title(f"RBI Scrum Timer  —  {name}")
        self._meeting_tab.refresh_state()

    def _on_bell(self) -> None:
        """Play bell sound if enabled in config."""
        if self._config.bell_enabled:
            play_bell(self._config.bell_volume)

    def _on_timer_tick(self) -> None:
        """Refresh timer display on each tick."""
        self._meeting_tab._update_timers()

    def _on_meeting_finished(self) -> None:
        """Handle meeting completion and show notification."""
        self._meeting_tab._cancel_tick()
        self._meeting_tab.refresh_state()
        showinfo(
            self,
            "Meeting Finished",
            "The meeting has ended!\nPress 💾 Save Session to record results.",
        )

    def _on_participants_changed_from_settings(self) -> None:
        """Called when Settings tab adds/updates participants — refresh participants tab."""
        self._participants_tab.load_data()

    def _on_tab_change(self) -> None:
        """Load stats when Stats tab is activated."""
        tab = self._tabs.get()
        if tab == "📊  Stats":
            self._stats_tab.load_data()

    def _on_close(self) -> None:
        """Warn if meeting is active or finished session has not been saved."""
        if self._timer.state in (MeetingState.RUNNING, MeetingState.PAUSED):
            showwarning(
                self,
                "Meeting in progress",
                "The meeting is still in progress.\nPlease stop or finish it before closing.",
            )
            return
        if self._timer.state == MeetingState.FINISHED and not self._session_saved:
            if not askyesno(
                self,
                "Unsaved session",
                "The meeting has finished but the session has not been saved.\nClose anyway and lose the data?",
            ):
                return
        self.destroy()

    def _save_session(self) -> None:
        """Save the completed meeting to the database — only once per session."""
        if self._timer.state != MeetingState.FINISHED:
            return
        today = datetime.now().strftime("%Y-%m-%d %H:%M")
        planned = self._timer.planned_seconds
        actual = self._timer.meeting_elapsed
        payload = self._timer.build_session_payload()
        db.save_session(today, planned, actual, payload)
        self._session_saved = True
        # Disable Save button to prevent duplicate saves
        self._meeting_tab._btn_save.configure(state="disabled")
        showinfo(self, "Saved", f"Session saved for {today}.")
        self._stats_tab.load_data()
