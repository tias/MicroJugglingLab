# Per-section lesson list — same chrome as main menu.

import lvgl as lv
from mpos import Activity, Intent

from i18n import get_lang, t
from lessons import get_section, localize_lesson, localize_section_title
from animate import Animator
import ui as U


class SectionLessons(Activity):
    def __init__(self):
        super().__init__()
        self._scroll = U.ScrollKeeper()

    def onCreate(self):
        intent = self.getIntent()
        extras = intent.extras if intent else {}
        section_id = extras.get("section_id") or "cascade3"
        lang = extras.get("lang") or get_lang()

        section = get_section(section_id)
        if section is None:
            section = get_section("cascade3")

        screen = U.make_screen()

        tab_bar = U.make_tab_bar(screen)
        U.make_tab_btn(tab_bar, t("back", lang), self.finish, width_pct=100, active=True)

        title = U.make_title(screen)
        key = section.get("title_key")
        if key:
            title.set_text(t(key, lang))
        else:
            title.set_text(localize_section_title(section, lang))

        body = U.make_panel(screen, height_pct=68, scrollable=True)
        self._scroll.bind(body)
        first_row = None
        for lesson in section["lessons"]:
            loc = localize_lesson(lesson, lang)
            # Placeholder cb; wired below once btn exists.
            btn, _lbl = U.make_row_btn(body, loc["name"], None)
            btn.add_event_cb(
                lambda e, les=lesson, lg=lang, b=btn: self._open_lesson(les, lg, b),
                lv.EVENT.CLICKED,
                None,
            )
            if first_row is None:
                first_row = btn

        self._scroll.set_default_row(first_row)
        self.setContentView(screen)
        U.focus_widget(first_row)

    def onResume(self, screen):
        super().onResume(screen)
        # MPOS restores keypad focus after Back; that scroll_to_view's the
        # focused lesson and can yank the list. Put scroll back and re-show cursor.
        self._scroll.restore()

    def _open_lesson(self, lesson, lang, btn=None):
        self._scroll.save(btn)
        loc = localize_lesson(lesson, lang)
        intent = Intent(activity_class=Animator)
        intent.putExtra("title", loc["name"])
        intent.putExtra("pattern", loc["pattern"])
        intent.putExtra("bps", loc.get("bps", 3.0))
        intent.putExtra("tip", loc.get("tip", ""))
        intent.putExtra("lang", lang)
        self.startActivity(intent)
