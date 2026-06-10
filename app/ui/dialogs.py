"""Custom dialogs — in-window overlay for showinfo/showwarning/showerror.
askyesno uses a polled-topmost Toplevel since it needs a boolean result.
"""

import customtkinter as ctk


def _get_root(parent):
    """Walk up to the root CTk window."""
    w = parent
    while getattr(w, "master", None):
        w = w.master
    return w


def _overlay(parent, title: str, message: str, icon: str,
             buttons: list) -> None:
    """Draw a modal card directly on the root — cannot go behind main window."""
    root = _get_root(parent)

    backdrop = ctk.CTkFrame(root, corner_radius=0, fg_color="#00000099")
    backdrop.place(relx=0, rely=0, relwidth=1, relheight=1)

    card = ctk.CTkFrame(backdrop, fg_color=("gray92", "gray17"),
                        corner_radius=12, width=400, height=165)
    card.place(relx=0.5, rely=0.5, anchor="center")
    card.pack_propagate(False)

    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=20, pady=(18, 8))
    ctk.CTkLabel(body, text=icon, font=("", 22)).pack(
        side="left", padx=(0, 12), anchor="center"
    )
    inner = ctk.CTkFrame(body, fg_color="transparent")
    inner.pack(side="left", fill="both", expand=True)
    ctk.CTkLabel(inner, text=title, font=("", 13, "bold"), anchor="w").pack(fill="x")
    ctk.CTkLabel(inner, text=message, font=("", 12), justify="left",
                 wraplength=290, anchor="w", text_color="gray").pack(
        fill="x", pady=(4, 0)
    )

    btn_row = ctk.CTkFrame(card, fg_color="transparent")
    btn_row.pack(pady=(0, 14))

    def _close():
        backdrop.destroy()

    for label, kw, cb in buttons:
        def _click(c=cb):
            _close()
            if c:
                c()
        ctk.CTkButton(btn_row, text=label, width=90, command=_click, **kw).pack(
            side="left", padx=6
        )

    backdrop.lift()


def showinfo(parent, title: str, message: str) -> None:
    """Show an info overlay with OK button."""
    _overlay(parent, title, message, "ℹ️", [("OK", {}, None)])


def showwarning(parent, title: str, message: str) -> None:
    """Show a warning overlay with OK button."""
    _overlay(parent, title, message, "⚠️", [("OK", {}, None)])


def showerror(parent, title: str, message: str) -> None:
    """Show an error overlay with red OK button."""
    _overlay(parent, title, message, "❌",
             [("OK", {"fg_color": "#c0392b", "hover_color": "#922b21"}, None)])


def askyesno(parent, title: str, message: str) -> bool:
    """Show a Yes/No dialog. Uses a polled-topmost Toplevel to return a boolean."""
    result = [False]
    root = _get_root(parent)

    d = ctk.CTkToplevel(root)
    d.title(title)
    d.resizable(False, False)
    d.attributes("-topmost", True)
    d.grab_set()
    d.lift()
    d.focus_force()
    d.update_idletasks()
    w, h = 400, 150
    px = root.winfo_rootx() + root.winfo_width() // 2 - w // 2
    py = root.winfo_rooty() + root.winfo_height() // 2 - h // 2
    d.geometry(f"{w}x{h}+{px}+{py}")

    body = ctk.CTkFrame(d, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=20, pady=(18, 8))
    ctk.CTkLabel(body, text="❓", font=("", 22)).pack(
        side="left", padx=(0, 12), anchor="center"
    )
    inner = ctk.CTkFrame(body, fg_color="transparent")
    inner.pack(side="left", fill="both", expand=True)
    ctk.CTkLabel(inner, text=title, font=("", 13, "bold"), anchor="w").pack(fill="x")
    ctk.CTkLabel(inner, text=message, font=("", 12), justify="left",
                 wraplength=280, anchor="w", text_color="gray").pack(
        fill="x", pady=(4, 0)
    )

    btn_row = ctk.CTkFrame(d, fg_color="transparent")
    btn_row.pack(pady=(0, 14))

    def _yes():
        result[0] = True
        d.destroy()

    ctk.CTkButton(btn_row, text="Yes", width=90,
                  fg_color="#c0392b", hover_color="#922b21",
                  command=_yes).pack(side="left", padx=6)
    ctk.CTkButton(btn_row, text="No", width=90,
                  command=d.destroy).pack(side="left", padx=6)

    # Poll every 150ms to keep it on top while waiting for answer
    def _keep_top():
        if d.winfo_exists():
            try:
                d.lift()
                d.attributes("-topmost", True)
            except Exception:
                pass
            d.after(150, _keep_top)

    _keep_top()
    d.wait_window()
    return result[0]
