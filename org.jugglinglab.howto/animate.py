# Animator activity — JL-style ClassicAvatar stick figure + TossPath view.

import lvgl as lv
from mpos import Activity

try:
    import math
except ImportError:
    import math

from engine import (
    JuggleEngine,
    RIGHT,
    LEFT,
    UPPER_ARM_LENGTH,
    LOWER_ARM_LENGTH,
)
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

_FIGURE = 0xD8DCE8
_HAND = 0xE8C080

# JL Avatar.JUGGLE_PLANE_OFFSET — hands sit in front of the torso. Without this
# depth term, 2D IK hits asin/tan singularities when the hand is under the
# shoulder and the elbow jumps wildly (especially the right arm).
_HAND_DEPTH_CM = 30.0


def _elbow(sx, sy, hx, hy, upper_len, lower_len, scale):
    """Two-bone IK matching JL Avatar.elbow (render space: +Y up, +Z depth)."""
    depth = _HAND_DEPTH_CM * scale
    # Screen (+y down) → render (+y up); hand has juggling-plane depth.
    s = (sx, -sy, 0.0)
    h = (hx, -hy, depth)
    dx = h[0] - s[0]
    dy = h[1] - s[1]
    dz = h[2] - s[2]
    D = math.sqrt(dx * dx + dy * dy + dz * dz)
    U = upper_len
    L = lower_len
    if D < 1e-6:
        return (sx, sy)
    if D > U + L - 1e-6:
        f = U / D
        return (sx + (hx - sx) * f, sy + (hy - sy) * f)

    uu_ll_dd = U * U + L * L - D * D
    radicand = (4.0 * U * U * L * L - uu_ll_dd * uu_ll_dd) / (4.0 * D * D)
    if radicand < 0.0:
        radicand = 0.0
    r = math.sqrt(radicand)
    along = math.sqrt(max(0.0, U * U - r * r)) / D
    # alpha from up-component (JL: asin(delta.y / D))
    alpha = math.asin(max(-1.0, min(1.0, dy / D)))
    # Keep tan(alpha) stable near vertical reaches
    ca = math.cos(alpha)
    if abs(ca) < 0.15:
        ca = 0.15 if ca >= 0.0 else -0.15
    ta = math.sin(alpha) / ca
    adj = 1.0 + r * ta / (along * D)
    # Clamp amplification so the elbow cannot flip across the torso
    if adj > 2.5:
        adj = 2.5
    elif adj < -1.5:
        adj = -1.5
    ex = s[0] + along * dx * adj
    ey_up = s[1] + along * dy - r * math.cos(alpha)
    # discard depth for 2D draw
    return (ex, -ey_up)


class Animator(Activity):
    def __init__(self):
        super().__init__()
        self.engine = None
        self.timer = None
        self.ball_objs = []
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

        top = U.make_tab_bar(screen)
        U.make_tab_btn(
            top, t("back", self._lang), self._on_back, width_pct=26, active=True
        )
        self.play_btn, self.play_lbl = U.make_tab_btn(
            top, t("pause", self._lang), self._on_play, width_pct=36
        )
        U.make_tab_btn(top, "-", self._on_slower, width_pct=19)
        U.make_tab_btn(top, "+", self._on_faster, width_pct=19)

        # Content row: left text (~1/3) | right stage (~2/3)
        content = lv.obj(screen)
        content.set_width(lv.pct(100))
        content.set_height(240 - U.TAB_H)
        content.align(lv.ALIGN.TOP_MID, 0, U.TAB_H)
        content.set_style_bg_opa(0, 0)
        content.set_style_border_width(0, 0)
        content.set_style_pad_all(4, 0)
        content.set_style_pad_column(6, 0)
        content.set_flex_flow(lv.FLEX_FLOW.ROW)
        content.set_flex_align(
            lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START
        )
        content.remove_flag(lv.obj.FLAG.SCROLLABLE)

        left = lv.obj(content)
        left.set_size(lv.pct(33), lv.pct(100))
        left.set_style_bg_opa(0, 0)
        left.set_style_border_width(0, 0)
        left.set_style_pad_all(2, 0)
        left.set_style_pad_row(4, 0)
        left.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        left.set_flex_align(
            lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START
        )
        left.add_flag(lv.obj.FLAG.SCROLLABLE)

        self.title_lbl = U.make_side_label(left, muted=False, font_size=14)
        self.title_lbl.set_text(title)

        self.pattern_lbl = U.make_side_label(left, muted=True, font_size=14)
        self.pattern_lbl.set_text("%s  |  %.1f bps" % (pattern, bps))

        if tip:
            tip_lbl = U.make_side_label(left, muted=True, font_size=14)
            tip_lbl.set_text(tip)

        stage = lv.obj(content)
        stage.set_style_bg_color(lv.color_hex(U.PANEL), 0)
        stage.set_style_border_width(0, 0)
        stage.set_style_pad_all(0, 0)
        stage.set_style_radius(6, 0)
        stage.set_size(lv.pct(67), lv.pct(100))
        try:
            stage.set_flex_grow(1)
        except Exception:
            pass
        stage.remove_flag(lv.obj.FLAG.SCROLLABLE)

        def _mk_line():
            ln = lv.line(stage)
            ln.set_style_line_width(3, 0)
            ln.set_style_line_color(lv.color_hex(_FIGURE), 0)
            ln.set_style_line_rounded(True, 0)
            return ln

        # Torso: two diagonals forming a shoulder–waist quad silhouette
        self.torso_l = _mk_line()
        self.torso_r = _mk_line()
        self.torso_top = _mk_line()
        self.torso_bot = _mk_line()

        self.head_obj = lv.obj(stage)
        self.head_obj.set_size(18, 18)
        self.head_obj.set_style_radius(9, 0)
        self.head_obj.set_style_bg_color(lv.color_hex(_FIGURE), 0)
        self.head_obj.set_style_border_width(0, 0)

        # Two-bone arms
        self.arm_ru = _mk_line()
        self.arm_rl = _mk_line()
        self.arm_lu = _mk_line()
        self.arm_ll = _mk_line()

        self.hand_r = lv.obj(stage)
        self.hand_r.set_size(10, 10)
        self.hand_r.set_style_radius(5, 0)
        self.hand_r.set_style_bg_color(lv.color_hex(_HAND), 0)
        self.hand_r.set_style_border_width(0, 0)

        self.hand_l = lv.obj(stage)
        self.hand_l.set_size(10, 10)
        self.hand_l.set_style_radius(5, 0)
        self.hand_l.set_style_bg_color(lv.color_hex(_HAND), 0)
        self.hand_l.set_style_border_width(0, 0)

        self.stage = stage
        self._content = content
        self._pattern = pattern
        self._bps = bps
        self._tip = tip

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
        # Content row sits under the tab bar; resize to actual screen height,
        # then let the stage fill the right column via flex.
        try:
            content = self._content
            scr_h = content.get_parent().get_height()
            if scr_h > 80:
                new_h = max(80, scr_h - U.TAB_H)
                if abs(new_h - content.get_height()) > 2:
                    content.set_height(new_h)
        except Exception:
            pass

        w = self.stage.get_width()
        h = self.stage.get_height()
        if w < 40:
            w = 200
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
        sr = st["shoulders"][RIGHT]
        sl = st["shoulders"][LEFT]
        wr = st["waist"][RIGHT]
        wl = st["waist"][LEFT]
        hx, hy = st["head"]
        scale = st.get("scale") or 1.0

        # Head
        self.head_obj.set_pos(int(hx - 9), int(hy - 9))

        # Torso quad: L-shoulder → R-shoulder → R-waist → L-waist
        self._set_line(self.torso_top, sl[0], sl[1], sr[0], sr[1])
        self._set_line(self.torso_r, sr[0], sr[1], wr[0], wr[1])
        self._set_line(self.torso_bot, wr[0], wr[1], wl[0], wl[1])
        self._set_line(self.torso_l, wl[0], wl[1], sl[0], sl[1])

        u_len = UPPER_ARM_LENGTH * scale
        l_len = LOWER_ARM_LENGTH * scale
        er = _elbow(sr[0], sr[1], hx_r, hy_r, u_len, l_len, scale)
        el = _elbow(sl[0], sl[1], hx_l, hy_l, u_len, l_len, scale)

        self._set_line(self.arm_ru, sr[0], sr[1], er[0], er[1])
        self._set_line(self.arm_rl, er[0], er[1], hx_r, hy_r)
        self._set_line(self.arm_lu, sl[0], sl[1], el[0], el[1])
        self._set_line(self.arm_ll, el[0], el[1], hx_l, hy_l)

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
