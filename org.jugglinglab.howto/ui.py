# Shared chrome: colors + layout helpers for a consistent app look.

import lvgl as lv

BG = 0x12161F
PANEL = 0x1A2030
BTN = 0x2A3348
TAB_IDLE = 0x252B38
ACCENT = 0x3A6EA5
TEXT = 0xF0F0F0
MUTED = 0x8890A0

TAB_H = 40
TITLE_Y = 52


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
    bar.set_style_bg_color(lv.color_hex(TAB_IDLE), 0)
    bar.set_style_border_width(0, 0)
    bar.set_style_radius(0, 0)
    bar.set_style_pad_all(0, 0)
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
    btn.set_style_bg_color(lv.color_hex(ACCENT if active else TAB_IDLE), 0)
    # Avoid click-focus so returning from a child activity does not
    # scroll_to_view a focused control inside a scrollable parent.
    try:
        btn.remove_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
    except Exception:
        pass
    if cb is not None:
        btn.add_event_cb(lambda e, c=cb: c(), lv.EVENT.CLICKED, None)
    lbl = lv.label(btn)
    lbl.set_text(text)
    lbl.center()
    return btn, lbl


def set_tab_active(btn, active):
    btn.set_style_bg_color(lv.color_hex(ACCENT if active else TAB_IDLE), 0)


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


def make_subtitle(parent, y=72):
    lbl = lv.label(parent)
    lbl.set_style_text_color(lv.color_hex(MUTED), 0)
    lbl.set_long_mode(lv.label.LONG_MODE.WRAP)
    lbl.set_width(lv.pct(92))
    lbl.align(lv.ALIGN.TOP_MID, 0, y)
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
    lbl.center()
    return btn, lbl
