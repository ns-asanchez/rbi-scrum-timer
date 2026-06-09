"""Stats tab — display meeting duration history and per-participant speaking time."""

import math

import customtkinter as ctk
import mplcursors
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app import db
from app.ui.dialogs import askyesno


def _secs_to_mmss(seconds: float) -> str:
    """Convert seconds to mm:ss format."""
    seconds = int(round(seconds))
    m, s = divmod(abs(seconds), 60)
    return f"{m}:{s:02d}"


class StatsTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build_ui()

    def _build_ui(self) -> None:
        """Build 2-row layout: top chart (duration history), bottom chart (participant times)."""
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # ── Top chart: meeting duration history ───────────────────────────────
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="nsew")
        top_frame.columnconfigure(0, weight=1)
        top_frame.rowconfigure(0, weight=1)

        self._fig_top = Figure(figsize=(6, 2.8), tight_layout=True)
        self._ax_top = self._fig_top.add_subplot(111)
        self._canvas_top = FigureCanvasTkAgg(self._fig_top, master=top_frame)
        self._canvas_top.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # ── Bottom chart: per-participant time ────────────────────────────────
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.grid(row=1, column=0, padx=10, pady=(4, 10), sticky="nsew")
        bottom_frame.columnconfigure(0, weight=1)
        bottom_frame.rowconfigure(1, weight=1)

        selector_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        selector_row.grid(row=0, column=0, padx=8, pady=(12, 12), sticky="ew")
        ctk.CTkLabel(selector_row, text="Session:", font=("", 12)).pack(
            side="left", padx=(0, 8)
        )
        self._session_var = ctk.StringVar()
        self._session_menu = ctk.CTkOptionMenu(
            selector_row,
            variable=self._session_var,
            values=["—"],
            command=self._on_session_select,
        )
        self._session_menu.pack(side="left")

        self._btn_delete_session = ctk.CTkButton(
            selector_row,
            text="🗑 Delete",
            width=90,
            height=28,
            fg_color="#c0392b",
            hover_color="#922b21",
            command=self._delete_selected_session,
        )
        self._btn_delete_session.pack(side="left", padx=(12, 0))

        self._fig_bot = Figure(figsize=(6, 2.8), tight_layout=True)
        self._ax_bot = self._fig_bot.add_subplot(111)
        self._canvas_bot = FigureCanvasTkAgg(self._fig_bot, master=bottom_frame)
        self._canvas_bot.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        self._sessions: list = []
        self._cursor_top = None
        self._cursor_bot = None

    def load_data(self) -> None:
        """Load all sessions from database and refresh both charts."""
        self._sessions = db.get_sessions()
        self._render_top_chart()
        self._populate_session_selector()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _mmss_yticks(self, ax, max_secs: float) -> None:
        """Set Y axis ticks in seconds with mm:ss labels."""
        if max_secs <= 0:
            return
        # Choose a nice step: aim for ~6-8 ticks
        raw_step = max_secs / 7
        # Round to nearest 15s, 30s, 1m, 2m, 5m
        for step in [15, 30, 60, 120, 300, 600]:
            if raw_step <= step:
                tick_step = step
                break
        else:
            tick_step = int(math.ceil(raw_step / 60) * 60)

        ticks = list(range(0, int(max_secs) + tick_step, tick_step))
        ax.set_yticks(ticks)
        ax.set_yticklabels([_secs_to_mmss(t) for t in ticks], color="white", fontsize=8)

    # ── Top chart ─────────────────────────────────────────────────────────────

    def _render_top_chart(self) -> None:
        """Render meeting duration history (planned vs actual) line chart."""
        ax = self._ax_top
        ax.clear()
        ax.set_facecolor("#1a1a2e")
        self._fig_top.set_facecolor("#1a1a2e")

        if not self._sessions:
            ax.text(
                0.5,
                0.5,
                "No sessions yet",
                ha="center",
                va="center",
                color="gray",
                transform=ax.transAxes,
            )
            self._canvas_top.draw()
            return

        sessions_rev = list(reversed(self._sessions))
        labels = [s.date for s in sessions_rev]  # "YYYY-MM-DD HH:MM" or "YYYY-MM-DD"
        planned = [s.planned_duration for s in sessions_rev]  # seconds
        actual = [s.actual_duration for s in sessions_rev]  # seconds

        x = list(range(len(labels)))
        (line1,) = ax.plot(
            x,
            planned,
            "o-",
            color="#3498db",
            label="Planned",
            linewidth=2,
            markersize=5,
        )
        (line2,) = ax.plot(
            x, actual, "s-", color="#e74c3c", label="Actual", linewidth=2, markersize=5
        )

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7, color="white")
        ax.set_ylabel("Time", color="white", fontsize=9)
        ax.set_title("Meeting Duration History", color="white", fontsize=10)
        ax.legend(fontsize=8, facecolor="#2d2d4e", labelcolor="white")
        ax.spines[:].set_color("#444")
        ax.grid(axis="y", color="#333", linestyle="--", linewidth=0.8)

        max_secs = max(  # pylint: disable=nested-min-max
            max(planned, default=0), max(actual, default=0)
        )
        self._mmss_yticks(ax, max_secs)

        # Tooltips — disconnect previous cursor first
        if self._cursor_top:
            self._cursor_top.remove()
        self._cursor_top = mplcursors.cursor([line1, line2], hover=True)

        @self._cursor_top.connect("add")
        def _tip(sel):
            val = sel.target[1]
            lbl = labels[int(round(sel.target[0]))]
            series = "Planned" if sel.artist == line1 else "Actual"
            sel.annotation.set_text(f"{series}\n{lbl}\n{_secs_to_mmss(val)}")
            sel.annotation.get_bbox_patch().set(fc="#2d2d4e", alpha=0.9)
            sel.annotation.set_color("white")

        self._canvas_top.draw()

    # ── Bottom chart ──────────────────────────────────────────────────────────

    def _populate_session_selector(self) -> None:
        """Populate session dropdown menu and render first session's chart."""
        if not self._sessions:
            self._session_menu.configure(values=["—"])
            self._session_var.set("—")
            self._render_bottom_chart(-1)
            return
        labels = [
            f"{s.date}  ({_secs_to_mmss(s.actual_duration)})" for s in self._sessions
        ]
        self._session_menu.configure(values=labels)
        self._session_var.set(labels[0])
        self._render_bottom_chart(0)

    def _delete_selected_session(self) -> None:
        """Delete selected session after confirmation."""
        value = self._session_var.get()
        if value == "—" or not self._sessions:
            return
        labels = [
            f"{s.date}  ({_secs_to_mmss(s.actual_duration)})" for s in self._sessions
        ]
        if value not in labels:
            return
        idx = labels.index(value)
        session = self._sessions[idx]
        if not askyesno(self, "Delete session", f"Delete session '{session.date}'?"):
            return
        db.delete_session(session.id)
        self.load_data()

    def _on_session_select(self, value: str) -> None:
        """Handle session selection and update bottom chart."""
        labels = [
            f"{s.date}  ({_secs_to_mmss(s.actual_duration)})" for s in self._sessions
        ]
        if value in labels:
            self._render_bottom_chart(labels.index(value))

    def _render_bottom_chart(self, idx: int) -> None:
        """Render per-participant speaking time bar chart for selected session."""
        ax = self._ax_bot
        ax.clear()
        ax.set_facecolor("#1a1a2e")
        self._fig_bot.set_facecolor("#1a1a2e")

        if not self._sessions or idx < 0:
            ax.text(
                0.5,
                0.5,
                "No sessions yet",
                ha="center",
                va="center",
                color="gray",
                transform=ax.transAxes,
            )
            self._canvas_bot.draw()
            return

        session = self._sessions[idx]
        participants = sorted(session.participants, key=lambda p: p["participant_name"])
        if not participants:
            self._canvas_bot.draw()
            return

        names = [
            p["participant_name"] + (" [J]" if p["is_jefote"] else "")
            for p in participants
        ]
        allocated = [p["allocated_time"] for p in participants]  # seconds
        actual = [p["actual_time"] for p in participants]  # seconds

        x = list(range(len(names)))
        bar_w = 0.35
        bars1 = ax.bar(
            [i - bar_w / 2 for i in x],
            allocated,
            bar_w,
            label="Allocated",
            color="#3498db",
            alpha=0.85,
        )
        bars2 = ax.bar(
            [i + bar_w / 2 for i in x],
            actual,
            bar_w,
            label="Actual",
            color="#e74c3c",
            alpha=0.85,
        )

        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8, color="white")
        ax.set_ylabel("Time", color="white", fontsize=9)
        ax.set_title(f"Participant Times — {session.date}", color="white", fontsize=10)
        ax.legend(fontsize=8, facecolor="#2d2d4e", labelcolor="white")
        ax.spines[:].set_color("#444")
        ax.grid(axis="y", color="#333", linestyle="--", linewidth=0.8)

        max_secs = max(  # pylint: disable=nested-min-max
            max(allocated, default=0), max(actual, default=0)
        )
        self._mmss_yticks(ax, max_secs)

        # Tooltips on bars — disconnect previous cursor first
        if self._cursor_bot:
            self._cursor_bot.remove()
        self._cursor_bot = mplcursors.cursor([bars1, bars2], hover=True)

        @self._cursor_bot.connect("add")
        def _tip(sel):
            bar_idx = sel.index
            name = names[bar_idx] if bar_idx < len(names) else "?"
            series = "Allocated" if sel.artist == bars1 else "Actual"
            val = sel.target[1]
            sel.annotation.set_text(f"{name}\n{series}: {_secs_to_mmss(val)}")
            sel.annotation.get_bbox_patch().set(fc="#2d2d4e", alpha=0.9)
            sel.annotation.set_color("white")

        self._canvas_bot.draw()
