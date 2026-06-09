"""Custom CTk dialogs — replaces tkinter.messagebox with native-looking popups."""
import customtkinter as ctk


def _base(parent, title: str, message: str, icon: str) -> ctk.CTkToplevel:
    d = ctk.CTkToplevel(parent)
    d.title(title)
    d.resizable(False, False)
    d.grab_set()
    d.lift()
    d.focus_force()
    # Center relative to parent
    d.update_idletasks()
    px = parent.winfo_rootx() + parent.winfo_width() // 2
    py = parent.winfo_rooty() + parent.winfo_height() // 2
    w, h = 360, 140
    d.geometry(f"{w}x{h}+{px - w//2}+{py - h//2}")
    # Icon + message on same row
    body = ctk.CTkFrame(d, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=20, pady=(18, 8))
    ctk.CTkLabel(body, text=icon, font=("", 22)).pack(side="left", padx=(0, 12), anchor="center")
    ctk.CTkLabel(body, text=message, font=("", 13), justify="left",
                 wraplength=280, anchor="w").pack(side="left", fill="both", expand=True)
    return d


def showinfo(parent, title: str, message: str) -> None:
    d = _base(parent, title, message, "ℹ️")
    ctk.CTkButton(d, text="OK", width=100, command=d.destroy).pack(pady=(0, 14))
    d.wait_window()


def showwarning(parent, title: str, message: str) -> None:
    d = _base(parent, title, message, "⚠️")
    ctk.CTkButton(d, text="OK", width=100, command=d.destroy).pack(pady=(0, 14))
    d.wait_window()


def showerror(parent, title: str, message: str) -> None:
    d = _base(parent, title, message, "❌")
    ctk.CTkButton(d, text="OK", width=100,
                  fg_color="#c0392b", hover_color="#922b21",
                  command=d.destroy).pack(pady=(0, 14))
    d.wait_window()


def askyesno(parent, title: str, message: str) -> bool:
    result = [False]
    d = _base(parent, title, message, "❓")
    btn_row = ctk.CTkFrame(d, fg_color="transparent")
    btn_row.pack(pady=(0, 14))
    def _yes():
        result[0] = True
        d.destroy()
    ctk.CTkButton(btn_row, text="Yes", width=90,
                  fg_color="#c0392b", hover_color="#922b21",
                  command=_yes).pack(side="left", padx=6)
    ctk.CTkButton(btn_row, text="No", width=90, command=d.destroy).pack(side="left", padx=6)
    d.wait_window()
    return result[0]
