# Per-section lesson list — same chrome as main menu.

from mpos import Activity, Intent

from i18n import get_lang, t
from lessons import get_section, localize_lesson, localize_section_title
from animate import Animator
import ui as U


class SectionLessons(Activity):
    def __init__(self):
        super().__init__()
        self._body = None
        self._scroll_y = 0

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
        self._body = body
        self._scroll_y = 0
        for lesson in section["lessons"]:
            loc = localize_lesson(lesson, lang)
            label = "%s  (%s)" % (loc["name"], loc["pattern"])
            U.make_row_btn(
                body,
                label,
                lambda les=lesson, lg=lang: self._open_lesson(les, lg),
            )

        self.setContentView(screen)

    def onResume(self, screen):
        super().onResume(screen)
        # MPOS restores keypad focus after Back; that scroll_to_view's the
        # focused lesson and can yank the list to the bottom. Put scroll back.
        self._restore_scroll()

    def _save_scroll(self):
        if self._body is None:
            return
        try:
            self._scroll_y = self._body.get_scroll_y()
        except Exception:
            self._scroll_y = 0

    def _restore_scroll(self):
        if self._body is None:
            return
        try:
            self._body.scroll_to_y(self._scroll_y, False)
        except Exception:
            pass

    def _open_lesson(self, lesson, lang):
        self._save_scroll()
        loc = localize_lesson(lesson, lang)
        intent = Intent(activity_class=Animator)
        intent.putExtra("title", loc["name"])
        intent.putExtra("pattern", loc["pattern"])
        intent.putExtra("bps", loc.get("bps", 3.0))
        intent.putExtra("tip", loc.get("tip", ""))
        intent.putExtra("lang", lang)
        self.startActivity(intent)
