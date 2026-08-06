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


def _elbow(sx, sy, hx, hy, upper_len, lower_len, scale, out):
    """Two-bone IK matching JL Avatar.elbow. Writes [ex, ey] into out."""
    depth = _HAND_DEPTH_CM * scale
    # Screen (+y down) → render (+y up); hand has juggling-plane depth.
    dx = hx - sx
    dy = (-hy) - (-sy)
    dz = depth
    D = math.sqrt(dx * dx + dy * dy + dz * dz)
    U = upper_len
    L = lower_len
    if D < 1e-6:
        out[0] = sx
        out[1] = sy
        return out
    if D > U + L - 1e-6:
        f = U / D
        out[0] = sx + (hx - sx) * f
        out[1] = sy + (hy - sy) * f
        return out

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
    out[0] = sx + along * dx * adj
    # discard depth for 2D draw; convert render +y up back to screen +y down
    out[1] = -((-sy) + along * dy - r * math.cos(alpha))
    return out


class Animator(Activity):
    def __init__(self):
        super().__init__()
        self.engine = None
        self.timer = None
        self.ball_objs = []
        self.title_lbl = None
        self.play_btn = None
        self.play_lbl = None
        self._cw = 320
        self._ch = 180
        # Reusable LVGL point buffers (avoid per-frame list/dict allocs)
        self._pt0 = {"x": 0, "y": 0}
        self._pt1 = {"x": 0, "y": 0}
        self._pts = [self._pt0, self._pt1]
        self._pts_t = None  # lv.point_t pair if dict form unsupported
        self._elbow_r = [0.0, 0.0]
        self._elbow_l = [0.0, 0.0]
        # Dirty caches: skip LVGL calls when int pixels unchanged
        self._line_xy = {}  # id(line) -> (x0, y0, x1, y1)
        self._pos_xy = {}  # id(obj) -> (x, y)
        self._ball_vis = []  # last HIDDEN state per ball
        self._torso_drawn = False

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
        back_btn, _back_lbl = U.make_tab_btn(
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
        try:
            stage.remove_flag(lv.obj.FLAG.CLICKABLE)
            stage.remove_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
        except Exception:
            pass

        def _mk_line():
            ln = lv.line(stage)
            ln.set_style_line_width(3, 0)
            ln.set_style_line_color(lv.color_hex(_FIGURE), 0)
            ln.set_style_line_rounded(True, 0)
            try:
                ln.remove_flag(lv.obj.FLAG.CLICKABLE)
            except Exception:
                pass
            return ln

        def _decor_obj(size, radius, color):
            o = lv.obj(stage)
            o.set_size(size, size)
            o.set_style_radius(radius, 0)
            o.set_style_bg_color(lv.color_hex(color), 0)
            o.set_style_border_width(0, 0)
            try:
                o.remove_flag(lv.obj.FLAG.CLICKABLE)
                o.remove_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
                o.remove_flag(lv.obj.FLAG.SCROLLABLE)
            except Exception:
                pass
            return o

        # Torso: two diagonals forming a shoulder–waist quad silhouette
        self.torso_l = _mk_line()
        self.torso_r = _mk_line()
        self.torso_top = _mk_line()
        self.torso_bot = _mk_line()

        self.head_obj = _decor_obj(18, 9, _FIGURE)

        # Two-bone arms
        self.arm_ru = _mk_line()
        self.arm_rl = _mk_line()
        self.arm_lu = _mk_line()
        self.arm_ll = _mk_line()

        self.hand_r = _decor_obj(10, 5, _HAND)
        self.hand_l = _decor_obj(10, 5, _HAND)

        self.stage = stage
        self._content = content
        self._pattern = pattern
        self._bps = bps
        self._tip = tip

        self.setContentView(screen)
        # Animator special case: start focus on Back for quick exit.
        U.focus_widget(back_btn)

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
        size_changed = abs(w - self._cw) > 1 or abs(h - self._ch) > 1
        self._cw = w
        self._ch = h
        if self.engine is None:
            self.engine = JuggleEngine(
                self._pattern, bps=self._bps, width=w, height=h
            )
            self._make_balls(self.engine.num_balls)
            self._invalidate_static()
        elif size_changed:
            self.engine.width = w
            self.engine.height = h
            self.engine._layout()
            self._invalidate_static()
        if not self._torso_drawn:
            self._draw_torso_static()

    def _invalidate_static(self):
        """Layout/body changed — redraw torso once and clear dirty caches."""
        self._torso_drawn = False
        self._line_xy.clear()
        self._pos_xy.clear()
        self._ball_vis = [None] * len(self.ball_objs)

    def _make_balls(self, n):
        for o in self.ball_objs:
            try:
                o.delete()
            except Exception:
                pass
        self.ball_objs = []
        self._ball_vis = []
        r = 7
        for i in range(n):
            b = lv.obj(self.stage)
            b.set_size(r * 2, r * 2)
            b.set_style_radius(r, 0)
            color = BALL_COLORS[i % len(BALL_COLORS)]
            b.set_style_bg_color(lv.color_hex(color), 0)
            b.set_style_border_width(0, 0)
            b.remove_flag(lv.obj.FLAG.SCROLLABLE)
            try:
                b.remove_flag(lv.obj.FLAG.CLICKABLE)
                b.remove_flag(lv.obj.FLAG.CLICK_FOCUSABLE)
            except Exception:
                pass
            self.ball_objs.append(b)
            self._ball_vis.append(None)

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
        if not self._torso_drawn:
            self._draw_torso_static()
        self.engine.state_at()
        self._draw_moving()

    def _set_line(self, line, x0, y0, x1, y1):
        ix0, iy0, ix1, iy1 = int(x0), int(y0), int(x1), int(y1)
        key = id(line)
        prev = self._line_xy.get(key)
        if prev is not None and prev[0] == ix0 and prev[1] == iy0 and prev[2] == ix1 and prev[3] == iy1:
            return
        self._line_xy[key] = (ix0, iy0, ix1, iy1)
        if self._pts_t is not None:
            p0, p1 = self._pts_t
            p0.x = ix0
            p0.y = iy0
            p1.x = ix1
            p1.y = iy1
            line.set_points(self._pts_t, 2)
            return
        p0, p1 = self._pt0, self._pt1
        p0["x"] = ix0
        p0["y"] = iy0
        p1["x"] = ix1
        p1["y"] = iy1
        try:
            line.set_points(self._pts, 2)
        except TypeError:
            self._pts_t = [
                lv.point_t({"x": ix0, "y": iy0}),
                lv.point_t({"x": ix1, "y": iy1}),
            ]
            line.set_points(self._pts_t, 2)

    def _set_pos(self, obj, x, y):
        ix, iy = int(x), int(y)
        key = id(obj)
        prev = self._pos_xy.get(key)
        if prev is not None and prev[0] == ix and prev[1] == iy:
            return
        self._pos_xy[key] = (ix, iy)
        obj.set_pos(ix, iy)

    def _set_ball_vis(self, i, visible):
        if i < len(self._ball_vis) and self._ball_vis[i] == visible:
            return
        if i < len(self._ball_vis):
            self._ball_vis[i] = visible
        obj = self.ball_objs[i]
        if visible:
            obj.remove_flag(lv.obj.FLAG.HIDDEN)
        else:
            obj.add_flag(lv.obj.FLAG.HIDDEN)

    def _draw_torso_static(self):
        """Head + torso once after layout — not every animation tick."""
        e = self.engine
        if e is None:
            return
        sr = e.shoulders[RIGHT]
        sl = e.shoulders[LEFT]
        wr = e.waist[RIGHT]
        wl = e.waist[LEFT]
        hx, hy = e.head
        self._set_pos(self.head_obj, hx - 9, hy - 9)
        self._set_line(self.torso_top, sl[0], sl[1], sr[0], sr[1])
        self._set_line(self.torso_r, sr[0], sr[1], wr[0], wr[1])
        self._set_line(self.torso_bot, wr[0], wr[1], wl[0], wl[1])
        self._set_line(self.torso_l, wl[0], wl[1], sl[0], sl[1])
        self._torso_drawn = True

    def _draw_moving(self):
        """Arms, hands, balls — only LVGL updates when int pixels change."""
        e = self.engine
        hx_r = e._hand_x[RIGHT]
        hy_r = e._hand_y[RIGHT]
        hx_l = e._hand_x[LEFT]
        hy_l = e._hand_y[LEFT]
        sr = e.shoulders[RIGHT]
        sl = e.shoulders[LEFT]
        scale = e.scale or 1.0

        u_len = UPPER_ARM_LENGTH * scale
        l_len = LOWER_ARM_LENGTH * scale
        er = _elbow(sr[0], sr[1], hx_r, hy_r, u_len, l_len, scale, self._elbow_r)
        el = _elbow(sl[0], sl[1], hx_l, hy_l, u_len, l_len, scale, self._elbow_l)

        self._set_line(self.arm_ru, sr[0], sr[1], er[0], er[1])
        self._set_line(self.arm_rl, er[0], er[1], hx_r, hy_r)
        self._set_line(self.arm_lu, sl[0], sl[1], el[0], el[1])
        self._set_line(self.arm_ll, el[0], el[1], hx_l, hy_l)

        self._set_pos(self.hand_r, hx_r - 5, hy_r - 5)
        self._set_pos(self.hand_l, hx_l - 5, hy_l - 5)

        n = e.num_balls
        for i, obj in enumerate(self.ball_objs):
            if i < n and e._ball_on[i]:
                self._set_ball_vis(i, True)
                self._set_pos(obj, e._ball_x[i] - 7, e._ball_y[i] - 7)
            else:
                self._set_ball_vis(i, False)

    def _on_back(self):
        self.finish()

    def _on_play(self):
        if self.engine is None:
            return
        self.engine.toggle()
        if self.play_lbl:
            key = "pause" if self.engine.playing else "play"
            U.set_tab_label(self.play_lbl, t(key, self._lang))

    def _on_slower(self):
        if self.engine is None:
            return
        self.engine.set_playback_rate(self.engine.playback_rate - 0.25)

    def _on_faster(self):
        if self.engine is None:
            return
        self.engine.set_playback_rate(self.engine.playback_rate + 0.25)
