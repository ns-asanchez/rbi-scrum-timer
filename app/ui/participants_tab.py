"""Participants tab — manage attendees, config, Jira sync."""

import customtkinter as ctk
from PIL import Image, ImageDraw

from app import db
from app.bell import play_bell
from app.models import MeetingState
from app.ui.dialogs import askyesno, showerror, showinfo, showwarning
from app.ui.scroll_fix import apply as apply_scroll


def _make_avatar(path: str, size: int = 28) -> ctk.CTkImage | None:
    """Create a circular avatar from a local image file."""
    try:
        img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None


class ParticipantsTab(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        get_state_cb,
        get_attendees_cb,
        set_attendees_cb,
        get_config_cb,
        set_config_cb,
    ):
        super().__init__(parent, fg_color="transparent")
        self._get_state = get_state_cb
        self._get_attendees = get_attendees_cb
        self._set_attendees = set_attendees_cb
        self._get_config = get_config_cb
        self._set_config = set_config_cb

        self._all_participants = []
        self._attendees = []
        self._selected_all: int | None = None
        self._selected_mtg: int | None = None

        self._build_ui()
        self.load_data()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Build 3-column layout: all participants, transfer buttons, in-meeting participants."""
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=2)
        self.rowconfigure(3, weight=1)

        # ── Header row 1: meeting name + duration ─────────────────────────────
        cfg_frame = ctk.CTkFrame(self)
        cfg_frame.grid(
            row=0, column=0, columnspan=3, padx=10, pady=(10, 6), sticky="ew"
        )
        ctk.CTkLabel(cfg_frame, text="Meeting Name:", font=("", 12, "bold")).pack(
            side="left", padx=(12, 8)
        )
        self._entry_name = ctk.CTkEntry(cfg_frame, width=220)
        self._entry_name.pack(side="left")
        ctk.CTkLabel(cfg_frame, text="Duration (min):", font=("", 12, "bold")).pack(
            side="left", padx=(16, 8)
        )
        self._entry_duration = ctk.CTkEntry(cfg_frame, width=50, justify="center")
        self._entry_duration.pack(side="left")
        ctk.CTkButton(cfg_frame, text="Save", width=80, command=self._save_config).pack(
            side="left", padx=8
        )

        # ── Header row 2: bell settings ───────────────────────────────────────
        bell_frame = ctk.CTkFrame(self)
        bell_frame.grid(
            row=1, column=0, columnspan=3, padx=10, pady=(0, 6), sticky="ew"
        )

        self._bell_var = ctk.BooleanVar(value=True)
        self._bell_check = ctk.CTkCheckBox(
            bell_frame,
            text="🔔  Bell alert (last 10 s of each turn)",
            variable=self._bell_var,
            command=self._on_bell_toggle,
            font=("", 12),
        )
        self._bell_check.pack(side="left", padx=(12, 16))

        ctk.CTkLabel(bell_frame, text="Volume:", font=("", 12)).pack(
            side="left", padx=(0, 6)
        )
        self._bell_volume_var = ctk.IntVar(value=70)
        self._bell_slider = ctk.CTkSlider(
            bell_frame,
            from_=0,
            to=100,
            number_of_steps=20,
            variable=self._bell_volume_var,
            width=140,
            command=self._on_volume_change,
        )
        self._bell_slider.pack(side="left")
        self._bell_volume_lbl = ctk.CTkLabel(
            bell_frame, text="70%", font=("", 12), width=36
        )
        self._bell_volume_lbl.pack(side="left", padx=(6, 8))
        ctk.CTkButton(
            bell_frame,
            text="▶ Test",
            width=70,
            command=self._test_bell,
        ).pack(side="left", padx=(4, 8))

        # ── Left: all participants ─────────────────────────────────────────────
        ctk.CTkLabel(self, text="All Participants", font=("", 13, "bold")).grid(
            row=2, column=0, padx=10, pady=(8, 2), sticky="nw"
        )
        self._list_all = ctk.CTkScrollableFrame(self)
        self._list_all.grid(row=3, column=0, padx=(10, 4), pady=(0, 4), sticky="nsew")
        self._list_all.columnconfigure(0, weight=1)

        all_btns = ctk.CTkFrame(self, fg_color="transparent")
        all_btns.grid(row=4, column=0, padx=10, pady=(0, 8), sticky="ew")
        ctk.CTkButton(
            all_btns, text="+ New", width=80, command=self._open_add_dialog
        ).pack(side="left", padx=4)
        self._btn_edit = ctk.CTkButton(
            all_btns, text="✏ Edit", width=80, command=self._open_edit_dialog
        )
        self._btn_edit.pack(side="left", padx=4)
        self._btn_delete = ctk.CTkButton(
            all_btns,
            text="🗑 Delete",
            width=80,
            fg_color="#c0392b",
            hover_color="#922b21",
            command=self._delete_participant,
        )
        self._btn_delete.pack(side="left", padx=4)
        ctk.CTkButton(
            all_btns,
            text="🏆 Ranking",
            width=90,
            fg_color="#6d4c9e",
            hover_color="#4a3070",
            command=self._show_ranking,
        ).pack(side="left", padx=4)

        # ── Center: transfer buttons ───────────────────────────────────────────
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=3, column=1, padx=4, pady=0, sticky="ns")
        center.rowconfigure((0, 1, 2, 3, 4), weight=1)
        self._btn_add_to_mtg = ctk.CTkButton(
            center, text="→", width=50, command=self._add_to_meeting
        )
        self._btn_add_to_mtg.grid(row=0, column=0, pady=4)
        self._btn_add_all = ctk.CTkButton(
            center, text="»", width=50, command=self._add_all_to_meeting
        )
        self._btn_add_all.grid(row=1, column=0, pady=4)
        self._btn_remove_from_mtg = ctk.CTkButton(
            center, text="←", width=50, command=self._remove_from_meeting
        )
        self._btn_remove_from_mtg.grid(row=2, column=0, pady=4)
        self._btn_clear_mtg = ctk.CTkButton(
            center,
            text="✕",
            width=50,
            fg_color="#555",
            hover_color="#333",
            command=self._clear_meeting,
        )
        self._btn_clear_mtg.grid(row=3, column=0, pady=4)

        # ── Right: meeting attendees ───────────────────────────────────────────
        ctk.CTkLabel(self, text="In Today's Meeting", font=("", 13, "bold")).grid(
            row=2, column=2, padx=10, pady=(8, 2), sticky="nw"
        )
        self._list_meeting = ctk.CTkScrollableFrame(self)
        self._list_meeting.grid(
            row=3, column=2, padx=(4, 10), pady=(0, 4), sticky="nsew"
        )
        self._list_meeting.columnconfigure(0, weight=1)

        self._lbl_attendee_count = ctk.CTkLabel(
            self, text="0 attendees", font=("", 11), text_color="gray"
        )
        self._lbl_attendee_count.grid(row=4, column=2, padx=10, pady=(0, 8), sticky="w")

        # ── Inline selection tracking ──────────────────────────────────────────
        self._selected_all: int | None = None
        self._selected_mtg: int | None = None

    def scrollable_frames(self):
        """Return scrollable frames for scroll fix."""
        return [self._list_all, self._list_meeting]

    # ── Data loading ──────────────────────────────────────────────────────────

    def load_data(self) -> None:
        """Load participants and config from database, refresh UI."""
        self._all_participants = db.get_all_participants()
        config = self._get_config()
        self._entry_duration.delete(0, "end")
        self._entry_duration.insert(0, str(config.duration_minutes))
        self._entry_name.delete(0, "end")
        self._entry_name.insert(0, config.meeting_name)
        self._bell_var.set(config.bell_enabled)
        self._bell_volume_var.set(config.bell_volume)
        self._bell_volume_lbl.configure(text=f"{config.bell_volume}%")
        self._bell_slider.configure(
            state="normal" if config.bell_enabled else "disabled"
        )
        # Re-sync attendees: keep same IDs but replace objects with fresh DB data
        fresh = {p.id: p for p in self._all_participants}
        current_ids = {a.id for a in self._get_attendees()}
        self._attendees = [fresh[pid] for pid in current_ids if pid in fresh]
        self._render_all()
        self._render_meeting()

    def _render_all(self) -> None:
        """Render all participants list."""
        for w in self._list_all.winfo_children():
            w.destroy()
        for p in self._all_participants:
            self._make_all_row(p)
        apply_scroll(self._list_all)

    def _make_all_row(self, p) -> None:
        """Render a row for a participant in the all-participants list."""
        in_mtg = any(a.id == p.id for a in self._attendees)
        row = ctk.CTkFrame(
            self._list_all,
            fg_color="#1a3a5a" if self._selected_all == p.id else "transparent",
            corner_radius=6,
        )
        row.pack(fill="x", padx=4, pady=2)
        dimmed = "#888" if in_mtg else None

        # Avatar or icon
        if p.avatar_path:
            img = _make_avatar(p.avatar_path, 28)
            if img:
                lbl = ctk.CTkLabel(row, text="", image=img, width=32)
                lbl._image = img
                lbl.pack(side="left", padx=(6, 2), pady=4)
            else:
                icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
                ctk.CTkLabel(row, text=icon, width=32).pack(
                    side="left", padx=(6, 2), pady=4
                )
        else:
            icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
            ctk.CTkLabel(row, text=icon, width=32).pack(
                side="left", padx=(6, 2), pady=4
            )

        ctk.CTkLabel(row, text=p.name, anchor="w", text_color=dimmed).pack(
            side="left", padx=4, pady=6
        )
        if in_mtg:
            ctk.CTkLabel(row, text="✓", text_color="#1a7a4a").pack(side="right", padx=8)
        row.bind("<Button-1>", lambda e, pid=p.id: self._select_all(pid))
        for child in row.winfo_children():
            child.bind("<Button-1>", lambda e, pid=p.id: self._select_all(pid))

    def _render_meeting(self) -> None:
        """Render attendees for today's meeting."""
        for w in self._list_meeting.winfo_children():
            w.destroy()
        for p in sorted(self._attendees, key=lambda x: x.name):
            self._make_mtg_row(p)
        non_j = sum(1 for p in self._attendees if not p.is_jefote)
        total = len(self._attendees)
        self._lbl_attendee_count.configure(
            text=f"{total} attendee{'s' if total != 1 else ''} ({non_j} non-jefote{'s' if non_j != 1 else ''})"
        )
        self._set_attendees(self._attendees)
        apply_scroll(self._list_meeting)

    def _make_mtg_row(self, p) -> None:
        """Render a row for a participant in the meeting attendees list."""
        row = ctk.CTkFrame(
            self._list_meeting,
            fg_color="#1a3a5a" if self._selected_mtg == p.id else "transparent",
            corner_radius=6,
        )
        row.pack(fill="x", padx=4, pady=2)

        if p.avatar_path:
            img = _make_avatar(p.avatar_path, 28)
            if img:
                lbl = ctk.CTkLabel(row, text="", image=img, width=32)
                lbl._image = img
                lbl.pack(side="left", padx=(6, 2), pady=4)
            else:
                icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
                ctk.CTkLabel(row, text=icon, width=32).pack(
                    side="left", padx=(6, 2), pady=4
                )
        else:
            icon = "👑" if p.is_jefote else (p.food_icon or "🍕")
            ctk.CTkLabel(row, text=icon, width=32).pack(
                side="left", padx=(6, 2), pady=4
            )

        ctk.CTkLabel(row, text=p.name, anchor="w").pack(side="left", padx=4, pady=6)
        row.bind("<Button-1>", lambda e, pid=p.id: self._select_mtg(pid))
        for child in row.winfo_children():
            child.bind("<Button-1>", lambda e, pid=p.id: self._select_mtg(pid))

    # ── Selection ─────────────────────────────────────────────────────────────

    def _select_all(self, pid: int) -> None:
        """Toggle selection in all-participants list."""
        self._selected_all = pid if self._selected_all != pid else None
        self._render_all()

    def _select_mtg(self, pid: int) -> None:
        """Toggle selection in meeting attendees list."""
        self._selected_mtg = pid if self._selected_mtg != pid else None
        self._render_meeting()

    # ── Transfer ──────────────────────────────────────────────────────────────

    def _is_meeting_locked(self) -> bool:
        """Check if a meeting is currently running or paused."""
        return self._get_state() in (MeetingState.RUNNING, MeetingState.PAUSED)

    def _add_to_meeting(self) -> None:
        """Add selected participant to today's meeting."""
        if self._is_meeting_locked():
            showwarning(
                self, "Meeting Active", "Cannot modify attendees during a meeting."
            )
            return
        if self._selected_all is None:
            return
        p = next(
            (x for x in self._all_participants if x.id == self._selected_all), None
        )
        if p is None:
            return
        if any(a.id == p.id for a in self._attendees):
            showinfo(self, "Already Added", f"{p.name} is already in the meeting.")
            return
        self._attendees.append(p)
        self._render_all()
        self._render_meeting()

    def _remove_from_meeting(self) -> None:
        """Remove selected participant from today's meeting."""
        if self._is_meeting_locked():
            showwarning(
                self, "Meeting Active", "Cannot modify attendees during a meeting."
            )
            return
        if self._selected_mtg is None:
            return
        self._attendees = [a for a in self._attendees if a.id != self._selected_mtg]
        self._selected_mtg = None
        self._render_all()
        self._render_meeting()

    def _add_all_to_meeting(self) -> None:
        """Add all participants not already in meeting to today's meeting."""
        if self._is_meeting_locked():
            showwarning(
                self, "Meeting Active", "Cannot modify attendees during a meeting."
            )
            return
        existing_ids = {a.id for a in self._attendees}
        added = 0
        for p in self._all_participants:
            if p.id not in existing_ids:
                self._attendees.append(p)
                added += 1
        self._render_all()
        self._render_meeting()

    def _clear_meeting(self) -> None:
        """Remove all participants from today's meeting."""
        if self._is_meeting_locked():
            showwarning(
                self, "Meeting Active", "Cannot modify attendees during a meeting."
            )
            return
        self._attendees = []
        self._selected_mtg = None
        self._render_all()
        self._render_meeting()

    # ── Config ────────────────────────────────────────────────────────────────

    def _save_config(self) -> None:
        """Save meeting name, duration, and bell settings to database."""
        if self._is_meeting_locked():
            showwarning(
                self, "Meeting Active", "Cannot change duration during a meeting."
            )
            return
        try:
            val = int(self._entry_duration.get())
            if val < 1:
                raise ValueError
        except ValueError:
            showerror(self, "Invalid", "Duration must be a positive integer.")
            return
        name = self._entry_name.get().strip() or "Polaris Rising [Ab+B]"
        bell_enabled = self._bell_var.get()
        bell_volume = int(self._bell_volume_var.get())
        db.set_config(val, name, bell_enabled, bell_volume)
        self._set_config(val, name, bell_enabled, bell_volume)
        showinfo(self, "Saved", f"Config saved: '{name}', {val} min.")

    def _on_bell_toggle(self) -> None:
        """Enable/disable the bell volume slider when checkbox is toggled."""
        enabled = self._bell_var.get()
        self._bell_slider.configure(state="normal" if enabled else "disabled")

    def _on_volume_change(self, value) -> None:
        """Update volume percentage label when slider changes."""
        pct = int(float(value))
        self._bell_volume_lbl.configure(text=f"{pct}%")

    def _test_bell(self) -> None:
        """Play bell sound at current volume for testing."""
        play_bell(int(self._bell_volume_var.get()))

    # ── CRUD dialogs ──────────────────────────────────────────────────────────

    def _open_add_dialog(self) -> None:
        """Open dialog to add a new participant."""
        self._participant_dialog("Add Participant", None)

    def _open_edit_dialog(self) -> None:
        """Open dialog to edit selected participant."""
        if self._selected_all is None:
            showinfo(self, "Select", "Select a participant to edit.")
            return
        p = next(
            (x for x in self._all_participants if x.id == self._selected_all), None
        )
        if p:
            self._participant_dialog("Edit Participant", p)

    def _participant_dialog(self, title: str, participant) -> None:
        """Open modal dialog to add or edit a participant."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x360")
        dialog.resizable(False, False)
        dialog.grab_set()

        fields_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        fields_frame.pack(fill="x", padx=20, pady=(16, 0))
        fields_frame.columnconfigure(1, weight=1)

        def _field(row, label, value="", placeholder=""):
            ctk.CTkLabel(fields_frame, text=label, anchor="w", width=90).grid(
                row=row, column=0, sticky="w", pady=4
            )
            entry = ctk.CTkEntry(fields_frame, placeholder_text=placeholder, height=30)
            entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
            if value:
                entry.insert(0, value)
            return entry

        p = participant
        entry_name = _field(0, "Name *", p.name if p else "", "Alex Sanchez")
        entry_jira_id = _field(
            1, "Jira ID", p.jira_account_id if p else "", "712020:xxxx…"
        )
        entry_avatar = _field(
            2,
            "Avatar URL",
            p.avatar_path if p else "",
            "https://…/avatar.png  (or local path)",
        )

        jefote_var = ctk.BooleanVar(value=p.is_jefote if p else False)
        jefote_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        jefote_frame.pack(anchor="w", padx=20, pady=(8, 0))
        ctk.CTkCheckBox(
            jefote_frame, text="Is Jefote / Manager", variable=jefote_var
        ).pack(side="left")

        ctk.CTkLabel(
            dialog,
            text="* Name is required. Jira ID links to Jira tasks.",
            font=("", 10),
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(4, 0))

        def _save():
            name = entry_name.get().strip()
            if not name:
                showerror(dialog, "Error", "Name cannot be empty.")
                return
            jira_id = entry_jira_id.get().strip()
            avatar_val = entry_avatar.get().strip()
            try:
                if participant:
                    db.update_participant(
                        participant.id,
                        name,
                        jefote_var.get(),
                        jira_account_id=jira_id,
                        avatar_path=avatar_val,
                    )
                else:
                    db.add_participant(
                        name,
                        jefote_var.get(),
                        jira_account_id=jira_id,
                        avatar_path=avatar_val,
                    )
            except Exception as e:
                showerror(dialog, "Error", str(e))
                return
            dialog.destroy()
            self._selected_all = None
            self.load_data()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(12, 0))
        ctk.CTkButton(
            btn_row,
            text="Save",
            width=100,
            fg_color="#1a7a4a",
            hover_color="#145c36",
            command=_save,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_row,
            text="Cancel",
            width=100,
            fg_color="#555",
            hover_color="#333",
            command=dialog.destroy,
        ).pack(side="left", padx=6)

    def _delete_participant(self) -> None:
        """Delete selected participant after confirmation."""
        if self._selected_all is None:
            showinfo(self, "Select", "Select a participant to delete.")
            return
        p = next(
            (x for x in self._all_participants if x.id == self._selected_all), None
        )
        if p is None:
            return
        if not askyesno(self, "Confirm", f"Delete '{p.name}'?"):
            return
        db.delete_participant(p.id)
        self._attendees = [a for a in self._attendees if a.id != p.id]
        self._selected_all = None
        self.load_data()

    def _show_ranking(self) -> None:
        """Show top3 most and least talkative participants across all sessions."""
        rows = db.get_participant_time_ranking()
        if not rows:
            showinfo(self, "Ranking", "No session data yet. Save a meeting first.")
            return

        popup = ctk.CTkToplevel(self)
        popup.title("🏆  Speaker Ranking")
        popup.resizable(False, False)
        # transient: stays on top of parent, doesn't block it
        popup.transient(self.winfo_toplevel())
        popup.lift()
        popup.focus_force()
        popup.update_idletasks()
        pw, ph = 700, 460
        px = self.winfo_rootx() + self.winfo_width() // 2 - pw // 2
        py = self.winfo_rooty() + self.winfo_height() // 2 - ph // 2
        popup.geometry(f"{pw}x{ph}+{px}+{py}")

        ctk.CTkLabel(popup, text="🏆  Speaker Ranking", font=("", 26, "bold")).pack(
            pady=(24, 6)
        )
        ctk.CTkLabel(
            popup,
            text="Cumulative speaking time across all saved sessions",
            font=("", 14),
            text_color="gray",
        ).pack(pady=(0, 18))

        cols = ctk.CTkFrame(popup, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=20)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        MEDALS = ["🥇", "🥈", "🥉"]
        TURTLES = ["🐢", "🐌", "🦥"]

        def _col(parent, col, title, entries, icons):
            """Render a ranking column."""
            frame = ctk.CTkFrame(parent, fg_color=("gray88", "gray20"), corner_radius=10)
            frame.grid(row=0, column=col, padx=10, sticky="nsew")
            ctk.CTkLabel(frame, text=title, font=("", 18, "bold")).pack(pady=(16, 10))
            for i, (name, total) in enumerate(entries[:3]):
                m, s = divmod(total, 60)
                time_str = f"{m}:{s:02d}"
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", padx=16, pady=6)
                ctk.CTkLabel(row, text=icons[i], font=("", 32), width=40).pack(
                    side="left"
                )
                ctk.CTkLabel(row, text=name, font=("", 18, "bold"), anchor="w").pack(
                    side="left", padx=(8, 0), fill="x", expand=True
                )
                ctk.CTkLabel(
                    row, text=time_str, font=("", 16), text_color="gray"
                ).pack(side="right")
            frame.pack_propagate(False)

        top3 = rows[:3]
        bot3 = list(reversed(rows[-3:]))
        _col(cols, 0, "⏱  Most talkative", top3, MEDALS)
        _col(cols, 1, "🤫  Least talkative", bot3, TURTLES)

        ctk.CTkButton(popup, text="Close", width=140, height=38, font=("", 14), command=popup.destroy).pack(
            pady=(18, 24)
        )
