"""Settings tab — credentials + board URL left column, team members right column."""
import os
import customtkinter as ctk
from app.ui.dialogs import showinfo, showwarning, showerror, askyesno
from PIL import Image, ImageDraw
from app import db
from app.jira_client import test_credentials, fetch_board_members
from app.ui.scroll_fix import apply as apply_scroll

TOKENS = [
    {"key": "ATLASSIAN_EMAIL",     "label": "Atlassian Email",     "env": "ATLASSIAN_EMAIL",
     "hint": "your@email.com", "secret": False},
    {"key": "ATLASSIAN_API_TOKEN", "label": "Atlassian API Token", "env": "ATLASSIAN_API_TOKEN",
     "hint": "ATATT3x…",       "secret": True},
]
BOARD_URL_KEY = "JIRA_BOARD_URL"


def _make_circular_avatar(path: str, size: int = 32) -> ctk.CTkImage | None:
    try:
        img = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception:
        return None


class SettingsTab(ctk.CTkFrame):
    def __init__(self, parent, on_participants_changed=None):
        super().__init__(parent, fg_color="transparent")
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._status_labels: dict[str, ctk.CTkLabel] = {}
        self._show_flags: dict[str, bool] = {}
        self._member_rows: dict[str, dict] = {}
        self._on_participants_changed = on_participants_changed  # called after Save Users
        self._build_ui()
        self._load_values()
        self._update_refresh_btn_state()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)   # left: credentials + board URL
        self.columnconfigure(1, weight=2)   # right: team members (wider)
        self.rowconfigure(0, weight=1)

        self._build_left_column()
        self._build_right_column()

    # ── Left column: credentials + board URL ─────────────────────────────────

    def _build_left_column(self) -> None:
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)  # spacer at bottom

        # Credentials panel
        creds = ctk.CTkFrame(left, fg_color=("gray92", "gray17"), corner_radius=10)
        creds.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        creds.columnconfigure(0, weight=1)

        ctk.CTkLabel(creds, text="🔑  Atlassian Credentials", font=("", 13, "bold")).pack(
            anchor="w", padx=16, pady=(14, 2)
        )
        ctk.CTkLabel(creds, text="Env vars (~/.zshrc) take precedence over stored values.",
                     font=("", 10), text_color="gray").pack(anchor="w", padx=16, pady=(0, 8))

        for token in TOKENS:
            self._build_token_row(creds, token)

        sep = ctk.CTkFrame(creds, height=1, fg_color="gray40")
        sep.pack(fill="x", padx=16, pady=(8, 8))

        btn_row = ctk.CTkFrame(creds, fg_color="transparent")
        btn_row.pack(anchor="w", padx=16, pady=(0, 14))
        ctk.CTkButton(btn_row, text="🔍 Test connection", width=170,
                      command=self._test_all).pack(side="left")
        self._test_result = ctk.CTkLabel(btn_row, text="", font=("", 11))
        self._test_result.pack(side="left", padx=10)

        # Board URL panel
        board = ctk.CTkFrame(left, fg_color=("gray92", "gray17"), corner_radius=10)
        board.grid(row=1, column=0, sticky="ew")
        board.columnconfigure(0, weight=1)

        ctk.CTkLabel(board, text="🎯  Board Filter URL", font=("", 13, "bold")).pack(
            anchor="w", padx=16, pady=(14, 2)
        )
        ctk.CTkLabel(
            board,
            text="Paste the Jira board URL. The ?label= param filters the team.",
            font=("", 10), text_color="gray", wraplength=300, justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 8))

        url_inner = ctk.CTkFrame(board, fg_color=("gray86", "gray22"), corner_radius=7)
        url_inner.pack(fill="x", padx=16, pady=(0, 4))

        er = ctk.CTkFrame(url_inner, fg_color="transparent")
        er.pack(fill="x", padx=12, pady=10)
        er.columnconfigure(0, weight=1)

        self._url_entry = ctk.CTkEntry(
            er, placeholder_text="https://…/boards/12345?label=polaris-squad",
            font=("", 11), height=30,
        )
        self._url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._url_entry.bind("<KeyRelease>", lambda e: self._update_refresh_btn_state())

        ctk.CTkButton(er, text="Save", width=60, height=30,
                      fg_color="#1a7a4a", hover_color="#145c36",
                      command=self._save_board_url).grid(row=0, column=1, padx=(0, 4))
        ctk.CTkButton(er, text="Clear", width=60, height=30,
                      fg_color="#7b2d2d", hover_color="#5a1f1f",
                      command=self._clear_board_url).grid(row=0, column=2)

        self._url_status = ctk.CTkLabel(url_inner, text="", font=("", 10), text_color="gray")
        self._url_status.pack(anchor="w", padx=16, pady=(0, 6))

    # ── Right column: team members ────────────────────────────────────────────

    def _build_right_column(self) -> None:
        right = ctk.CTkFrame(self, fg_color=("gray92", "gray17"), corner_radius=10)
        right.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        # Header + buttons
        ctk.CTkLabel(right, text="👥  Team Members", font=("", 13, "bold")).grid(
            row=0, column=0, padx=16, pady=(14, 4), sticky="w"
        )

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="ew")

        self._btn_refresh = ctk.CTkButton(
            btn_row, text="🔄  Refresh Users", width=160,
            state="disabled", command=self._refresh_users,
        )
        self._btn_refresh.pack(side="left")

        self._save_users_btn = ctk.CTkButton(
            btn_row, text="💾  Save Selected", width=150,
            fg_color="#1a7a4a", hover_color="#145c36",
            state="disabled", command=self._save_users,
        )
        self._save_users_btn.pack(side="left", padx=8)

        self._refresh_status = ctk.CTkLabel(btn_row, text="", font=("", 11), text_color="gray")
        self._refresh_status.pack(side="left", padx=4)

        # Members scrollable list
        self._members_frame = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self._members_frame.grid(row=2, column=0, padx=12, pady=(0, 14), sticky="nsew")
        self._members_frame.columnconfigure(0, weight=1)

    def _build_token_row(self, parent, token: dict) -> None:
        key = token["key"]
        self._show_flags[key] = False

        frame = ctk.CTkFrame(parent, fg_color=("gray86", "gray22"), corner_radius=7)
        frame.pack(fill="x", padx=16, pady=4)

        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(hdr, text=token["label"], font=("", 12, "bold")).pack(side="left")
        env_val = os.environ.get(token["env"], "")
        ctk.CTkLabel(hdr, text="✓ from env" if env_val else "not in env",
                     font=("", 10), text_color="#27ae60" if env_val else "gray").pack(side="right")

        er = ctk.CTkFrame(frame, fg_color="transparent")
        er.pack(fill="x", padx=12, pady=(0, 4))
        er.columnconfigure(0, weight=1)

        entry = ctk.CTkEntry(er, placeholder_text=token["hint"],
                              show="●" if token["secret"] else "",
                              font=("", 11), height=30)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._entries[key] = entry

        col = 1
        if token["secret"]:
            ctk.CTkButton(er, text="👁", width=30, height=30,
                          fg_color="transparent", hover_color=("gray80","gray30"),
                          command=lambda k=key, e=entry: self._toggle_show(k, e)
                          ).grid(row=0, column=col, padx=(0,4)); col += 1

        ctk.CTkButton(er, text="Save", width=60, height=30,
                      fg_color="#1a7a4a", hover_color="#145c36",
                      command=lambda k=key, env=token["env"]: self._save_token(k, env)
                      ).grid(row=0, column=col, padx=(0,4)); col += 1
        ctk.CTkButton(er, text="Clear", width=60, height=30,
                      fg_color="#7b2d2d", hover_color="#5a1f1f",
                      command=lambda k=key, env=token["env"]: self._clear_token(k, env)
                      ).grid(row=0, column=col)

        status = ctk.CTkLabel(frame, text="", font=("", 10))
        status.pack(anchor="w", padx=12, pady=(0, 6))
        self._status_labels[key] = status

    # ── Token actions ─────────────────────────────────────────────────────────

    def _toggle_show(self, key, entry):
        self._show_flags[key] = not self._show_flags[key]
        entry.configure(show="" if self._show_flags[key] else "●")

    def _save_token(self, key, env_var):
        value = self._entries[key].get().strip()
        if not value:
            self._set_status(key, "⚠ Nothing to save", "orange"); return
        db.set_token(key, value)
        os.environ[env_var] = value
        self._set_status(key, "💾 Saved", "#27ae60")
        self._update_refresh_btn_state()

    def _clear_token(self, key, env_var):
        db.delete_token(key)
        os.environ.pop(env_var, None)
        self._entries[key].delete(0, "end")
        self._set_status(key, "🗑 Cleared", "gray")
        self._update_refresh_btn_state()

    def _set_status(self, key, text, color):
        lbl = self._status_labels.get(key)
        if lbl: lbl.configure(text=text, text_color=color)

    def _test_all(self):
        email = os.environ.get("ATLASSIAN_EMAIL","").strip()
        token = os.environ.get("ATLASSIAN_API_TOKEN","").strip()
        if not email or not token:
            self._test_result.configure(text="⚠ Set credentials first", text_color="orange"); return
        self._test_result.configure(text="⏳ Testing…", text_color="gray")

        def on_ok():
            self.after(0, lambda: (
                self._test_result.configure(text="✅ Connection OK", text_color="#27ae60"),
                self._set_status("ATLASSIAN_EMAIL",     "✅ Verified", "#27ae60"),
                self._set_status("ATLASSIAN_API_TOKEN", "✅ Verified", "#27ae60"),
            ))
        def on_error(msg):
            self.after(0, lambda: (
                self._test_result.configure(text=f"❌ {msg[:60]}", text_color="#e74c3c"),
                self._set_status("ATLASSIAN_EMAIL",     "❌ Failed", "#e74c3c"),
                self._set_status("ATLASSIAN_API_TOKEN", "❌ Failed", "#e74c3c"),
            ))
        test_credentials(email, token, on_ok=on_ok, on_error=on_error)

    # ── Board URL ─────────────────────────────────────────────────────────────

    def _save_board_url(self):
        url = self._url_entry.get().strip()
        if not url:
            self._url_status.configure(text="⚠ Enter a URL", text_color="orange"); return
        db.set_setting(BOARD_URL_KEY, url)
        os.environ[BOARD_URL_KEY] = url
        self._url_status.configure(text="💾 Saved", text_color="#27ae60")
        self._update_refresh_btn_state()

    def _clear_board_url(self):
        db.set_setting(BOARD_URL_KEY, "")
        os.environ.pop(BOARD_URL_KEY, None)
        self._url_entry.delete(0, "end")
        self._url_status.configure(text="🗑 Cleared", text_color="gray")
        self._update_refresh_btn_state()

    def _update_refresh_btn_state(self):
        email = os.environ.get("ATLASSIAN_EMAIL","").strip()
        token = os.environ.get("ATLASSIAN_API_TOKEN","").strip()
        url   = self._url_entry.get().strip() if hasattr(self, "_url_entry") else ""
        self._btn_refresh.configure(state="normal" if (email and token and url) else "disabled")

    # ── Refresh users ─────────────────────────────────────────────────────────

    def _refresh_users(self):
        url = self._url_entry.get().strip()
        if not url: return
        self._refresh_status.configure(text="⏳ Fetching…", text_color="gray")
        self._btn_refresh.configure(state="disabled")
        self._save_users_btn.configure(state="disabled")
        for w in self._members_frame.winfo_children():
            w.destroy()
        self._member_rows.clear()

        fetch_board_members(
            url,
            on_done=lambda members: self.after(0, lambda: self._render_members(members)),
            on_error=lambda err:    self.after(0, lambda: self._members_error(err)),
        )

    def _members_error(self, msg):
        self._refresh_status.configure(text=f"❌ {msg[:80]}", text_color="#e74c3c")
        self._btn_refresh.configure(state="normal")

    def _render_members(self, members: list[dict]):
        existing = {p.jira_account_id: p for p in db.get_all_participants() if p.jira_account_id}

        new_members     = [m for m in members if m["accountId"] not in existing]
        already_members = [m for m in members if m["accountId"] in existing]

        total_new = len(new_members)
        self._refresh_status.configure(
            text=f"✅ {len(members)} found — {total_new} new, {len(already_members)} already in DB",
            text_color="#27ae60",
        )
        self._btn_refresh.configure(state="normal")
        if total_new > 0:
            self._save_users_btn.configure(state="normal")

        # Fixed column widths — shared by header and every row
        COL_AVATAR  = 44
        COL_NAME    = 0   # expands
        COL_ADD     = 52
        COL_JEFAZO  = 72
        COL_STATUS  = 70

        # Column headers
        hdr = ctk.CTkFrame(self._members_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=4, pady=(4, 2))
        hdr.columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text="",          width=COL_AVATAR).grid(row=0, column=0)
        ctk.CTkLabel(hdr, text="Name",      font=("",11,"bold"), anchor="w").grid(row=0, column=1, sticky="w", padx=4)
        ctk.CTkLabel(hdr, text="Add ✚",     font=("",11), width=COL_ADD,    anchor="center").grid(row=0, column=2, padx=2)
        ctk.CTkLabel(hdr, text="Jefazo ⭐", font=("",11), width=COL_JEFAZO, anchor="center").grid(row=0, column=3, padx=2)
        ctk.CTkLabel(hdr, text="Status",    font=("",11), width=COL_STATUS,  anchor="center").grid(row=0, column=4, padx=(2,8))
        ctk.CTkFrame(self._members_frame, height=1, fg_color="gray40").pack(fill="x", padx=4, pady=(0,4))

        # Store column widths for rows
        self._col_widths = (COL_AVATAR, COL_ADD, COL_JEFAZO, COL_STATUS)

        # New members first — with checkboxes
        for m in new_members:
            self._render_member_row(m, in_db=False)

        # Already in DB — shown dimmed, no add checkbox
        if already_members:
            ctk.CTkLabel(self._members_frame, text="Already in DB",
                         font=("",10,"bold"), text_color="gray").pack(anchor="w", padx=8, pady=(8,2))
            ctk.CTkFrame(self._members_frame, height=1, fg_color="gray30").pack(fill="x", padx=4, pady=(0,4))
            for m in already_members:
                self._render_member_row(m, in_db=True)

        apply_scroll(self._members_frame)

    def _render_member_row(self, m: dict, in_db: bool) -> None:
        existing = {p.jira_account_id: p for p in db.get_all_participants() if p.jira_account_id}
        p_existing = existing.get(m["accountId"])
        COL_AVATAR, COL_ADD, COL_JEFAZO, COL_STATUS = getattr(self, "_col_widths", (44, 52, 72, 70))

        add_var    = ctk.BooleanVar(value=False)
        jefote_var = ctk.BooleanVar(value=p_existing.is_jefote if p_existing else False)

        row = ctk.CTkFrame(
            self._members_frame,
            fg_color=("gray84", "gray26") if in_db else "transparent",
            corner_radius=6,
        )
        row.pack(fill="x", padx=4, pady=2)
        row.columnconfigure(1, weight=1)

        # col 0 — Avatar
        av_lbl = ctk.CTkLabel(row, text="", width=COL_AVATAR)
        if m.get("avatarPath"):
            img = _make_circular_avatar(m["avatarPath"], 32)
            if img:
                av_lbl.configure(image=img)
                av_lbl._image = img
        av_lbl.grid(row=0, column=0, padx=(6, 2), pady=4)

        # col 1 — Name (expands)
        parts = m["displayName"].split()
        short = f"{parts[0]} {parts[1]}" if len(parts) >= 2 else m["displayName"]
        ctk.CTkLabel(row, text=short, anchor="w",
                     font=("",12), text_color="gray" if in_db else None).grid(
            row=0, column=1, sticky="ew", padx=4
        )

        # col 2 — Add checkbox (or spacer)
        if not in_db:
            def _on_toggle(av=add_var, jcb_ref=[None]):
                if jcb_ref[0]:
                    jcb_ref[0].configure(state="normal" if av.get() else "disabled")

            add_cb = ctk.CTkCheckBox(row, text="", variable=add_var,
                                      width=COL_ADD, command=_on_toggle)
            add_cb.grid(row=0, column=2, padx=2)
        else:
            ctk.CTkLabel(row, text="", width=COL_ADD).grid(row=0, column=2, padx=2)

        # col 3 — Jefazo checkbox
        jefote_cb = ctk.CTkCheckBox(row, text="", variable=jefote_var,
                                     width=COL_JEFAZO, state="disabled")
        jefote_cb.grid(row=0, column=3, padx=2)

        # Wire jefote enable/disable after both widgets exist
        if not in_db:
            def _on_toggle_wired(av=add_var, jcb=jefote_cb):
                jcb.configure(state="normal" if av.get() else "disabled")
            add_cb.configure(command=_on_toggle_wired)

        # col 4 — Status badge
        ctk.CTkLabel(row, text="✓ in DB" if in_db else "new", font=("",10),
                     text_color="#555" if in_db else "#d68910",
                     width=COL_STATUS, anchor="center").grid(row=0, column=4, padx=(2,8))

        aid = m["accountId"]
        self._member_rows[aid] = {
            "add_var": add_var, "jefote_var": jefote_var,
            "data": m, "in_db": in_db,
            "short_name": short, "existing": p_existing,
        }

    # ── Save users ────────────────────────────────────────────────────────────

    def _save_users(self):
        added = 0
        for aid, row in self._member_rows.items():
            if row["in_db"] or not row["add_var"].get():
                continue
            db.add_participant(
                row["short_name"], row["jefote_var"].get(),
                jira_account_id=aid,
                avatar_path=row["data"].get("avatarPath") or "",
            )
            added += 1

        if added:
            showinfo(self, "Saved", f"{added} user{'s' if added>1 else ''} added.")
            if self._on_participants_changed:
                self._on_participants_changed()
            self._refresh_users()
        else:
            showinfo(self, "Nothing to do", "Tick ✚ on users you want to add first.")

    # ── Load persisted values ─────────────────────────────────────────────────

    def _load_values(self) -> None:
        stored = db.get_all_tokens()
        for token in TOKENS:
            key, env_var = token["key"], token["env"]
            value = os.environ.get(env_var,"") or stored.get(key,"")
            if value:
                self._entries[key].delete(0,"end")
                self._entries[key].insert(0, value)
                if not os.environ.get(env_var):
                    os.environ[env_var] = value

        url = os.environ.get(BOARD_URL_KEY,"") or db.get_setting(BOARD_URL_KEY,"")
        if url:
            self._url_entry.delete(0,"end")
            self._url_entry.insert(0, url)
            if not os.environ.get(BOARD_URL_KEY):
                os.environ[BOARD_URL_KEY] = url
