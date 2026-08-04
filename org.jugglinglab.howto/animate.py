# Animator activity — live siteswap view for Fri3d Badge / MicroPythonOS.

import lvgl as lv
from mpos import Activity

from engine import JuggleEngine, RIGHT, LEFT

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
        try:
            bps = float(bps) if bps is not None else 3.0
        except (TypeError, ValueError):
            bps = 3.0

        screen = lv.obj()
        screen.set_style_bg_color(lv.color_hex(0x12161F), 0)

        self.title_lbl = lv.label(screen)
        self.title_lbl.set_text(title)
        self.title_lbl.set_style_text_color(lv.color_hex(0xF0F0F0), 0)
        self.title_lbl.align(lv.ALIGN.TOP_MID, 0, 4)
        try:
            self.title_lbl.set_style_text_font(lv.font_montserrat_14, 0)
        except Exception:
            pass

        self.pattern_lbl = lv.label(screen)
        self.pattern_lbl.set_text("%s  |  %.1f bps" % (pattern, bps))
        self.pattern_lbl.set_style_text_color(lv.color_hex(0xA0A8B8), 0)
        self.pattern_lbl.align(lv.ALIGN.TOP_MID, 0, 22)

        stage = lv.obj(screen)
        stage.set_style_bg_color(lv.color_hex(0x1A2030), 0)
        stage.set_style_border_width(0, 0)
        stage.set_style_pad_all(0, 0)
        stage.set_style_radius(0, 0)
        stage.align(lv.ALIGN.TOP_MID, 0, 40)
        stage.set_size(lv.pct(100), lv.pct(62))
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

        if tip:
            tip_lbl = lv.label(screen)
            tip_lbl.set_text(tip)
            tip_lbl.set_long_mode(lv.label.LONG_MODE.WRAP)
            tip_lbl.set_width(lv.pct(92))
            tip_lbl.set_style_text_color(lv.color_hex(0x8890A0), 0)
            tip_lbl.align(lv.ALIGN.BOTTOM_MID, 0, -48)

        bar = lv.obj(screen)
        bar.set_size(lv.pct(100), 44)
        bar.align(lv.ALIGN.BOTTOM_MID, 0, 0)
        bar.set_style_bg_color(lv.color_hex(0x0E1218), 0)
        bar.set_style_border_width(0, 0)
        bar.set_style_pad_all(4, 0)
        bar.set_flex_flow(lv.FLEX_FLOW.ROW)
        bar.set_flex_align(lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        bar.remove_flag(lv.obj.FLAG.SCROLLABLE)

        self._mk_btn(bar, "Back", self._on_back)
        self.play_btn = self._mk_btn(bar, "Pause", self._on_play)
        self.play_lbl = self.play_btn.get_child(0)
        self._mk_btn(bar, "-", self._on_slower)
        self._mk_btn(bar, "+", self._on_faster)

        self.setContentView(screen)

    def _mk_btn(self, parent, text, cb):
        btn = lv.button(parent)
        btn.set_size(70, 34)
        btn.add_event_cb(lambda e, c=cb: c(), lv.EVENT.CLICKED, None)
        lbl = lv.label(btn)
        lbl.set_text(text)
        lbl.center()
        return btn

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
        w = self.stage.get_width()
        h = self.stage.get_height()
        if w < 40:
            w = 320
        if h < 40:
            h = 180
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
            line.set_points([{"x": int(x0), "y": int(y0)}, {"x": int(x1), "y": int(y1)}], 2)
        except TypeError:
            line.set_points(
                [lv.point_t({"x": int(x0), "y": int(y0)}), lv.point_t({"x": int(x1), "y": int(y1)})],
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
            self.play_lbl.set_text("Pause" if self.engine.playing else "Play")

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
