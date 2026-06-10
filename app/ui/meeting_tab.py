"""Meeting tab — 4-column layout: timer/controls, attendees, open Jira tasks, closed Jira tasks."""

import os
import subprocess
from datetime import date

import customtkinter as ctk
from PIL import Image, ImageDraw

from app.jira_client import (
    fetch_closed_issues_for_participant,
    fetch_issues_for_participant,
    fetch_sprint_info,
)
from app.models import MeetingParticipant, MeetingState
from app.ui.scroll_fix import apply as apply_scroll


def _make_avatar(path: str, size: int = 32) -> ctk.CTkImage | None:
    """Create a circular avatar from an image file."""
    try:
        img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None


def _fmt(seconds: int) -> str:
    """Format seconds as MM:SS."""
    m, s = divmod(abs(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _lerp_color(c1: tuple, c2: tuple, t: float) -> str:
    """Interpolate between two RGB tuples and return a hex color string."""
    r = int(c1[0] + (c2[0] - c1[0]) * t)
    g = int(c1[1] + (c2[1] - c1[1]) * t)
    b = int(c1[2] + (c2[2] - c1[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _status_color(ratio: float) -> str:
    """Green → yellow (0→0.6), yellow → red (0.6→1.0+)."""
    GREEN = (39, 174, 96)
    YELLOW = (241, 196, 15)
    RED = (231, 76, 60)
    if ratio <= 0:
        return _lerp_color(GREEN, GREEN, 0)
    if ratio <= 0.6:
        return _lerp_color(GREEN, YELLOW, ratio / 0.6)
    return _lerp_color(YELLOW, RED, min((ratio - 0.6) / 0.4, 1.0))


class MeetingTab(ctk.CTkFrame):
    """Main meeting timer UI with 4-column layout:
    Col 0 (w=2): Timer + Current Speaker + Controls
    Col 1 (w=2): Attendees + Managers
    Col 2 (w=3): Jira Open Tasks
    Col 3 (w=3): Jira Closed Tasks
    """

    def __init__(self, parent, timer, get_config_cb, get_attendees_cb, save_cb):
        super().__init__(parent, fg_color="transparent")
        self._timer = timer
        self._get_config = get_config_cb
        self._get_attendees = get_attendees_cb
        self._save_cb = save_cb
        self._tick_job = None
        self._blink_job = None
        self._blink_on = True
        self._jira_fetch_results = {}
        self._jira_font_size: int = 18  # normal; A- = 12, A+ = 24
        self._speaker_avatar_cache: dict[str, ctk.CTkImage] = {}  # path -> CTkImage
        self._speaker_current_path: str = ""
        # Blank 1×1 transparent image used to clear the speaker label image
        _blank_pil = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        self._blank_img = ctk.CTkImage(
            light_image=_blank_pil, dark_image=_blank_pil, size=(1, 1)
        )

        self._build_ui()
        self.refresh_state()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Build the 4-column layout."""
        # Configure grid: 4 columns with weights, 1 row
        self.columnconfigure(0, weight=3)  # timer + controls (fixed feel)
        self.columnconfigure(1, weight=3)  # attendees (+10%)
        self.columnconfigure(2, weight=7)  # jira open  (doubled vs attendees)
        self.columnconfigure(3, weight=7)  # jira closed (doubled)
        self.rowconfigure(0, weight=1)

        # ── Col 0: Timer + Speaker + Controls ────────────────────────────────
        self._build_col0()

        # ── Col 1: Attendees + Managers ──────────────────────────────────────
        self._build_col1()

        # ── Col 2: Jira Open ─────────────────────────────────────────────────
        self._build_col2()

        # ── Col 3: Jira Closed ───────────────────────────────────────────────
        self._build_col3()

    def _build_col0(self) -> None:
        """Column 0: Timer, current speaker, and control buttons."""
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=(10, 4), pady=10, sticky="nsew")
        left.columnconfigure(0, weight=1)

        # Meeting header with time + date
        meeting_header = ctk.CTkFrame(left, fg_color="transparent")
        meeting_header.pack(pady=(14, 0), anchor="w", padx=12)
        ctk.CTkLabel(meeting_header, text="Meeting Time", font=("", 13, "bold")).pack(
            side="left", padx=(0, 6)
        )
        self._lbl_config_time = ctk.CTkLabel(
            meeting_header, text="[--:--]", font=("", 13, "bold"), text_color="gray"
        )
        self._lbl_config_time.pack(side="left", padx=(0, 12))
        ctk.CTkLabel(meeting_header, text="Date:", font=("", 13, "bold")).pack(
            side="left", padx=(0, 6)
        )
        ctk.CTkLabel(
            meeting_header,
            text=f"[{date.today().strftime('%d %b %Y')}]",
            font=("", 13, "bold"),
            text_color="gray",
        ).pack(side="left")

        # Total elapsed time (big font)
        self._lbl_total = ctk.CTkLabel(left, text="00:00", font=("", 38, "bold"))
        self._lbl_total.pack(pady=(6, 0))

        # Current Speaker label
        ctk.CTkLabel(left, text="Current Speaker", font=("", 13, "bold")).pack(
            anchor="w", padx=12, pady=(12, 0)
        )

        # Speaker block (fixed height, contains speaker label + time + progress)
        speaker_block = ctk.CTkFrame(left, fg_color="transparent", height=120)
        speaker_block.pack(fill="x", pady=(2, 0))
        speaker_block.pack_propagate(False)

        # Single label for speaker with compound="top" for avatar above name
        self._lbl_speaker = ctk.CTkLabel(
            speaker_block,
            text="—",
            font=("", 20, "bold"),
            wraplength=220,
            justify="center",
            compound="top",
        )
        self._lbl_speaker.pack(pady=(6, 0))

        # Speaker time row: dot + time/allocated
        speaker_time_row = ctk.CTkFrame(speaker_block, fg_color="transparent")
        speaker_time_row.pack(pady=(4, 0))
        self._dot = ctk.CTkLabel(
            speaker_time_row, text="●", font=("", 20), text_color="#27ae60"
        )
        self._dot.pack(side="left", padx=(0, 6))
        self._lbl_speaker_time = ctk.CTkLabel(
            speaker_time_row, text="00:00 / 00:00", font=("", 18, "bold")
        )
        self._lbl_speaker_time.pack(side="left")

        # Progress bar
        self._progress = ctk.CTkProgressBar(left, width=200)
        self._progress.set(0)
        self._progress.pack(pady=(8, 0))

        # Spacer
        ctk.CTkFrame(left, fg_color="transparent", height=20).pack()

        # Control buttons: Start/Pause/Next/Stop/Reset
        btn_frame = ctk.CTkFrame(left, fg_color="transparent")
        btn_frame.pack(pady=(0, 4))
        btn_frame.columnconfigure((0, 1), weight=1)

        self._btn_start = ctk.CTkButton(
            btn_frame, text="▶  Start", width=120, command=self._on_start
        )
        self._btn_start.grid(row=0, column=0, columnspan=2, padx=4, pady=4)

        self._btn_pause = ctk.CTkButton(
            btn_frame, text="⏸  Pause", width=120, command=self._on_pause
        )
        self._btn_pause.grid(row=1, column=0, padx=4, pady=4)

        self._btn_next = ctk.CTkButton(
            btn_frame, text="⏭  Next", width=120, command=self._on_next
        )
        self._btn_next.grid(row=1, column=1, padx=4, pady=4)

        self._btn_stop = ctk.CTkButton(
            btn_frame,
            text="⏹  Stop",
            width=120,
            fg_color="#c0392b",
            hover_color="#922b21",
            command=self._on_stop,
        )
        self._btn_stop.grid(row=2, column=0, padx=4, pady=4)

        self._btn_reset = ctk.CTkButton(
            btn_frame,
            text="↺  Reset",
            width=120,
            fg_color="#555",
            hover_color="#333",
            command=self._on_reset,
        )
        self._btn_reset.grid(row=2, column=1, padx=4, pady=4)

        # Save button
        self._btn_save = ctk.CTkButton(
            left,
            text="💾  Save Session",
            width=250,
            fg_color="#1a7a4a",
            hover_color="#145c36",
            command=self._on_save,
        )
        self._btn_save.pack(pady=(4, 6))

        # Sprint Info button
        self._btn_sprint_info = ctk.CTkButton(
            left,
            text="🏃  Sprint Info",
            width=250,
            fg_color="#1a4a7a",
            hover_color="#143660",
            command=self._show_sprint_info,
        )
        self._btn_sprint_info.pack(pady=(0, 16))

    def _build_col1(self) -> None:
        """Column 1: Attendees (expandable) + Managers (fixed height)."""
        mid = ctk.CTkFrame(self)
        mid.grid(row=0, column=1, padx=4, pady=10, sticky="nsew")
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(1, weight=1)  # Attendees expand
        mid.rowconfigure(3, weight=0)  # Managers fixed height

        # Attendees section
        ctk.CTkLabel(mid, text="Attendees", font=("", 13, "bold")).grid(
            row=0, column=0, padx=10, pady=(12, 4), sticky="w"
        )
        self._list_attendees = ctk.CTkScrollableFrame(mid)
        self._list_attendees.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        self._list_attendees.columnconfigure(0, weight=1)

        # Managers section
        ctk.CTkLabel(mid, text="Managers & +", font=("", 13, "bold")).grid(
            row=2, column=0, padx=10, pady=(4, 4), sticky="w"
        )
        self._list_jefotes = ctk.CTkScrollableFrame(mid, height=120)
        self._list_jefotes.grid(row=3, column=0, padx=8, pady=(0, 12), sticky="ew")
        self._list_jefotes.columnconfigure(0, weight=1)

    def _set_jira_font(self, size: int) -> None:
        """Change Jira summary font size and re-render current tasks."""
        self._jira_font_size = size
        # Update button highlight
        for s, btn in self._font_btns.items():
            btn.configure(fg_color="#1f6aa5" if s == size else "transparent")
        # Re-render if there are results cached
        if "open" in self._jira_fetch_results or "closed" in self._jira_fetch_results:
            self._render_jira_issues(
                self._jira_fetch_results.get("open", []),
                self._jira_fetch_results.get("closed", []),
            )

    def _build_col2(self) -> None:
        """Column 2: Jira Active Tasks — title + sprint info button in header."""
        jira_open = ctk.CTkFrame(self)
        jira_open.grid(row=0, column=2, padx=4, pady=10, sticky="nsew")
        jira_open.columnconfigure(0, weight=1)
        jira_open.rowconfigure(1, weight=1)

        self._jira_header = ctk.CTkLabel(
            jira_open, text="⚡  Active", font=("", 13, "bold")
        )
        self._jira_header.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        # font_btns dict initialised here so col3 can populate it
        self._font_btns = {}

        self._list_jira = ctk.CTkScrollableFrame(jira_open)
        self._list_jira.grid(row=1, column=0, padx=8, pady=(0, 12), sticky="nsew")
        self._list_jira.columnconfigure(0, weight=1)
        apply_scroll(self._list_jira)

    def _build_col3(self) -> None:
        """Column 3: Jira Closed Tasks with Font size controls in header."""
        jira_closed = ctk.CTkFrame(self)
        jira_closed.grid(row=0, column=3, padx=(4, 10), pady=10, sticky="nsew")
        jira_closed.columnconfigure(0, weight=1)
        jira_closed.rowconfigure(1, weight=1)

        # Header row: title + "Font size" label + A−/A/A+ buttons
        header_row3 = ctk.CTkFrame(jira_closed, fg_color="transparent")
        header_row3.grid(row=0, column=0, padx=8, pady=(12, 4), sticky="ew")
        header_row3.columnconfigure(0, weight=1)

        self._jira_closed_header = ctk.CTkLabel(
            header_row3, text="✅  Done", font=("", 13, "bold")
        )
        self._jira_closed_header.grid(row=0, column=0, sticky="w")

        sizer3 = ctk.CTkFrame(header_row3, fg_color="transparent")
        sizer3.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(sizer3, text="Font size", font=("", 11, "bold"), text_color="gray").pack(side="left", padx=(0, 4))
        for label, size in [("A−", 12), ("A", 18), ("A+", 24)]:
            btn = ctk.CTkButton(
                sizer3, text=label, width=32, height=24, font=("", 10),
                fg_color="#1f6aa5" if size == 18 else "transparent",
                hover_color=("gray75", "gray35"),
                command=lambda s=size: self._set_jira_font(s),
            )
            btn.pack(side="left", padx=2)
            self._font_btns[size] = btn  # same dict, same buttons

        self._list_jira_closed = ctk.CTkScrollableFrame(jira_closed)
        self._list_jira_closed.grid(
            row=1, column=0, padx=8, pady=(0, 12), sticky="nsew"
        )
        self._list_jira_closed.columnconfigure(0, weight=1)
        apply_scroll(self._list_jira_closed)

    # ── Scrollable Frames ─────────────────────────────────────────────────────

    def scrollable_frames(self):
        """Return all scrollable frames for scroll fix."""
        return [
            self._list_attendees,
            self._list_jefotes,
            self._list_jira,
            self._list_jira_closed,
        ]

    def _scroll_to_current(self) -> None:
        """Auto-scroll to current speaker in the participant list."""
        current = self._timer.current
        if current is None:
            return
        is_jefote = current.participant.is_jefote
        sf = self._list_jefotes if is_jefote else self._list_attendees
        queue = self._timer.jefotes if is_jefote else self._timer.non_jefotes

        try:
            idx = queue.index(current)
        except ValueError:
            return
        total = len(queue)
        if total == 0:
            return
        fraction = idx / total
        sf._parent_canvas.yview_moveto(max(0.0, fraction - 0.2))

    # ── Button Callbacks ──────────────────────────────────────────────────────

    def _on_start(self) -> None:
        """Start the meeting."""
        config = self._get_config()
        attendees = self._get_attendees()
        if not attendees:
            return
        non_jefotes = [p for p in attendees if not p.is_jefote]
        if not non_jefotes:
            return
        self._timer.setup(attendees, config)
        self._timer.start()
        self._schedule_tick()
        self.refresh_state()
        self._load_jira_for_current()

    def _on_pause(self) -> None:
        """Pause or resume the meeting."""
        self._timer.pause()
        if self._timer.state == MeetingState.PAUSED:
            self._stop_blink()
        self.refresh_state()

    def _on_next(self) -> None:
        """Move to next participant."""
        self._stop_blink()
        self._cancel_tick()
        self._timer.next_participant()
        if self._timer.state == MeetingState.RUNNING:
            self._schedule_tick()
        self.refresh_state()
        self.after(50, self._scroll_to_current)
        self._load_jira_for_current()

    def _on_stop(self) -> None:
        """Stop the meeting."""
        self._stop_blink()
        self._timer.stop()
        self._cancel_tick()
        self.refresh_state()

    def _on_reset(self) -> None:
        """Reset the meeting and clear Jira panels."""
        self._stop_blink()
        self._cancel_tick()
        self._timer.reset()
        self.refresh_state()
        self._load_jira_for_current()

    def _on_save(self) -> None:
        """Save the session."""
        self._save_cb()

    # ── Tick & Animation ──────────────────────────────────────────────────────

    def _schedule_tick(self) -> None:
        """Schedule the next tick (1 second later)."""
        self._tick_job = self.after(1000, self._do_tick)

    def _do_tick(self) -> None:
        """Perform one tick: update timer, refresh UI, reschedule."""
        self._timer.tick()
        self._update_timers()
        if self._timer.state in (MeetingState.RUNNING, MeetingState.PAUSED):
            self._schedule_tick()

    def _cancel_tick(self) -> None:
        """Cancel pending tick."""
        if self._tick_job:
            self.after_cancel(self._tick_job)
            self._tick_job = None

    def _start_blink(self) -> None:
        """Start blinking the status dot."""
        if self._blink_job is None:
            self._do_blink()

    def _do_blink(self) -> None:
        """Toggle blink state every 400ms."""
        self._blink_on = not self._blink_on
        self._dot.configure(text_color="#e74c3c" if self._blink_on else "#2d2d2d")
        self._blink_job = self.after(400, self._do_blink)

    def _stop_blink(self) -> None:
        """Stop blinking and reset dot to normal."""
        if self._blink_job:
            self.after_cancel(self._blink_job)
            self._blink_job = None

    # ── UI Refresh ────────────────────────────────────────────────────────────

    def refresh_state(self) -> None:
        """Full UI refresh: timers, buttons, participant lists."""
        state = self._timer.state
        config = self._get_config()

        self._lbl_config_time.configure(text=f"[{config.duration_minutes:02d}:00]")
        self._update_timers()
        self._update_buttons(state)
        self._update_participant_lists()

    def _update_timers(self) -> None:
        """Update timer displays and speaker info."""
        self._lbl_total.configure(text=_fmt(self._timer.meeting_elapsed))

        current = self._timer.current
        if current:
            p = current.participant
            if p.avatar_path:
                # Cache avatar per path to avoid recreating CTkImage on every tick
                if p.avatar_path not in self._speaker_avatar_cache:
                    img = _make_avatar(p.avatar_path, 48)
                    if img:
                        self._speaker_avatar_cache[p.avatar_path] = img
                img = self._speaker_avatar_cache.get(p.avatar_path)
                if img:
                    if self._speaker_current_path != p.avatar_path:
                        self._speaker_current_path = p.avatar_path
                        self._lbl_speaker.configure(
                            image=img, text=p.name, compound="top"
                        )
                else:
                    if self._speaker_current_path != p.name:
                        self._speaker_current_path = p.name
                        icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
                        self._lbl_speaker.configure(
                            image=self._blank_img,
                            compound="center",
                            text=f"{icon}  {p.name}",
                        )
            else:
                if self._speaker_current_path != p.name:
                    self._speaker_current_path = p.name
                    icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
                    self._lbl_speaker.configure(
                        image=self._blank_img,
                        compound="center",
                        text=f"{icon}  {p.name}",
                    )

            # Update speaker time
            self._lbl_speaker_time.configure(
                text=f"{_fmt(current.actual_seconds)} / {_fmt(current.allocated_seconds)}"
            )

            # Update progress bar
            ratio = (
                current.actual_seconds / current.allocated_seconds
                if current.allocated_seconds
                else 0
            )
            self._progress.set(min(ratio, 1.0))
            color = "#e74c3c" if ratio >= 1.0 else "#1f6aa5"
            self._progress.configure(progress_color=color)

            # Update status dot
            self._update_dot(current)
        else:
            if self._speaker_current_path != "":
                self._speaker_current_path = ""
                self._lbl_speaker.configure(
                    image=self._blank_img, compound="center", text="—"
                )
            self._lbl_speaker_time.configure(text="00:00 / 00:00")
            self._progress.set(0)
            self._stop_blink()
            self._dot.configure(text_color="#27ae60")

    def _update_dot(self, current) -> None:
        """Update status dot color based on time remaining."""
        remaining = current.allocated_seconds - current.actual_seconds
        ratio = (
            current.actual_seconds / current.allocated_seconds
            if current.allocated_seconds
            else 0
        )
        if (
            0 <= remaining <= 10  # chained comparison
            and self._timer.state == MeetingState.RUNNING
        ):
            self._start_blink()
        else:
            self._stop_blink()
            self._dot.configure(text_color=_status_color(ratio))

    def _update_buttons(self, state: MeetingState) -> None:
        """Enable/disable buttons based on meeting state."""
        attendees = self._get_attendees()
        non_jefotes = [p for p in attendees if not p.is_jefote]
        can_start = state == MeetingState.IDLE and len(non_jefotes) >= 1

        self._set_btn(self._btn_start, can_start)
        self._set_btn(
            self._btn_pause, state in (MeetingState.RUNNING, MeetingState.PAUSED)
        )
        self._btn_pause.configure(
            text="▶  Resume" if state == MeetingState.PAUSED else "⏸  Pause"
        )
        self._set_btn(
            self._btn_next,
            state in (MeetingState.RUNNING, MeetingState.PAUSED)
            and self._timer.has_next(),
        )
        self._set_btn(
            self._btn_stop, state in (MeetingState.RUNNING, MeetingState.PAUSED)
        )
        self._set_btn(
            self._btn_reset, state in (MeetingState.IDLE, MeetingState.FINISHED)
        )
        self._set_btn(self._btn_save, state == MeetingState.FINISHED)

    def _set_btn(self, btn: ctk.CTkButton, enabled: bool) -> None:
        """Enable or disable a button."""
        btn.configure(state="normal" if enabled else "disabled")

    def _update_participant_lists(self) -> None:
        """Render participant lists based on meeting state."""
        for widget in self._list_attendees.winfo_children():
            widget.destroy()
        for widget in self._list_jefotes.winfo_children():
            widget.destroy()

        state = self._timer.state

        if state == MeetingState.IDLE:
            # IDLE: show participants with avatars if available
            for p in self._get_attendees():
                target = self._list_jefotes if p.is_jefote else self._list_attendees
                row = ctk.CTkFrame(target, fg_color="transparent")
                row.pack(fill="x", padx=4, pady=2)

                if p.avatar_path:
                    img = _make_avatar(p.avatar_path, 28)
                    if img:
                        av = ctk.CTkLabel(row, text="", image=img, width=32)
                        av._image = img
                        av.pack(side="left", padx=(4, 2), pady=2)
                        ctk.CTkLabel(row, text=p.name, anchor="w").pack(
                            side="left", padx=2
                        )
                        continue

                icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
                ctk.CTkLabel(row, text=f"{icon}  {p.name}", anchor="w").pack(
                    side="left", padx=4
                )
        else:
            # RUNNING/FINISHED: show queue with status indicators
            for mp in self._timer.non_jefotes:
                self._render_mp_row(self._list_attendees, mp)
            for mp in self._timer.jefotes:
                self._render_mp_row(self._list_jefotes, mp)

        apply_scroll(self._list_attendees)
        apply_scroll(self._list_jefotes)

    def _render_mp_row(self, container, mp: MeetingParticipant) -> None:
        """Render a single participant row with status, avatar, and time."""
        is_current = self._timer.current == mp
        if mp.done:
            fg = "#2d5a27" if not mp.participant.is_jefote else "#5a4a27"
        elif is_current:
            fg = "#1a3a5a"
        else:
            fg = "transparent"

        row = ctk.CTkFrame(container, fg_color=fg, corner_radius=6)
        row.pack(fill="x", padx=4, pady=2)
        row.columnconfigure(1, weight=1)
        row.columnconfigure(2, weight=0)

        # Click on any row to load that participant's Jira tasks
        def _on_row_click(event, _mp=mp):
            """Load Jira tasks for the clicked participant."""
            self._load_jira_for_participant(_mp.participant)

        row.bind("<Button-1>", _on_row_click)

        p = mp.participant
        indicator = "▶ " if is_current else ("✓ " if mp.done else "  ")
        txt_color = "gray" if mp.done else ("white" if is_current else None)
        font = ("", 13, "bold") if is_current else ("", 12)

        # Avatar or icon column
        if p.avatar_path:
            img = _make_avatar(p.avatar_path, 28)
        else:
            img = None

        if img:
            av_lbl = ctk.CTkLabel(
                row,
                text=indicator.strip(),
                image=img,
                compound="left",
                font=font,
                text_color=txt_color or "white",
                anchor="w",
            )
            av_lbl._image = img  # keep reference
            av_lbl.grid(row=0, column=0, padx=(8, 4), pady=4, sticky="w")
            ctk.CTkLabel(
                row, text=f"  {p.name}", anchor="w", font=font, text_color=txt_color
            ).grid(row=0, column=1, padx=(0, 4), pady=4, sticky="w")
        else:
            icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
            ctk.CTkLabel(
                row,
                text=f"{indicator}{icon}  {p.name}",
                anchor="w",
                font=font,
                text_color=txt_color,
            ).grid(row=0, column=0, columnspan=2, padx=(8, 4), pady=4, sticky="w")

        # Time column
        ctk.CTkLabel(
            row,
            text=f"{_fmt(mp.actual_seconds)} / {_fmt(mp.allocated_seconds)}",
            anchor="e",
            font=("", 11),
            text_color="gray" if mp.done else None,
        ).grid(row=0, column=2, padx=(4, 8), pady=4, sticky="e")

        # Propagate click to all child widgets
        for child in row.winfo_children():
            child.bind("<Button-1>", _on_row_click)

    # ── Jira Panel ────────────────────────────────────────────────────────────

    def _load_jira_for_participant(self, participant) -> None:
        """Load Jira tasks for a specific participant (e.g. when clicked in the list)."""
        name = participant.name
        account_id = participant.jira_account_id
        is_jefote = participant.is_jefote
        board_url = os.environ.get("JIRA_BOARD_URL", "")

        self._jira_header.configure(text=f"⚡  {name} — Active")
        self._jira_closed_header.configure(text=f"✅  {name} — Done")
        self._clear_jira_list()

        loading = ctk.CTkLabel(self._list_jira, text="⏳ Loading…", font=("", 11), text_color="gray")
        loading.pack(padx=8, pady=8, anchor="w")

        self._jira_fetch_results = {}

        def _on_open(issues):
            """Handle open issues response."""
            self._jira_fetch_results["open"] = issues
            if "closed" in self._jira_fetch_results:
                self.after(0, lambda: self._render_jira_issues(
                    self._jira_fetch_results["open"],
                    self._jira_fetch_results["closed"],
                ))

        def _on_closed(issues):
            """Handle closed issues response."""
            self._jira_fetch_results["closed"] = issues
            if "open" in self._jira_fetch_results:
                self.after(0, lambda: self._render_jira_issues(
                    self._jira_fetch_results["open"],
                    self._jira_fetch_results["closed"],
                ))

        fetch_issues_for_participant(
            account_id, board_url=board_url,
            on_done=_on_open,
            on_error=lambda err: self.after(0, lambda: self._jira_error(err)),
            is_jefote=is_jefote,
        )
        fetch_closed_issues_for_participant(
            account_id, board_url=board_url,
            on_done=_on_closed,
            on_error=lambda err: self._jira_fetch_results.setdefault("closed", []),
            is_jefote=is_jefote,
        )

    def _show_sprint_info(self) -> None:
        """Fetch and display active sprint info for the configured board."""
        board_url = os.environ.get("JIRA_BOARD_URL", "")
        if not board_url:
            from app.ui.dialogs import showwarning
            showwarning(self, "No board configured",
                        "Set a Board Filter URL in Settings first.")
            return

        self._btn_sprint_info.configure(state="disabled", text="⏳")

        def _on_done(sprints):
            self.after(0, lambda: self._render_sprint_info(sprints))

        def _on_error(err):
            self.after(0, lambda: (
                self._btn_sprint_info.configure(state="normal", text="ℹ️"),
                __import__("app.ui.dialogs", fromlist=["showerror"]).showerror(
                    self, "Sprint info error", err[:120]
                )
            ))

        fetch_sprint_info(board_url, on_done=_on_done, on_error=_on_error)

    def _render_sprint_info(self, sprints: list[dict]) -> None:
        """Show sprint info as a transient popup (stays above main window)."""
        self._btn_sprint_info.configure(state="normal", text="ℹ️")
        if not sprints:
            from app.ui.dialogs import showinfo
            showinfo(self, "Sprint info", "No active RBI sprint found for this board.")
            return

        root = self.winfo_toplevel()
        popup = ctk.CTkToplevel(root)
        popup.title("🏃  Current Sprint")
        popup.resizable(False, False)
        popup.transient(root)
        popup.lift()
        popup.focus_force()
        popup.update_idletasks()
        pw, ph = 580, 300 + len(sprints) * 10
        px = root.winfo_rootx() + root.winfo_width() // 2 - pw // 2
        py = root.winfo_rooty() + root.winfo_height() // 2 - ph // 2
        popup.geometry(f"{pw}x{ph}+{px}+{py}")

        ctk.CTkLabel(popup, text="🏃  Current Sprint",
                     font=("", 18, "bold")).pack(pady=(20, 6), padx=24, anchor="w")

        for sprint in sprints:
            box = ctk.CTkFrame(popup, fg_color=("gray88", "gray20"), corner_radius=10)
            box.pack(fill="x", padx=16, pady=6)

            name_row = ctk.CTkFrame(box, fg_color="transparent")
            name_row.pack(fill="x", padx=12, pady=(12, 4))
            ctk.CTkLabel(name_row, text=sprint["name"], font=("", 15, "bold"),
                         anchor="w").pack(side="left")
            ctk.CTkLabel(name_row, text=f"⏳ {sprint['daysLeft']} left",
                         font=("", 12), text_color="#e67e22").pack(side="right")

            ctk.CTkLabel(box, text=f"📅  {sprint['startDate']}  →  {sprint['endDate']}",
                         font=("", 12), text_color="gray", anchor="w").pack(
                anchor="w", padx=12, pady=2)

            if sprint["goal"] and sprint["goal"] != "—":
                ctk.CTkLabel(box, text=f"🎯  {sprint['goal'][:90]}",
                             font=("", 12), text_color="gray", anchor="w",
                             justify="left", wraplength=520).pack(
                    anchor="w", padx=12, pady=2)

            ctk.CTkFrame(box, height=1, fg_color="gray40").pack(fill="x", padx=12, pady=(8, 6))

            stats_row = ctk.CTkFrame(box, fg_color="transparent")
            stats_row.pack(fill="x", padx=12, pady=(0, 12))
            for label, value, color in [
                ("✅ Done",        f"{sprint['done']} / {sprint['total']}", "#27ae60"),
                ("🔵 In Progress", str(sprint["inProgress"]),              "#1f6aa5"),
                ("⬜ To Do",       str(sprint["todo"]),                    "gray"),
                ("SP Done",        f"{sprint['spDone']} / {sprint['spTotal']}", "#8e44ad"),
            ]:
                cell = ctk.CTkFrame(stats_row, fg_color="transparent")
                cell.pack(side="left", expand=True, fill="x", padx=4)
                ctk.CTkLabel(cell, text=value, font=("", 18, "bold"),
                             text_color=color).pack()
                ctk.CTkLabel(cell, text=label, font=("", 10),
                             text_color="gray").pack()

        ctk.CTkButton(popup, text="✕  Close", width=120, height=34,
                      command=popup.destroy).pack(pady=(10, 20))

    def _load_jira_for_current(self) -> None:
        """Fetch Jira tasks for current speaker (open + closed in parallel)."""
        current = self._timer.current
        if current is None:
            self._jira_header.configure(text="⚡  Active")
            self._jira_closed_header.configure(text="✅  Done")
            self._clear_jira_list()
            return

        name = current.participant.name
        self._jira_header.configure(text=f"⚡  {name} — Active")
        self._jira_closed_header.configure(text=f"✅  {name} — Done")
        self._clear_jira_list()

        # Show loading indicator
        loading = ctk.CTkLabel(
            self._list_jira, text="⏳ Loading…", font=("", 11), text_color="gray"
        )
        loading.pack(padx=8, pady=8, anchor="w")

        account_id = current.participant.jira_account_id
        is_jefote = current.participant.is_jefote
        board_url = os.environ.get("JIRA_BOARD_URL", "")

        # Collect results from both fetches before rendering
        self._jira_fetch_results = {}

        def _on_open(issues):
            self._jira_fetch_results["open"] = issues
            if "closed" in self._jira_fetch_results:
                self.after(
                    0,
                    lambda: self._render_jira_issues(
                        self._jira_fetch_results["open"],
                        self._jira_fetch_results["closed"],
                    ),
                )

        def _on_closed(issues):
            self._jira_fetch_results["closed"] = issues
            if "open" in self._jira_fetch_results:
                self.after(
                    0,
                    lambda: self._render_jira_issues(
                        self._jira_fetch_results["open"],
                        self._jira_fetch_results["closed"],
                    ),
                )

        # Fetch both in parallel
        fetch_issues_for_participant(
            account_id,
            board_url=board_url,
            on_done=_on_open,
            on_error=lambda err: self.after(0, lambda: self._jira_error(err)),
            is_jefote=is_jefote,
        )
        fetch_closed_issues_for_participant(
            account_id,
            board_url=board_url,
            on_done=_on_closed,
            on_error=lambda err: self._jira_fetch_results.setdefault("closed", []),
            is_jefote=is_jefote,
        )

    def _clear_jira_list(self) -> None:
        """Clear both open and closed Jira lists."""
        for w in self._list_jira.winfo_children():
            w.destroy()
        for w in self._list_jira_closed.winfo_children():
            w.destroy()

    def _jira_error(self, msg: str) -> None:
        """Display error message in Jira panel."""
        self._clear_jira_list()
        lbl = ctk.CTkLabel(
            self._list_jira,
            text=f"⚠ {msg}",
            font=("", 11),
            text_color="#e74c3c",
            wraplength=500,
            justify="left",
        )
        lbl.pack(padx=8, pady=6, anchor="w")

    def _render_jira_issues(
        self, issues: list[dict], closed: list[dict] | None = None
    ) -> None:
        """Render open and closed Jira task cards."""
        self._clear_jira_list()
        if not issues and not closed:
            ctk.CTkLabel(
                self._list_jira,
                text="No issues found",
                font=("", 11),
                text_color="gray",
            ).pack(padx=8, pady=12)
            return

        STATUS_COLORS = {
            "In Progress": "#1f6aa5",
            "En curso": "#1f6aa5",
            "In Review": "#8e44ad",
            "Code Review": "#b7950b",
            "To Do": "#555555",
            "Abierta": "#555555",
            "Open": "#555555",
            "Blocked": "#c0392b",
            "Bloqueada": "#c0392b",
            "More Info": "#d68910",
            "Más info": "#d68910",
            "Done": "#27ae60",
            "Cerrada": "#27ae60",
            "Closed": "#27ae60",
            "Resolved": "#e67e22",
            "Resuelta": "#e67e22",
        }

        # ── Open issues ─────────────────────────────────────────────────────
        for issue in issues:
            card = ctk.CTkFrame(
                self._list_jira, corner_radius=6, fg_color=("gray88", "gray22")
            )
            card.pack(fill="x", padx=6, pady=4)
            card.columnconfigure(1, weight=1)

            # Top row: key button | SP | status
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=8, pady=(8, 2))

            # Clickable key
            key_btn = ctk.CTkButton(
                top,
                text=issue["key"],
                font=("", self._jira_font_size + 2, "bold"),
                width=120,
                height=28,
                fg_color="transparent",
                text_color=("#1f6aa5", "#4a9ede"),
                hover=False,
                anchor="w",
                command=lambda url=issue["url"]: subprocess.run(
                    ["open", url], check=False
                ),
            )
            key_btn.pack(side="left", padx=(0, 8))

            # Status badge
            status = issue["status"]
            status_color = STATUS_COLORS.get(status, "#555555")
            status_lbl = ctk.CTkLabel(
                top,
                text=f" {status} ",
                font=("", 13, "bold"),
                text_color="white",
                fg_color=status_color,
                corner_radius=4,
            )
            status_lbl.pack(side="right", padx=(4, 0))

            # Story points
            sp_text = (
                f"SP: {int(issue['points'])}"
                if issue["points"] is not None
                else "SP: —"
            )
            sp_lbl = ctk.CTkLabel(top, text=sp_text, font=("", 12), text_color="gray")
            sp_lbl.pack(side="right", padx=(0, 8))

            # Summary — wraplength tracks card width dynamically
            summary_lbl = ctk.CTkLabel(
                card,
                text=issue["summary"],
                font=("", self._jira_font_size),
                anchor="w",
                justify="left",
                wraplength=400,
            )
            summary_lbl.pack(fill="x", padx=10, pady=(2, 8), anchor="w")
            card.bind(
                "<Configure>",
                lambda e, lbl=summary_lbl: lbl.configure(
                    wraplength=max(100, e.width - 24)
                ),
            )

        apply_scroll(self._list_jira)

        # ── Closed issues ────────────────────────────────────────────────────
        if closed:
            for issue in closed:
                card = ctk.CTkFrame(
                    self._list_jira_closed,
                    corner_radius=6,
                    fg_color=("gray84", "gray18"),
                )
                card.pack(fill="x", padx=6, pady=4)
                top = ctk.CTkFrame(card, fg_color="transparent")
                top.pack(fill="x", padx=8, pady=(8, 2))

                # Key button
                ctk.CTkButton(
                    top,
                    text=issue["key"],
                    font=("", self._jira_font_size + 2, "bold"),
                    width=120,
                    height=28,
                    fg_color="transparent",
                    text_color=("gray50", "gray50"),
                    hover=False,
                    anchor="w",
                    command=lambda url=issue["url"]: subprocess.run(
                        ["open", url], check=False
                    ),
                ).pack(side="left", padx=(0, 8))

                # Status badge — Cerrada/Closed/Done=green, Resuelta/Resolved=orange
                _badge_color = {
                    "Resolved": "#e67e22", "Resuelta": "#e67e22",
                    "Done": "#27ae60", "Cerrada": "#27ae60", "Closed": "#27ae60",
                }.get(issue["status"], "#27ae60")
                ctk.CTkLabel(
                    top,
                    text=f" {issue['status']} ",
                    font=("", 13, "bold"),
                    text_color="white",
                    fg_color=_badge_color,
                    corner_radius=4,
                ).pack(side="right", padx=(4, 0))

                # Story points (left of status badge)
                sp_text = (
                    f"SP: {int(issue['points'])}"
                    if issue["points"] is not None
                    else "SP: —"
                )
                ctk.CTkLabel(top, text=sp_text, font=("", 10), text_color="gray").pack(
                    side="right", padx=(0, 8)
                )

                # Summary — wraplength tracks card width dynamically
                summary_lbl = ctk.CTkLabel(
                    card,
                    text=issue["summary"],
                    font=("", self._jira_font_size),
                    anchor="w",
                    justify="left",
                    wraplength=400,
                    text_color="gray",
                )
                summary_lbl.pack(fill="x", padx=10, pady=(2, 8), anchor="w")
                card.bind(
                    "<Configure>",
                    lambda e, lbl=summary_lbl: lbl.configure(
                        wraplength=max(100, e.width - 24)
                    ),
                )
        else:
            ctk.CTkLabel(
                self._list_jira_closed,
                text="No closed issues",
                font=("", 11),
                text_color="gray",
            ).pack(padx=8, pady=12)

        apply_scroll(self._list_jira_closed)
