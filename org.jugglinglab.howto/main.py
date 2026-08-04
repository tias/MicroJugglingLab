# Lesson list — launcher activity for Juggle How-To.

import lvgl as lv
from mpos import Activity, Intent

from lessons import SECTIONS
from animate import Animator


class LessonList(Activity):
    def onCreate(self):
        screen = lv.obj()
        screen.set_style_bg_color(lv.color_hex(0x12161F), 0)

        title = lv.label(screen)
        title.set_text("How to Juggle")
        title.set_style_text_color(lv.color_hex(0xF0F0F0), 0)
        try:
            title.set_style_text_font(lv.font_montserrat_16, 0)
        except Exception:
            pass
        title.align(lv.ALIGN.TOP_MID, 0, 6)

        subtitle = lv.label(screen)
        subtitle.set_text("Learn the steps - then juggle!")
        subtitle.set_style_text_color(lv.color_hex(0x8890A0), 0)
        subtitle.align(lv.ALIGN.TOP_MID, 0, 28)

        lst = lv.list(screen)
        lst.set_size(lv.pct(100), lv.pct(78))
        lst.align(lv.ALIGN.BOTTOM_MID, 0, 0)
        lst.set_style_bg_color(lv.color_hex(0x1A2030), 0)
        lst.set_style_border_width(0, 0)
        lst.set_style_pad_row(2, 0)

        for section in SECTIONS:
            # Section header as a non-clickable button look
            hdr = lst.add_button(None, section["title"])
            hdr.set_style_bg_color(lv.color_hex(0x2A3348), 0)
            hdr.set_style_text_color(lv.color_hex(0xC8D0E0), 0)
            try:
                hdr.set_style_text_font(lv.font_montserrat_12, 0)
            except Exception:
                pass
            # Disable click feedback by ignoring — still focusable; OK on small UI

            for lesson in section["lessons"]:
                label = "%s  (%s)" % (lesson["name"], lesson["pattern"])
                btn = lst.add_button(None, label)
                btn.set_style_bg_color(lv.color_hex(0x1A2030), 0)
                btn.set_style_text_color(lv.color_hex(0xE8ECF4), 0)
                btn.add_event_cb(
                    lambda e, les=lesson: self._open_lesson(les),
                    lv.EVENT.CLICKED,
                    None,
                )

        self.setContentView(screen)

    def _open_lesson(self, lesson):
        intent = Intent(activity_class=Animator)
        intent.putExtra("title", lesson["name"])
        intent.putExtra("pattern", lesson["pattern"])
        intent.putExtra("bps", lesson.get("bps", 3.0))
        intent.putExtra("tip", lesson.get("tip", ""))
        self.startActivity(intent)
