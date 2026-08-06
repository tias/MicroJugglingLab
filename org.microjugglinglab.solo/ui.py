# Shared chrome: colors + layout helpers for a consistent app look.

import lvgl as lv

try:
    from mpos import add_focus_highlight
except ImportError:
    add_focus_highlight = None

try:
    from mpos.ui.focus import enable_focus_borders
except ImportError:
    enable_focus_borders = None

BG = 0x12161F
PANEL = 0x1A2030
BTN = 0x2A3348
TAB_BAR = 0x252B38
TAB_IDLE = 0x2A3348
TAB_ACTIVE = 0x4A90D9
ACCENT = 0x3A6EA5
TEXT = 0xF0F0F0
MUTED = 0x8890A0

TAB_H = 32
TITLE_Y = 38
FOCUS_BORDER_W = 3


def _paint_focus_border(widget):
    if widget is None:
        return
    try:
        widget.set_style_border_color(lv.color_hex(TEXT), lv.PART.MAIN)
        widget.set_style_border_width(FOCUS_BORDER_W, lv.PART.MAIN)
    except Exception:
        try:
            widget.set_style_border_color(lv.color_hex(TEXT), 0)
            widget.set_style_border_width(FOCUS_BORDER_W, 0)
        except Exception:
            pass


def _enable_focus_cursor(widget):
    """MPOS keypad/joystick focus ring (visible after directional navigation)."""
    if add_focus_highlight is None:
        return
    try:
        add_focus_highlight(
            widget, width=FOCUS_BORDER_W, color=lv.color_hex(TEXT), radius=0
        )
    except Exception:
        pass


def show_focus_cursor(widget=None):
    """Put keypad focus on `widget` and paint the ring.

    When `widget` is given it always wins (do not keep a stray top-bar focus).
    When omitted, uses the group's current focused object.
    """
    if enable_focus_borders is not None:
        try:
            enable_focus_borders()
        except Exception:
            pass
    if widget is None:
        try:
            group = lv.group_get_default()
            widget = group.get_focused() if group else None
        except Exception:
            widget = None
    if widget is None:
        return
    try:
        lv.group_focus_obj(widget)
    except Exception:
        pass
    _paint_focus_border(widget)


def focus_widget(widget):
    """Focus widget and show the keypad cursor immediately (cold start)."""
    show_focus_cursor(widget)


class ScrollKeeper:
    """Remember list scroll + which body row to focus across child activities.

    On Back: restore scroll and force focus onto the previously selected
    non-top-bar row (or the screen's default first row). MPOS often leaves
    focus on a top-bar control; we override that.
    """

    def __init__(self):
        self.body = None
        self.y = 0
        self._timer = None
        self._focus_row = None
        self._default_row = None

    def bind(self, body, default_row=None):
        self.body = body
        self.y = 0
        self._focus_row = None
        self._default_row = default_row

    def set_default_row(self, row):
        self._default_row = row

    def save(self, focus_row=None):
        if focus_row is not None:
            self._focus_row = focus_row
        if self.body is None:
            return
        try:
            self.y = self.body.get_scroll_y()
        except Exception:
            self.y = 0

    def restore(self):
        self._apply()
        self._cancel_timer()
        try:
            self._timer = lv.timer_create(self._deferred, 80, None)
            self._timer.set_repeat_count(1)
        except Exception:
            self._timer = None

    def _target_row(self):
        return self._focus_row if self._focus_row is not None else self._default_row

    def _apply(self):
        if self.body is None:
            return
        try:
            self.body.scroll_to_y(self.y, False)
        except Exception:
            pass
        show_focus_cursor(self._target_row())

    def _deferred(self, _t):
        self._timer = None
        self._apply()

    def _cancel_timer(self):
        if self._timer is None:
            return
        try:
            self._timer.delete()
        except Exception:
            pass
        self._timer = None


def make_screen():
    screen = lv.obj()
    screen.set_style_bg_color(lv.color_hex(BG), 0)
    screen.set_style_pad_all(0, 0)
    screen.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return screen


def make_tab_bar(parent, align_bottom=False):
    bar = lv.obj(parent)
    bar.set_size(lv.pct(100), TAB_H)
    if align_bottom:
        bar.align(lv.ALIGN.BOTTOM_MID, 0, 0)
    else:
        bar.align(lv.ALIGN.TOP_MID, 0, 0)
    bar.set_style_bg_color(lv.color_hex(TAB_BAR), 0)
    bar.set_style_border_width(0, 0)
    bar.set_style_radius(0, 0)
    bar.set_style_pad_all(0, 0)
    bar.set_style_pad_row(0, 0)
    bar.set_style_pad_column(0, 0)
    bar.set_flex_flow(lv.FLEX_FLOW.ROW)
    bar.set_flex_align(
        lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
    )
    bar.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return bar


def make_tab_btn(bar, text, cb, width_pct=None, active=False):
    btn = lv.button(bar)
    if width_pct is not None:
        btn.set_size(lv.pct(width_pct), TAB_H)
    else:
        btn.set_size(lv.pct(100), TAB_H)
        try:
            btn.set_flex_grow(1)
        except Exception:
            pass
    btn.set_style_radius(0, 0)
    btn.set_style_shadow_width(0, 0)
    btn.set_style_pad_all(0, 0)
    # Avoid click-focus so returning from a child activity does not
    # scroll_to_view a focused control inside a scrollable parent.
    try:
        btn.remove_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
    except Exception:
        pass
    if cb is not None:
        btn.add_event_cb(lambda e, c=cb: c(), lv.EVENT.CLICKED, None)
    lbl = lv.label(btn)
    try:
        lbl.set_style_text_font(lv.font_montserrat_16, 0)
    except Exception:
        pass
    set_tab_label(lbl, text)
    lbl.center()
    set_tab_active(btn, active)
    _enable_focus_cursor(btn)
    return btn, lbl


def set_tab_label(lbl, text):
    """Set top-bar label text (normal i18n casing)."""
    lbl.set_text(str(text))


def set_tab_active(btn, active):
    # Fill + text only — border is reserved for the MPOS keypad focus cursor.
    btn.set_style_bg_color(lv.color_hex(TAB_ACTIVE if active else TAB_IDLE), 0)
    btn.set_style_border_width(0, 0)
    try:
        lbl = btn.get_child(0)
        if lbl is not None:
            lbl.set_style_text_color(
                lv.color_hex(TEXT if active else MUTED), 0
            )
    except Exception:
        pass


def make_title(parent, y=TITLE_Y, font_size=16):
    title = lv.label(parent)
    title.set_style_text_color(lv.color_hex(TEXT), 0)
    title.set_long_mode(lv.label.LONG_MODE.WRAP)
    title.set_width(lv.pct(92))
    try:
        if font_size >= 16:
            title.set_style_text_font(lv.font_montserrat_16, 0)
        else:
            title.set_style_text_font(lv.font_montserrat_14, 0)
    except Exception:
        pass
    title.align(lv.ALIGN.TOP_MID, 0, y)
    return title


def make_subtitle(parent, y=58):
    lbl = lv.label(parent)
    lbl.set_style_text_color(lv.color_hex(MUTED), 0)
    lbl.set_long_mode(lv.label.LONG_MODE.WRAP)
    lbl.set_width(lv.pct(92))
    lbl.align(lv.ALIGN.TOP_MID, 0, y)
    return lbl


def make_side_label(parent, muted=False, font_size=14):
    """Left-column label: full width, wrap, left-aligned (for side-by-side layouts)."""
    lbl = lv.label(parent)
    lbl.set_style_text_color(lv.color_hex(MUTED if muted else TEXT), 0)
    lbl.set_long_mode(lv.label.LONG_MODE.WRAP)
    lbl.set_width(lv.pct(100))
    try:
        if font_size >= 16:
            lbl.set_style_text_font(lv.font_montserrat_16, 0)
        else:
            lbl.set_style_text_font(lv.font_montserrat_14, 0)
    except Exception:
        pass
    try:
        lbl.set_style_text_align(lv.TEXT_ALIGN.LEFT, 0)
    except Exception:
        pass
    return lbl


def make_panel(parent, height_pct=68, bottom_margin=-8, scrollable=False):
    body = lv.obj(parent)
    body.set_size(lv.pct(94), lv.pct(height_pct))
    body.align(lv.ALIGN.BOTTOM_MID, 0, bottom_margin)
    body.set_style_bg_color(lv.color_hex(PANEL), 0)
    body.set_style_border_width(0, 0)
    body.set_style_radius(6, 0)
    body.set_style_pad_all(8, 0)
    body.set_style_pad_row(6, 0)
    body.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    if scrollable:
        body.set_flex_align(
            lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        body.add_flag(lv.obj.FLAG.SCROLLABLE)
    else:
        body.set_flex_align(
            lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        body.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return body


def make_row_btn(parent, text, cb, height=48):
    btn = lv.button(parent)
    btn.set_size(lv.pct(100), height)
    btn.set_style_bg_color(lv.color_hex(BTN), 0)
    try:
        btn.remove_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
    except Exception:
        pass
    if cb is not None:
        btn.add_event_cb(lambda e, c=cb: c(), lv.EVENT.CLICKED, None)
    lbl = lv.label(btn)
    lbl.set_text(text)
    lbl.set_long_mode(lv.label.LONG_MODE.WRAP)
    lbl.set_width(lv.pct(90))
    try:
        lbl.set_style_text_font(lv.font_montserrat_16, 0)
    except Exception:
        pass
    lbl.center()
    _enable_focus_cursor(btn)
    return btn, lbl
