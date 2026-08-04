# Per-section lesson list in the active language.

import lvgl as lv
from mpos import Activity, Intent

from i18n import get_lang, t
from lessons import get_section, localize_lesson, localize_section_title
from animate import Animator

_BG = 0x12161F
_PANEL = 0x1A2030
_HDR = 0x2A3348
_TEXT = 0xF0F0F0
_MUTED = 0xC8D0E0


class SectionLessons(Activity):
    def onCreate(self):
        intent = self.getIntent()
        extras = intent.extras if intent else {}
        section_id = extras.get("section_id") or "cascade3"
        lang = extras.get("lang") or get_lang()

        section = get_section(section_id)
        if section is None:
            section = get_section("cascade3")

        screen = lv.obj()
        screen.set_style_bg_color(lv.color_hex(_BG), 0)

        title = lv.label(screen)
        title.set_text(localize_section_title(section, lang))
        title.set_style_text_color(lv.color_hex(_TEXT), 0)
        try:
            title.set_style_text_font(lv.font_montserrat_14, 0)
        except Exception:
            pass
        title.set_long_mode(lv.label.LONG_MODE.WRAP)
        title.set_width(lv.pct(92))
        title.align(lv.ALIGN.TOP_MID, 0, 6)

        back = lv.button(screen)
        back.set_size(80, 32)
        back.align(lv.ALIGN.TOP_LEFT, 6, 4)
        back.add_event_cb(lambda e: self.finish(), lv.EVENT.CLICKED, None)
        back_lbl = lv.label(back)
        back_lbl.set_text(t("back", lang))
        back_lbl.center()

        lst = lv.list(screen)
        lst.set_size(lv.pct(100), lv.pct(78))
        lst.align(lv.ALIGN.BOTTOM_MID, 0, 0)
        lst.set_style_bg_color(lv.color_hex(_PANEL), 0)
        lst.set_style_border_width(0, 0)
        lst.set_style_pad_row(2, 0)

        hdr = lst.add_button(None, t("lessons_header", lang))
        hdr.set_style_bg_color(lv.color_hex(_HDR), 0)
        hdr.set_style_text_color(lv.color_hex(_MUTED), 0)

        for lesson in section["lessons"]:
            loc = localize_lesson(lesson, lang)
            label = "%s  (%s)" % (loc["name"], loc["pattern"])
            btn = lst.add_button(None, label)
            btn.set_style_bg_color(lv.color_hex(_PANEL), 0)
            btn.set_style_text_color(lv.color_hex(_TEXT), 0)
            btn.add_event_cb(
                lambda e, les=lesson, lg=lang: self._open_lesson(les, lg),
                lv.EVENT.CLICKED,
                None,
            )

        self.setContentView(screen)

    def _open_lesson(self, lesson, lang):
        loc = localize_lesson(lesson, lang)
        intent = Intent(activity_class=Animator)
        intent.putExtra("title", loc["name"])
        intent.putExtra("pattern", loc["pattern"])
        intent.putExtra("bps", loc.get("bps", 3.0))
        intent.putExtra("tip", loc.get("tip", ""))
        intent.putExtra("lang", lang)
        self.startActivity(intent)
