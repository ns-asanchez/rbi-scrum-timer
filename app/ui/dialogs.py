"""Custom dialogs — in-window overlay that can never go behind the main window."""

import customtkinter as ctk


def _get_root(parent):
    """Walk up to the root CTk window."""
    w = parent
    while getattr(w, "master", None):
        w = w.master
    return w


def _overlay(parent, title: str, message: str, icon: str,
             buttons: list, wait: bool = True):
    """Draw a modal card on the root window. Blocks until dismissed if wait=True."""
    root = _get_root(parent)
    done = ctk.BooleanVar(master=root, value=False)
    result = [None]

    backdrop = ctk.CTkFrame(root, corner_radius=0)
    backdrop.configure(fg_color="#00000088")
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

    def _close(value=None):
        result[0] = value
        backdrop.destroy()
        done.set(True)

    for label, kw, value in buttons:
        ctk.CTkButton(btn_row, text=label, width=90,
                      command=lambda v=value: _close(v), **kw).pack(
            side="left", padx=6
        )

    backdrop.lift()

    if wait:
        root.wait_variable(done)

    return result[0]


def showinfo(parent, title: str, message: str) -> None:
    """Show an info overlay — blocks until OK is clicked."""
    _overlay(parent, title, message, "ℹ️", [("OK", {}, True)])


def showwarning(parent, title: str, message: str) -> None:
    """Show a warning overlay — blocks until OK is clicked."""
    _overlay(parent, title, message, "⚠️", [("OK", {}, True)])


def showerror(parent, title: str, message: str) -> None:
    """Show an error overlay — blocks until OK is clicked."""
    _overlay(parent, title, message, "❌",
             [("OK", {"fg_color": "#c0392b", "hover_color": "#922b21"}, True)])


def askyesno(parent, title: str, message: str) -> bool:
    """Show a Yes/No overlay — blocks and returns True if Yes."""
    result = _overlay(
        parent, title, message, "❓",
        [
            ("Yes", {"fg_color": "#c0392b", "hover_color": "#922b21"}, True),
            ("No",  {}, False),
        ],
    )
    return bool(result)
