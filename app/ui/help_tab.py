"""Help tab — scrollable reference guide for all app features."""

# pylint: disable=line-too-long

import customtkinter as ctk

from app.ui.scroll_fix import apply as apply_scroll

HELP_CONTENT = [
    (
        "🕐  Meeting",
        [
            (
                "Start",
                "Starts the meeting. Randomly orders participants (non-managers first, then Managers & +). Each person gets an equal slice of the total meeting time.",
            ),
            (
                "Pause / Resume",
                "Pauses the current speaker's timer. The overall meeting clock keeps running so you always see the real elapsed time.",
            ),
            (
                "Next",
                "Advances to the next participant and automatically loads their Jira tasks (Active + Done columns). If paused, resumes the timer.",
            ),
            ("Stop", "Ends the meeting early and marks remaining participants as done. Unlocks Save Session."),
            (
                "Reset",
                "Clears everything and returns to idle. Jira task columns are also cleared. Only available after Stop or when the meeting ends naturally.",
            ),
            (
                "Save Session",
                "Saves the session to the local database (visible in Stats). Only available once per meeting — the button is disabled after saving to prevent duplicates.",
            ),
            (
                "🏃  Sprint Info",
                "Opens a popup with the current RBI sprint details: name, dates, days remaining, sprint goal (clickable if it's a URL), and issue stats — Done / In Progress / To Do / Story Points done.",
            ),
            (
                "Status dot ●",
                "Shows the current speaker's time usage: green → yellow → red as they approach their limit. Blinks red in the last 10 seconds.",
            ),
            (
                "Current Speaker avatar",
                "Displays the Jira profile picture of the current speaker (if synced via Settings) above their name.",
            ),
            (
                "Attendees list (col 2)",
                "Shows all participants in random order with their timers. Click any row — including already-done participants — to load their Jira tasks in the right columns. Useful when someone arrives late.",
            ),
            (
                "⚡ Active (col 3)",
                "Active sprint issues assigned to the current (or clicked) speaker. Click a ticket key to open it in Jira. Colour-coded by status: blue=In Progress, purple=In Review, orange=More Info, red=Blocked, grey=Open.",
            ),
            (
                "✅ Done (col 4)",
                "Issues completed this sprint by the same speaker. Green badge = Cerrada/Closed/Done, orange badge = Resuelta/Resolved.",
            ),
            (
                "Font size A− / A / A+",
                "Three font size presets (12 / 18 / 24) in the Done column header. Applies to ticket key and summary text in both columns. The active size is highlighted in blue.",
            ),
        ],
    ),
    (
        "👥  Participants",
        [
            (
                "Meeting Name",
                "The name shown in the title bar and saved with each session.",
            ),
            (
                "Duration (min)",
                "Total planned meeting time in minutes. Divided equally among all non-manager participants.",
            ),
            (
                "Save",
                "Saves name, duration and bell settings. Cannot be changed while a meeting is running.",
            ),
            (
                "All Participants list",
                "Everyone in the app. Select one and use → to add to today's meeting, or « for everyone at once.",
            ),
            (
                "In Today's Meeting",
                "Attendees for this session. Use ← to remove someone or ✕ to clear the list.",
            ),
            (
                "+ New",
                "Add a participant manually — enter name, Jira Account ID and avatar URL/path. The Jira ID links the person to their sprint tasks in the Meeting tab.",
            ),
            (
                "✏ Edit / 🗑 Delete",
                "Edit name, Jira ID, avatar or manager flag. Delete removes permanently.",
            ),
            (
                "🏆 Ranking",
                "Opens a popup with two columns: Top 3 most talkative (🥇🥈🥉) and Top 3 least talkative (🐢🐌🦥), ranked by total cumulative speaking time across all saved sessions. Managers are excluded.",
            ),
            (
                "🔔  Bell alert",
                "Plays a chime every second during the last 10 s of each turn. Toggle on/off, adjust volume with the slider, or preview with ▶ Test.",
            ),
        ],
    ),
    (
        "📊  Stats",
        [
            (
                "Session history",
                "Dropdown showing all saved sessions with date and actual duration. Select one to see its per-participant breakdown.",
            ),
            (
                "🗑 Delete",
                "Deletes the selected session after confirmation. The charts update immediately.",
            ),
            (
                "Top chart",
                "Meeting duration history — planned (blue) vs actual (red) across all sessions. Hover a point for details.",
            ),
            (
                "Bottom chart",
                "Per-participant allocated vs actual speaking time for the selected session. Hover a bar for the exact value.",
            ),
        ],
    ),
    (
        "⚙️  Settings",
        [
            (
                "Atlassian Email",
                "Your Netskope Atlassian email. Stored locally in the DB. Environment variables (~/.zshrc) take precedence at runtime.",
            ),
            (
                "Atlassian API Token",
                "Your Atlassian API token (from id.atlassian.com). Masked with ● — use 👁 to reveal. Click Save to persist.",
            ),
            (
                "Test connection",
                "Validates the email + token against the Jira API (/myself endpoint). Shows ✅ Verified on success.",
            ),
            (
                "Board Filter URL",
                "The Jira board URL used to sync team members, e.g. .../boards/14955?label=polaris-squad. The ?label= query param is used to filter which sprint members appear.",
            ),
            (
                "Refresh Users",
                "Fetches unique assignees from the board's active sprint. New members (not yet in DB) appear at the top with Add ✚ checkbox enabled. Already-synced members appear below, dimmed.",
            ),
            (
                "Add ✚ / Jefazo ⭐",
                "Tick Add ✚ to include a new member. Tick Jefazo ⭐ to mark them as a manager. Click Save Selected to write to the database.",
            ),
            (
                "Save Selected",
                "Saves ticked members with their Jira account ID and avatar path. The Participants tab refreshes automatically.",
            ),
        ],
    ),
    (
        "⚙  General",
        [
            (
                "Closing the app",
                "The app warns you if a meeting is in progress. Stop or finish the meeting before closing.",
            ),
            (
                "Data storage",
                "All data is stored locally in data/scrum.db (SQLite). The file is excluded from git. Delete it to start fresh — it is recreated automatically on next launch.",
            ),
            (
                "Avatars",
                "Profile pictures are downloaded from Jira and cached in data/avatars/<accountId>.png. They replace food icons once synced via Settings → Refresh Users.",
            ),
            (
                "Jira status colours",
                "In Progress / En curso = blue · In Review = purple · Blocked = red · More Info = amber · Code Review = gold · Cerrada/Closed/Done = green · Resuelta/Resolved = orange.",
            ),
        ],
    ),
]


class HelpTab(ctk.CTkFrame):
    """Scrollable help tab — feature reference for all tabs."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._build_ui()

    def _build_ui(self) -> None:
        """Build scrollable help content from HELP_CONTENT."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scroll.columnconfigure(0, weight=1)

        row = 0
        for section, items in HELP_CONTENT:
            ctk.CTkLabel(scroll, text=section, font=("", 15, "bold"), anchor="w").grid(
                row=row, column=0, sticky="w", padx=8, pady=(16, 4)
            )
            row += 1

            sep = ctk.CTkFrame(scroll, height=2, fg_color="#3a3a3a")
            sep.grid(row=row, column=0, sticky="ew", padx=8, pady=(0, 6))
            row += 1

            for title, desc in items:
                item_frame = ctk.CTkFrame(scroll, fg_color="#1e1e2e", corner_radius=8)
                item_frame.grid(row=row, column=0, sticky="ew", padx=8, pady=3)
                item_frame.columnconfigure(1, weight=1)

                ctk.CTkLabel(
                    item_frame,
                    text=title,
                    font=("", 12, "bold"),
                    anchor="nw",
                    width=160,
                ).grid(row=0, column=0, padx=(12, 8), pady=8, sticky="nw")

                ctk.CTkLabel(
                    item_frame,
                    text=desc,
                    font=("", 12),
                    anchor="nw",
                    justify="left",
                    wraplength=480,
                ).grid(row=0, column=1, padx=(0, 12), pady=8, sticky="nw")

                row += 1

        ctk.CTkLabel(
            scroll,
            text="RBI Scrum Timer — made with ❤ by the RBI team",
            font=("", 11),
            text_color="gray",
        ).grid(row=row, column=0, pady=(20, 8))

        apply_scroll(scroll)
