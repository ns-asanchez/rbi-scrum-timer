"""
Smooth scroll — macOS Tk9 trackpad.

Tk9 sends <TouchpadScroll> (unsigned 16-bit):
  fingers slide down (scroll down, content moves up):  delta > 65535
  fingers slide up   (scroll up,  content moves down): delta in [32768,65535]

We scroll 1 unit per event. The trackpad fires 10-60 events per gesture
so the result is smooth. yview_scroll(+1) = content moves up = scroll down.
"""
import customtkinter as ctk


def _direction(delta: int) -> int:
    """Return scroll direction: +1 = down (content up), -1 = up (content down)."""
    if delta > 65535:
        return -1   # fast gesture → up (natural scroll: fingers down = content down)
    if delta > 32767:
        return 1    # signed-negative range → down
    if delta > 0:
        return -1
    return 1


def apply(sf: ctk.CTkScrollableFrame) -> None:
    canvas = sf._parent_canvas

    def _scroll(event):
        canvas.yview_scroll(_direction(event.delta), "units")
        return "break"

    def _bind(widget):
        widget.bind("<TouchpadScroll>", _scroll, add="+")
        widget.bind("<MouseWheel>",     _scroll, add="+")
        for child in widget.winfo_children():
            _bind(child)

    canvas.bind("<TouchpadScroll>", _scroll, add="+")
    canvas.bind("<MouseWheel>",     _scroll, add="+")
    _bind(sf)
