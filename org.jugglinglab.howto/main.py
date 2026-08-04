# Main menu — language tabs on top, then title + three How-To tracks.

import lvgl as lv
from mpos import Activity, Intent

from i18n import LANGS, LANG_LABELS, get_lang, set_lang, t
from lessons import SECTIONS
from section import SectionLessons

_BG = 0x12161F
_PANEL = 0x1A2030
_ACCENT = 0x3A6EA5
_BTN = 0x2A3348
_TAB_IDLE = 0x252B38
_TEXT = 0xF0F0F0
_MUTED = 0x8890A0


class MainMenu(Activity):
    def __init__(self):
        super().__init__()
        self._title = None
        self._lang_btns = {}
        self._section_lbls = []

    def onCreate(self):
        get_lang()
        screen = lv.obj()
        screen.set_style_bg_color(lv.color_hex(_BG), 0)
        screen.set_style_pad_all(0, 0)

        # --- Language tabs (top) ---
        tab_bar = lv.obj(screen)
        tab_bar.set_size(lv.pct(100), 40)
        tab_bar.align(lv.ALIGN.TOP_MID, 0, 0)
        tab_bar.set_style_bg_color(lv.color_hex(_TAB_IDLE), 0)
        tab_bar.set_style_border_width(0, 0)
        tab_bar.set_style_radius(0, 0)
        tab_bar.set_style_pad_all(0, 0)
        tab_bar.set_flex_flow(lv.FLEX_FLOW.ROW)
        tab_bar.set_flex_align(
            lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        tab_bar.remove_flag(lv.obj.FLAG.SCROLLABLE)

        self._lang_btns = {}
        for code in LANGS:
            btn = lv.button(tab_bar)
            btn.set_size(lv.pct(33), 40)
            btn.set_style_radius(0, 0)
            btn.set_style_shadow_width(0, 0)
            btn.add_event_cb(
                lambda e, c=code: self._on_lang(c), lv.EVENT.CLICKED, None
            )
            lbl = lv.label(btn)
            lbl.set_text(LANG_LABELS[code])
            lbl.center()
            self._lang_btns[code] = btn

        # --- Title under tabs ---
        self._title = lv.label(screen)
        self._title.set_style_text_color(lv.color_hex(_TEXT), 0)
        try:
            self._title.set_style_text_font(lv.font_montserrat_16, 0)
        except Exception:
            pass
        self._title.align(lv.ALIGN.TOP_MID, 0, 52)

        # --- Three lesson tracks ---
        body = lv.obj(screen)
        body.set_size(lv.pct(94), lv.pct(68))
        body.align(lv.ALIGN.BOTTOM_MID, 0, -8)
        body.set_style_bg_color(lv.color_hex(_PANEL), 0)
        body.set_style_border_width(0, 0)
        body.set_style_radius(6, 0)
        body.set_style_pad_all(8, 0)
        body.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        body.set_flex_align(
            lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        body.remove_flag(lv.obj.FLAG.SCROLLABLE)

        self._section_lbls = []
        for section in SECTIONS:
            btn = lv.button(body)
            btn.set_size(lv.pct(100), 48)
            btn.set_style_bg_color(lv.color_hex(_BTN), 0)
            btn.add_event_cb(
                lambda e, sid=section["id"]: self._open_section(sid),
                lv.EVENT.CLICKED,
                None,
            )
            lbl = lv.label(btn)
            lbl.set_long_mode(lv.label.LONG_MODE.WRAP)
            lbl.set_width(lv.pct(90))
            lbl.center()
            self._section_lbls.append((lbl, section))

        self._refresh_texts()
        self.setContentView(screen)

    def onResume(self, screen):
        super().onResume(screen)
        self._refresh_texts()

    def _on_lang(self, code):
        set_lang(code)
        self._refresh_texts()

    def _refresh_texts(self):
        lang = get_lang()
        if self._title:
            self._title.set_text(t("app_title", lang))

        for code, btn in self._lang_btns.items():
            if code == lang:
                btn.set_style_bg_color(lv.color_hex(_ACCENT), 0)
            else:
                btn.set_style_bg_color(lv.color_hex(_TAB_IDLE), 0)

        for lbl, section in self._section_lbls:
            key = section.get("title_key")
            if key:
                lbl.set_text(t(key, lang))
            else:
                from lessons import localize_section_title

                lbl.set_text(localize_section_title(section, lang))

    def _open_section(self, section_id):
        intent = Intent(activity_class=SectionLessons)
        intent.putExtra("section_id", section_id)
        intent.putExtra("lang", get_lang())
        self.startActivity(intent)
