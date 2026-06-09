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
                "Skips to the next participant and loads their Jira tasks automatically. If paused, resumes.",
            ),
            ("Stop", "Ends the meeting early. Unlocks the Save Session button."),
            (
                "Reset",
                "Clears everything and returns to idle. Only available after Stop or when the meeting ends naturally.",
            ),
            (
                "Save Session",
                "Saves the session to the local database (visible in Stats). Only available after the meeting finishes.",
            ),
            (
                "Status dot ●",
                "Shows the current speaker's time usage: green → yellow → red as they approach their limit. Blinks red in the last 10 seconds.",
            ),
            (
                "Current Speaker avatar",
                "Displays the Jira profile picture of the current speaker if one has been synced via Settings.",
            ),
            (
                "Attendees list",
                "Shows all participants in order. Avatars are shown when synced from Jira. The active speaker is highlighted.",
            ),
            (
                "Jira Tasks panel",
                "Shows the active sprint issues assigned to the current speaker — open issues at the top, closed this sprint below. Click a ticket key to open it in Jira.",
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
                "Everyone in the app. Select one and use → to add to today's meeting, or « for everyone.",
            ),
            (
                "In Today's Meeting",
                "Attendees for this session. Use ← to remove or ✕ to clear.",
            ),
            (
                "+ New",
                "Add a participant manually with name, Jira Account ID and avatar URL/path. Jira ID links the person to their sprint tasks.",
            ),
            (
                "✏ Edit / 🗑 Delete",
                "Edit name, Jira ID, avatar or manager flag. Delete removes permanently.",
            ),
            (
                "🔔  Bell alert",
                "Plays a chime in the last 10 s of each turn. Toggle, adjust volume, or test with ▶ Test.",
            ),
        ],
    ),
    (
        "📊  Stats",
        [
            (
                "Session history",
                "All saved sessions with date, planned vs actual duration.",
            ),
            (
                "Top chart",
                "Meeting duration history across sessions — planned vs actual.",
            ),
            (
                "Bottom chart",
                "Per-participant speaking time for a selected session. Hover a bar to see the value.",
            ),
        ],
    ),
    (
        "⚙️  Settings",
        [
            (
                "Atlassian Email",
                "Your Netskope Atlassian email. Used for Jira API calls. Set once — stored locally, env vars take precedence.",
            ),
            (
                "Atlassian API Token",
                "Your Atlassian API token (from id.atlassian.com). Masked by default — use 👁 to reveal. Test connection to verify.",
            ),
            (
                "Test connection",
                "Validates the email + token against the Jira API. Shows ✅ Verified on success.",
            ),
            (
                "Board Filter URL",
                "The Jira board URL used to sync team members (e.g. .../boards/14955?label=polaris-squad). The ?label= param filters the sprint members shown.",
            ),
            (
                "Refresh Users",
                "Fetches team members from the board's active sprint. Shows new (not in DB) and already synced members with their avatars.",
            ),
            (
                "Add ✚ / Jefazo ⭐",
                "Tick Add to include a new member. Tick Jefazo to mark them as a manager (appears in Managers & + list). Save Selected to persist.",
            ),
            (
                "Save Selected",
                "Adds ticked members to the local database with their Jira account ID and avatar. Participants tab refreshes automatically.",
            ),
        ],
    ),
    (
        "⚙  General",
        [
            (
                "Closing the app",
                "The app warns you if a meeting is in progress. Stop or finish before closing.",
            ),
            (
                "Data storage",
                "All data is stored locally in data/scrum.db — no external services required.",
            ),
            (
                "Avatars",
                "Profile pictures are downloaded from Jira and cached in data/avatars/. They replace food icons once synced.",
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
