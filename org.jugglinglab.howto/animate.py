# Animator activity — live siteswap view with shared app chrome.

import lvgl as lv
from mpos import Activity

from engine import JuggleEngine, RIGHT, LEFT
from i18n import get_lang, t
import ui as U

BALL_COLORS = (
    0xE05050,
    0x50B060,
    0x5080E0,
    0xE0C040,
    0xC060E0,
    0x40C0C0,
)


class Animator(Activity):
    def __init__(self):
        super().__init__()
        self.engine = None
        self.timer = None
        self.ball_objs = []
        self.arm_r = None
        self.arm_l = None
        self.title_lbl = None
        self.pattern_lbl = None
        self.play_btn = None
        self.play_lbl = None
        self._cw = 320
        self._ch = 180

    def onCreate(self):
        intent = self.getIntent()
        extras = intent.extras if intent else {}
        title = extras.get("title") or "Cascade"
        pattern = extras.get("pattern") or "3"
        bps = extras.get("bps")
        tip = extras.get("tip") or ""
        self._lang = extras.get("lang") or get_lang()
        try:
            bps = float(bps) if bps is not None else 3.0
        except (TypeError, ValueError):
            bps = 3.0

        screen = U.make_screen()

        # Top: Back | Pause | - | + (all controls in one strip)
        top = U.make_tab_bar(screen)
        U.make_tab_btn(
            top, t("back", self._lang), self._on_back, width_pct=26, active=True
        )
        self.play_btn, self.play_lbl = U.make_tab_btn(
            top, t("pause", self._lang), self._on_play, width_pct=36
        )
        U.make_tab_btn(top, "-", self._on_slower, width_pct=19)
        U.make_tab_btn(top, "+", self._on_faster, width_pct=19)

        # Compact title block under tabs (~40px used by bar)
        self.title_lbl = U.make_title(screen, y=44, font_size=14)
        self.title_lbl.set_text(title)

        self.pattern_lbl = U.make_subtitle(screen, y=62)
        self.pattern_lbl.set_text("%s  |  %.1f bps" % (pattern, bps))

        tip_h = 0
        if tip:
            tip_lbl = lv.label(screen)
            tip_lbl.set_text(tip)
            try:
                tip_lbl.set_long_mode(lv.label.LONG_MODE.DOT)
            except Exception:
                tip_lbl.set_long_mode(lv.label.LONG_MODE.SCROLL_CIRCULAR)
            tip_lbl.set_width(lv.pct(92))
            tip_lbl.set_style_text_color(lv.color_hex(U.MUTED), 0)
            tip_lbl.align(lv.ALIGN.TOP_MID, 0, 78)
            tip_h = 18

        # Stage fills remaining height to the bottom of the 240px screen
        stage_top = 78 + tip_h + 4
        # Assume ~240px display; leave 4px bottom pad
        stage = lv.obj(screen)
        stage.set_style_bg_color(lv.color_hex(U.PANEL), 0)
        stage.set_style_border_width(0, 0)
        stage.set_style_pad_all(0, 0)
        stage.set_style_radius(6, 0)
        stage.set_width(lv.pct(94))
        stage.set_height(240 - stage_top - 4)
        stage.align(lv.ALIGN.TOP_MID, 0, stage_top)
        stage.remove_flag(lv.obj.FLAG.SCROLLABLE)

        self.head_obj = lv.obj(stage)
        self.head_obj.set_size(18, 18)
        self.head_obj.set_style_radius(9, 0)
        self.head_obj.set_style_bg_color(lv.color_hex(0xD8DCE8), 0)
        self.head_obj.set_style_border_width(0, 0)

        self.body_line = lv.line(stage)
        self.body_line.set_style_line_width(3, 0)
        self.body_line.set_style_line_color(lv.color_hex(0xD8DCE8), 0)
        self.body_line.set_style_line_rounded(True, 0)

        self.arm_r = lv.line(stage)
        self.arm_r.set_style_line_width(3, 0)
        self.arm_r.set_style_line_color(lv.color_hex(0xD8DCE8), 0)
        self.arm_r.set_style_line_rounded(True, 0)

        self.arm_l = lv.line(stage)
        self.arm_l.set_style_line_width(3, 0)
        self.arm_l.set_style_line_color(lv.color_hex(0xD8DCE8), 0)
        self.arm_l.set_style_line_rounded(True, 0)

        self.hand_r = lv.obj(stage)
        self.hand_r.set_size(10, 10)
        self.hand_r.set_style_radius(5, 0)
        self.hand_r.set_style_bg_color(lv.color_hex(0xE8C080), 0)
        self.hand_r.set_style_border_width(0, 0)

        self.hand_l = lv.obj(stage)
        self.hand_l.set_size(10, 10)
        self.hand_l.set_style_radius(5, 0)
        self.hand_l.set_style_bg_color(lv.color_hex(0xE8C080), 0)
        self.hand_l.set_style_border_width(0, 0)

        self.stage = stage
        self._pattern = pattern
        self._bps = bps
        self._tip = tip
        self._stage_top = stage_top

        self.setContentView(screen)

    def onResume(self, screen):
        super().onResume(screen)
        self._ensure_engine()
        self._start_timer()

    def onPause(self, screen):
        self._stop_timer()
        super().onPause(screen)

    def onDestroy(self, screen):
        self._stop_timer()
        self.engine = None

    def _ensure_engine(self):
        # Fit stage to remaining screen height if display is not exactly 240.
        try:
            scr_h = self.stage.get_parent().get_height()
            if scr_h > 80:
                new_h = max(80, scr_h - self._stage_top - 4)
                if abs(new_h - self.stage.get_height()) > 2:
                    self.stage.set_height(new_h)
        except Exception:
            pass

        w = self.stage.get_width()
        h = self.stage.get_height()
        if w < 40:
            w = 300
        if h < 40:
            h = 140
        self._cw = w
        self._ch = h
        if self.engine is None:
            self.engine = JuggleEngine(
                self._pattern, bps=self._bps, width=w, height=h
            )
            self._make_balls(self.engine.num_balls)
        else:
            self.engine.width = w
            self.engine.height = h
            self.engine._layout()

    def _make_balls(self, n):
        for o in self.ball_objs:
            try:
                o.delete()
            except Exception:
                pass
        self.ball_objs = []
        r = 7
        for i in range(n):
            b = lv.obj(self.stage)
            b.set_size(r * 2, r * 2)
            b.set_style_radius(r, 0)
            color = BALL_COLORS[i % len(BALL_COLORS)]
            b.set_style_bg_color(lv.color_hex(color), 0)
            b.set_style_border_width(0, 0)
            b.remove_flag(lv.obj.FLAG.SCROLLABLE)
            self.ball_objs.append(b)

    def _start_timer(self):
        self._stop_timer()
        self.timer = lv.timer_create(self._on_tick, 33, None)

    def _stop_timer(self):
        if self.timer is not None:
            try:
                self.timer.delete()
            except Exception:
                pass
            self.timer = None

    def _on_tick(self, timer):
        if not self.has_foreground():
            return
        if self.engine is None:
            return
        st = self.engine.state_at()
        self._draw_state(st)

    def _set_line(self, line, x0, y0, x1, y1):
        try:
            line.set_points(
                [{"x": int(x0), "y": int(y0)}, {"x": int(x1), "y": int(y1)}], 2
            )
        except TypeError:
            line.set_points(
                [
                    lv.point_t({"x": int(x0), "y": int(y0)}),
                    lv.point_t({"x": int(x1), "y": int(y1)}),
                ],
                2,
            )

    def _draw_state(self, st):
        hx_r, hy_r = st["hands"][RIGHT]
        hx_l, hy_l = st["hands"][LEFT]
        bx, by = st["body"]
        hx, hy = st["head"]

        self.head_obj.set_pos(int(hx - 9), int(hy - 9))
        self._set_line(self.body_line, hx, hy + 9, bx, by + 20)
        shoulder_y = by - 5
        self._set_line(self.arm_r, bx + 6, shoulder_y, hx_r, hy_r)
        self._set_line(self.arm_l, bx - 6, shoulder_y, hx_l, hy_l)
        self.hand_r.set_pos(int(hx_r - 5), int(hy_r - 5))
        self.hand_l.set_pos(int(hx_l - 5), int(hy_l - 5))

        balls = st["balls"]
        for i, obj in enumerate(self.ball_objs):
            if i in balls:
                x, y = balls[i]
                obj.remove_flag(lv.obj.FLAG.HIDDEN)
                obj.set_pos(int(x - 7), int(y - 7))
            else:
                obj.add_flag(lv.obj.FLAG.HIDDEN)

    def _on_back(self):
        self.finish()

    def _on_play(self):
        if self.engine is None:
            return
        self.engine.toggle()
        if self.play_lbl:
            key = "pause" if self.engine.playing else "play"
            self.play_lbl.set_text(t(key, self._lang))

    def _on_slower(self):
        if self.engine is None:
            return
        self.engine.set_bps(self.engine.bps - 0.5)
        self._bps = self.engine.bps
        self.pattern_lbl.set_text("%s  |  %.1f bps" % (self._pattern, self._bps))

    def _on_faster(self):
        if self.engine is None:
            return
        self.engine.set_bps(self.engine.bps + 0.5)
        self._bps = self.engine.bps
        self.pattern_lbl.set_text("%s  |  %.1f bps" % (self._pattern, self._bps))
