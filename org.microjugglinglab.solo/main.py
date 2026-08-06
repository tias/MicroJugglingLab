# Main menu — language tabs on top, then title + three How-To tracks.

from mpos import Activity, Intent

from i18n import LANGS, LANG_LABELS, get_lang, set_lang, t
from lessons import SECTIONS
from section import SectionLessons
import ui as U


class MainMenu(Activity):
    def __init__(self):
        super().__init__()
        self._title = None
        self._lang_btns = {}
        self._section_lbls = []
        self._section_btns = {}
        self._scroll = U.ScrollKeeper()

    def onCreate(self):
        get_lang()
        screen = U.make_screen()

        tab_bar = U.make_tab_bar(screen)
        self._lang_btns = {}
        for code in LANGS:
            btn, _lbl = U.make_tab_btn(
                tab_bar,
                LANG_LABELS[code],
                lambda c=code: self._on_lang(c),
                width_pct=33,
            )
            self._lang_btns[code] = btn

        self._title = U.make_title(screen)

        body = U.make_panel(screen, height_pct=68, scrollable=True)
        self._scroll.bind(body)
        self._section_lbls = []
        self._section_btns = {}
        first_row = None
        for section in SECTIONS:
            btn, lbl = U.make_row_btn(
                body,
                "",
                lambda sid=section["id"]: self._open_section(sid),
            )
            self._section_lbls.append((lbl, section))
            self._section_btns[section["id"]] = btn
            if first_row is None:
                first_row = btn

        self._scroll.set_default_row(first_row)
        self._refresh_texts()
        self.setContentView(screen)
        U.focus_widget(first_row)

    def onResume(self, screen):
        super().onResume(screen)
        self._refresh_texts()
        # After Back from a section, MPOS focus restore can scroll_to_view the
        # list to the wrong place — put scroll back and re-show the cursor.
        self._scroll.restore()

    def _on_lang(self, code):
        set_lang(code)
        self._refresh_texts()

    def _refresh_texts(self):
        lang = get_lang()
        if self._title:
            self._title.set_text(t("app_title", lang))

        for code, btn in self._lang_btns.items():
            U.set_tab_active(btn, code == lang)

        for lbl, section in self._section_lbls:
            key = section.get("title_key")
            if key:
                lbl.set_text(t(key, lang))
            else:
                from lessons import localize_section_title

                lbl.set_text(localize_section_title(section, lang))

    def _open_section(self, section_id):
        self._scroll.save(self._section_btns.get(section_id))
        intent = Intent(activity_class=SectionLessons)
        intent.putExtra("section_id", section_id)
        intent.putExtra("lang", get_lang())
        self.startActivity(intent)
