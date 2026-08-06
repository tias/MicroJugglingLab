# Siteswap engine — JL-inspired motion (TossPath + hand Hermite carries).
# Units: centimeters and seconds in the juggling plane; screen map at the end.

try:
    import utime as time
except ImportError:
    import time


def _now_ms():
    try:
        return time.ticks_ms()
    except AttributeError:
        return int(time.time() * 1000)


def _diff_ms(start, end):
    try:
        return time.ticks_diff(end, start)
    except AttributeError:
        return end - start


def parse_siteswap(pattern):
    """Parse a siteswap string into beats.

    Returns (beats, is_sync).
    Async: each beat is a list of (height, crossing).
    Sync: each beat is ('sync', right_list, left_list).
    """
    s = pattern.strip().replace(" ", "")
    if not s:
        raise ValueError("empty pattern")

    beats = []
    i = 0
    n = len(s)
    is_sync = False

    def parse_throw_token(ch, crossing_force=None):
        if ch.isdigit():
            h = int(ch)
        elif "a" <= ch <= "z":
            h = 10 + (ord(ch) - ord("a"))
        elif "A" <= ch <= "Z":
            h = 10 + (ord(ch) - ord("A"))
        else:
            raise ValueError("bad throw %r" % ch)
        if crossing_force is not None:
            cross = crossing_force
        else:
            cross = (h % 2) == 1
        return (h, cross)

    def parse_hand_throws(text, start):
        j = start
        throws = []
        if j >= len(text):
            raise ValueError("unexpected end")
        if text[j] == "[":
            j += 1
            while j < len(text) and text[j] != "]":
                ch = text[j]
                j += 1
                cross_force = None
                if j < len(text) and text[j] == "x":
                    cross_force = True
                    j += 1
                throws.append(parse_throw_token(ch, cross_force))
            if j >= len(text) or text[j] != "]":
                raise ValueError("unclosed multiplex")
            j += 1
        else:
            ch = text[j]
            j += 1
            cross_force = None
            if j < len(text) and text[j] == "x":
                cross_force = True
                j += 1
            throws.append(parse_throw_token(ch, cross_force))
        return throws, j

    while i < n:
        if s[i] == "(":
            is_sync = True
            i += 1
            right, i = parse_hand_throws(s, i)
            if i >= n or s[i] != ",":
                raise ValueError("expected comma in sync")
            i += 1
            left, i = parse_hand_throws(s, i)
            if i >= n or s[i] != ")":
                raise ValueError("unclosed sync")
            i += 1
            if i < n and s[i] == "x":
                i += 1
            beats.append(("sync", right, left))
        else:
            throws, i = parse_hand_throws(s, i)
            beats.append(throws)

    if is_sync and any(not (isinstance(b, tuple) and b and b[0] == "sync") for b in beats):
        raise ValueError("mixed sync/async not supported")
    return beats, is_sync


def average_balls(beats, is_sync):
    total = 0
    units = 0
    for b in beats:
        if is_sync:
            _, right, left = b
            for h, _ in right + left:
                total += h
            units += 2
        else:
            for h, _ in b:
                total += h
            units += 1
    if units == 0:
        return 0
    return int(round(total / units))


RIGHT = 0
LEFT = 1

# Juggling Lab MhnPattern defaults (cm). Index by throw/catch value, capped at 8.
_SAME_THROW_X = (0.0, 20.0, 25.0, 12.0, 7.0, 7.5, 5.0, 5.0, 5.0)
_CROSS_THROW_X = (0.0, 17.0, 17.0, 7.0, 10.0, 14.0, 25.0, 24.0, 30.0)
_CATCH_X = (0.0, 17.0, 25.0, 30.0, 40.0, 45.0, 45.0, 50.0, 50.0)
_RESTING_X = 25.0
_G = 980.0  # CGS
_DWELL_DEFAULT = 1.3
_AIR_BEATS_MIN = 0.3
_SQUEEZEBEATS = 0.4  # JL MhnPattern default — stagger multi-catches on one beat
# JL throwsPerSec by throw height (MhnPattern); used for default bps.
_THROWS_PER_SEC = (2.0, 2.0, 2.0, 2.9, 3.4, 4.1, 4.25, 5.0, 5.0, 5.5)
_SECS_AIRTIME_MAX = 2.6
# Badge stage (~320×240): separate peak budgets for 4 vs 5+.
# Cascade-3 @ 3bps ~50cm boosted; 4s a bit above; 5s fill to the top of the frame
# at cascade figure scale (z_max=85).
_SCREEN_PEAK_Z_4 = 78.0
_LAYOUT_Z_MAX = 85.0
_SCREEN_TOP_MARGIN_PX = 6.0
# Hand plane (z=0) as fraction of stage height; higher = closer to bottom.
_ORIGIN_Y_FRAC = 0.87
# Hermite carry: match softcatch/throw tip speeds enough to dip, not overshoot.
_HAND_VEL_SCALE = 0.35
_HAND_VZ_SCALE = 0.40  # softcatch→throw cubic must dip and rise into the throw
_HAND_Z_MIN = -18.0
_HAND_Z_MAX = 10.0
# Slight visual lift so toss peaks clear the shoulders (hands stay unscaled).
_BALL_Z_BOOST = 1.28

# ClassicAvatar body (cm) — anchors for the avatar layer.
SHOULDER_HW = 23.0
SHOULDER_H = 40.0
WAIST_HW = 17.0
WAIST_H = -5.0
HEAD_HW = 10.0
HEAD_H = 26.0
NECK_H = 5.0
UPPER_ARM_LENGTH = 41.0
LOWER_ARM_LENGTH = 40.0


def _table_x(table, value):
    i = int(value)
    if i < 0:
        i = 0
    if i > 8:
        i = 8
    return table[i]


def _hand_sign(hand):
    return 1.0 if hand == RIGHT else -1.0


def throw_xz(hand, height, crossing):
    table = _CROSS_THROW_X if crossing else _SAME_THROW_X
    return (_hand_sign(hand) * _table_x(table, height), 0.0)


def catch_xz(hand, height):
    return (_hand_sign(hand) * _table_x(_CATCH_X, height), 0.0)


def resting_xz(hand):
    return (_hand_sign(hand) * _RESTING_X, 0.0)


def _next_beat_same_hand_has_real_throw(beats, is_sync, beat_index, hand_id, cycles_period):
    """JL resolveModifiers: look at th[hand][i+1] for a real (non-empty) throw.

    Async vanilla: the other hand throws on i+1 → false → hold-2.
    Sync: MHN advances 2 half-beats per pair, so i+1 is the empty half-beat → false → hold-2.
    """
    period = len(beats)
    if period == 0:
        return False
    if is_sync:
        # Next half-beat slot for this hand is empty inside the sync pair.
        return False
    ni = beat_index + 1
    if ni >= cycles_period:
        return False
    # Async: only the active hand has throws at ni. Starting RIGHT on even gi.
    active = RIGHT if (ni % 2) == 0 else LEFT
    if active != hand_id:
        return False
    for h, _c in beats[ni % period]:
        if h != 0:
            return True
    return False


def _is_hold_2(height, crossing, beats, is_sync, beat_index, hand_id, cycles_period):
    """JL: same-hand 2 is a hold unless beat i+1 for that hand has a real throw."""
    if height != 2 or crossing:
        return False
    return not _next_beat_same_hand_has_real_throw(
        beats, is_sync, beat_index, hand_id, cycles_period
    )


def _beats_one_throw_early(dwell):
    """JL: max(0, dwell + BEATS_AIRTIME_MIN - 1)."""
    early = dwell + _AIR_BEATS_MIN - 1.0
    if early < 0.0:
        return 0.0
    return early


def _max_throw_height(beats, is_sync):
    m = 0
    for b in beats:
        if is_sync:
            for h, _c in b[1] + b[2]:
                if h > m:
                    m = h
        else:
            for h, _c in b:
                if h > m:
                    m = h
    return m


def calc_bps(beats, is_sync, dwell=None):
    """JL MhnPattern.calcBps — default tempo from throw heights."""
    if dwell is None:
        dwell = _DWELL_DEFAULT
    total = 0.0
    n = 0
    max_h = 0
    for b in beats:
        throws = b[1] + b[2] if is_sync else b
        for h, _c in throws:
            if h > max_h:
                max_h = h
            if h > 2:
                i = h if h < 9 else 9
                total += _THROWS_PER_SEC[i]
                n += 1
    tps = (total / n) if n > 0 else 2.0
    max_flight = (max_h - dwell) / _SECS_AIRTIME_MAX if max_h > 0 else 0.0
    bps = tps if tps > max_flight else max_flight
    if bps < 0.5:
        bps = 0.5
    return bps


def _toss_peak_z(height, bps, dwell):
    """Parabola peak for a z0=z1=0 TossPath of duration (h-dwell)/bps."""
    air_beats = height - dwell
    if air_beats < _AIR_BEATS_MIN:
        air_beats = _AIR_BEATS_MIN
    T = air_beats / bps if bps > 0 else air_beats
    # z_max = g T^2 / 8 for throw/catch at z=0
    return (_G * T * T) / 8.0


def _top_of_frame_peak_z(stage_h):
    """Boosted cm peak that lands near the top of the stage at cascade framing."""
    z_min = WAIST_H - 8.0
    z_max = _LAYOUT_Z_MAX
    scale = (stage_h * 0.72) / (z_max - z_min)
    origin_y = stage_h * _ORIGIN_Y_FRAC
    peak = (origin_y - _SCREEN_TOP_MARGIN_PX) / scale
    if peak < _SCREEN_PEAK_Z_4:
        return _SCREEN_PEAK_Z_4
    return peak


def _peak_budget_cm(max_height, stage_h=200):
    if max_height >= 5:
        return _top_of_frame_peak_z(stage_h)
    return _SCREEN_PEAK_Z_4


def _bps_for_peak(max_height, dwell, peak_boosted):
    """bps so the highest toss's boosted peak equals peak_boosted cm."""
    if max_height <= 0:
        return 0.5
    air_beats = max_height - dwell
    if air_beats < _AIR_BEATS_MIN:
        air_beats = _AIR_BEATS_MIN
    tmax = (8.0 * peak_boosted / (_G * _BALL_Z_BOOST)) ** 0.5
    if tmax < 1e-6:
        return 8.0
    bps = air_beats / tmax
    if bps < 0.5:
        return 0.5
    if bps > 8.0:
        return 8.0
    return bps


def _clamp_bps_for_screen(bps, beats, is_sync, dwell, stage_h=200):
    """Fit height≥4 tosses to the badge stage (4s moderate; 5s to frame top)."""
    max_h = _max_throw_height(beats, is_sync)
    if max_h < 4:
        return bps
    target = _bps_for_peak(max_h, dwell, _peak_budget_cm(max_h, stage_h))
    if max_h >= 5:
        # Drive 5+ arcs to the top of the frame (not the cramped mid-height).
        return target
    if bps < target:
        return target
    return bps


def _hermite_coeffs(x0, v0, x1, v1, T):
    """Cubic Hermite on [0,T]: x(t)=a+bt+ct^2+dt^3 (JL SplineCurve form)."""
    if T <= 1e-9:
        return (x0, 0.0, 0.0, 0.0)
    a = x0
    b = v0
    c = (3.0 * (x1 - x0) - (v1 + 2.0 * v0) * T) / (T * T)
    d = (-2.0 * (x1 - x0) + (v1 + v0) * T) / (T * T * T)
    return (a, b, c, d)


def _eval_cubic(coeffs, t):
    a, b, c, d = coeffs
    return a + t * (b + t * (c + t * d))


def _toss_coeffs(x0, z0, x1, z1, T, g=_G):
    """TossPath coefficients; position (cx+bx*t, cz+t*(bz+az*t)), az=-g/2."""
    if T <= 1e-9:
        T = 1e-9
    az = -0.5 * g
    bx = (x1 - x0) / T
    bz = (z1 - z0) / T - az * T
    return {
        "cx": x0,
        "bx": bx,
        "cz": z0,
        "bz": bz,
        "az": az,
        "T": T,
        "x1": x1,
        "z1": z1,
    }


def _toss_pos(tc, t):
    return (
        tc["cx"] + tc["bx"] * t,
        tc["cz"] + t * (tc["bz"] + tc["az"] * t),
    )


def _toss_start_vel(tc):
    return (tc["bx"], tc["bz"])


def _toss_end_vel(tc):
    return (tc["bx"], tc["bz"] + 2.0 * tc["az"] * tc["T"])


class JuggleEngine:
    """Simulate siteswap; report ball/hand/body anchors in screen pixels."""

    def __init__(self, pattern, bps=None, dwell=None, width=320, height=200):
        self.pattern = pattern
        self.dwell = float(dwell) if dwell is not None else _DWELL_DEFAULT
        self.width = width
        self.height = height
        self.beats, self.is_sync = parse_siteswap(pattern)
        if bps is None or bps == "" or float(bps) <= 0:
            self.bps = calc_bps(self.beats, self.is_sync, self.dwell)
        else:
            self.bps = float(bps)
        self.bps = _clamp_bps_for_screen(
            self.bps, self.beats, self.is_sync, self.dwell, self.height
        )
        self.beat_ms = 1000.0 / self.bps
        self.num_balls = max(1, average_balls(self.beats, self.is_sync))
        self.flights = []
        self.hand_segs = {RIGHT: [], LEFT: []}
        self._flights_by_ball = []
        self.loop_ms = self.beat_ms
        self.warmup_ms = 0.0
        self.playback_rate = 1.0
        self._sim_at_anchor = 0.0
        self._t0 = _now_ms()
        self._paused_at = None
        self.playing = True
        self._layout()
        self._build_schedule()
        self._ensure_frame_bufs()

    def _ensure_frame_bufs(self):
        """Reusable per-frame output — avoids allocating every tick."""
        n = max(1, self.num_balls)
        if getattr(self, "_ball_x", None) is not None and len(self._ball_x) == n:
            return
        self._hand_x = [0.0, 0.0]
        self._hand_y = [0.0, 0.0]
        self._ball_x = [0.0] * n
        self._ball_y = [0.0] * n
        self._ball_on = [False] * n

    def _layout(self):
        """Body anchors in cm + affine map so the figure fills ~70% of the stage."""
        self.shoulder_cm = {
            RIGHT: (SHOULDER_HW, SHOULDER_H),
            LEFT: (-SHOULDER_HW, SHOULDER_H),
        }
        self.waist_cm = {
            RIGHT: (WAIST_HW, WAIST_H),
            LEFT: (-WAIST_HW, WAIST_H),
        }
        self.head_cm = (0.0, SHOULDER_H + NECK_H + HEAD_H * 0.5)

        z_min = WAIST_H - 8.0
        # Keep cascade-sized figure; 5-ball peaks use the space above to the frame top.
        z_max = _LAYOUT_Z_MAX
        x_half = 55.0

        scale_z = (self.height * 0.72) / (z_max - z_min)
        scale_x = (self.width * 0.85) / (2.0 * x_half)
        self.scale = min(scale_x, scale_z)
        self.origin_x = self.width * 0.5
        # z=0 (hands) sits in lower portion of the stage
        self.origin_y = self.height * _ORIGIN_Y_FRAC

        self.shoulders = {
            RIGHT: self.to_screen(*self.shoulder_cm[RIGHT]),
            LEFT: self.to_screen(*self.shoulder_cm[LEFT]),
        }
        self.waist = {
            RIGHT: self.to_screen(*self.waist_cm[RIGHT]),
            LEFT: self.to_screen(*self.waist_cm[LEFT]),
        }
        self.head = self.to_screen(*self.head_cm)
        sx = 0.5 * (self.shoulders[RIGHT][0] + self.shoulders[LEFT][0])
        sy = 0.5 * (self.shoulders[RIGHT][1] + self.shoulders[LEFT][1])
        self.body = (sx, sy)
        self.floor_y = self.origin_y + 6

    def to_screen(self, x, z):
        return (self.origin_x + x * self.scale, self.origin_y - z * self.scale)

    def _to_screen_xy(self, x, z):
        """Screen map without allocating a tuple."""
        return self.origin_x + x * self.scale, self.origin_y - z * self.scale

    def set_bps(self, bps):
        self.bps = max(0.5, min(8.0, float(bps)))
        self.bps = _clamp_bps_for_screen(
            self.bps, self.beats, self.is_sync, self.dwell, self.height
        )
        self.beat_ms = 1000.0 / self.bps
        self._layout()
        self._build_schedule()
        self._sim_at_anchor = 0.0
        self._t0 = _now_ms()
        self._paused_at = None
        if not self.playing:
            self._paused_at = self._t0

    def set_playback_rate(self, rate):
        """Scale animation speed only — does not change bps or throw height."""
        rate = max(0.25, min(2.0, float(rate)))
        self._sim_at_anchor = self.elapsed_ms()
        self._t0 = _now_ms()
        if self._paused_at is not None:
            self._paused_at = self._t0
        self.playback_rate = rate

    def elapsed_ms(self):
        now = _now_ms()
        if self._paused_at is not None:
            wall = _diff_ms(self._t0, self._paused_at)
        else:
            wall = _diff_ms(self._t0, now)
        return self._sim_at_anchor + wall * self.playback_rate

    def play(self):
        if self.playing:
            return
        self._sim_at_anchor = self.elapsed_ms()
        self._t0 = _now_ms()
        self._paused_at = None
        self.playing = True

    def pause(self):
        if not self.playing:
            return
        self._sim_at_anchor = self.elapsed_ms()
        self._t0 = _now_ms()
        self._paused_at = self._t0
        self.playing = False

    def toggle(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def _air_ms(self, height, unit_ms):
        air_beats = height - self.dwell
        if air_beats < _AIR_BEATS_MIN:
            air_beats = _AIR_BEATS_MIN
        return max(1.0, air_beats * unit_ms)

    def _pair_ms(self):
        """Time between consecutive sync pairs (JL: 2 half-beat units)."""
        return 2.0 * self.beat_ms if self.is_sync else self.beat_ms

    def _schedule_cycles(self):
        """Minimal pattern cycles to cover warmup + loop search (badge CPU/RAM)."""
        period = max(1, len(self.beats))
        balls = max(1, average_balls(self.beats, self.is_sync))
        max_h = max(1, _max_throw_height(self.beats, self.is_sync))
        # Beats/pairs needed: throw land + warmup + longest loop candidate + margin.
        loop_n = max(2 * balls * period, 4 * period, 24)
        need_steps = max_h + balls * period + loop_n + 2 * period + 2
        cycles = (need_steps + period - 1) // period
        if cycles < 4:
            cycles = 4
        if cycles > 20:
            cycles = 20
        return cycles

    def _build_schedule(self):
        period = len(self.beats)
        if period == 0:
            self.flights = []
            self.hand_segs = {RIGHT: [], LEFT: []}
            self._flights_by_ball = []
            self.loop_ms = self.beat_ms
            self.warmup_ms = 0.0
            return

        cycles = self._schedule_cycles()
        flights = self._resimulate(cycles)
        self._apply_squeeze(flights)
        self._attach_paths(flights)
        self.flights = flights
        ids = set(f["ball"] for f in flights)
        if ids:
            self.num_balls = max(ids) + 1
        else:
            self.num_balls = max(1, average_balls(self.beats, self.is_sync))
        self._index_flights()
        self._measure_seamless_loop()
        self._prune_to_loop()
        self._ensure_frame_bufs()
        try:
            import gc

            gc.collect()
        except ImportError:
            pass

    def _index_flights(self):
        """Per-ball flight lists sorted by t0 — avoids O(flights) scans every frame."""
        by = [[] for _ in range(self.num_balls)]
        for f in self.flights:
            b = f["ball"]
            if 0 <= b < self.num_balls:
                by[b].append(f)
        for lst in by:
            lst.sort(key=lambda f: f["t0"])
        self._flights_by_ball = by

    def _prune_to_loop(self):
        """Drop schedule outside the playback window to cut RAM and frame cost."""
        t0 = self.warmup_ms - 0.5
        t1 = self.warmup_ms + self.loop_ms + 0.5
        self.flights = [
            f
            for f in self.flights
            if f["hold_until"] >= t0 and f["t0"] <= t1
        ]
        for h in (RIGHT, LEFT):
            segs = self.hand_segs.get(h) or []
            self.hand_segs[h] = [
                s for s in segs if s["t1"] >= t0 and s["t0"] <= t1
            ]
        self._index_flights()

    def _apply_squeeze(self, flights):
        """JL squeezebeats: stagger N>1 airborne catches on the same hand/beat."""
        if not flights:
            return
        step = self._pair_ms()
        squeeze_ms = _SQUEEZEBEATS * self.beat_ms
        groups = {}
        for f in flights:
            # Bucket by catching hand and nominal catch beat.
            bi = int(round(f["t1"] / step)) if step > 0 else 0
            key = (f["hand1"], bi)
            groups.setdefault(key, []).append(f)
        for flist in groups.values():
            n = len(flist)
            if n < 2:
                continue
            flist.sort(key=lambda f: (f["height"], f["t0"], f["ball"]))
            for i, f in enumerate(flist):
                f["t1"] = f["t1"] + (i / float(n - 1)) * squeeze_ms

    def _ball_flight_at(self, bid, t_loop):
        """Rightmost flight for ball with t0 <= t_loop, or None."""
        flist = self._flights_by_ball[bid] if bid < len(self._flights_by_ball) else None
        if not flist:
            return None
        lo = 0
        hi = len(flist) - 1
        best = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if flist[mid]["t0"] <= t_loop:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best < 0:
            return None
        return flist[best]

    def _balls_cm_at(self, t_loop, hands_cm=None):
        """Labeled ball positions in cm at absolute schedule time t_loop."""
        if hands_cm is None:
            hands_cm = {
                RIGHT: self._hand_xz(RIGHT, t_loop),
                LEFT: self._hand_xz(LEFT, t_loop),
            }
        balls = {}
        for bid in range(self.num_balls):
            f = self._ball_flight_at(bid, t_loop)
            if f is None:
                h = RIGHT if (bid % 2 == 0) else LEFT
                balls[bid] = hands_cm[h]
                continue
            if t_loop <= f["t1"]:
                balls[bid] = _toss_pos(f["toss"], (t_loop - f["t0"]) / 1000.0)
            else:
                # In hold, or past hold until the next throw — stay on catch hand.
                balls[bid] = hands_cm[f["hand1"]]
        return balls

    def _state_key(self, t_loop):
        hands = {
            RIGHT: self._hand_xz(RIGHT, t_loop),
            LEFT: self._hand_xz(LEFT, t_loop),
        }
        balls = self._balls_cm_at(t_loop, hands)
        hk = tuple(round(v, 1) for h in (RIGHT, LEFT) for v in hands[h])
        bk = tuple(
            (bid, round(balls[bid][0], 1), round(balls[bid][1], 1))
            for bid in range(self.num_balls)
            if bid in balls
        )
        return hk + bk

    def _all_balls_present(self, t_loop):
        n = 0
        for bid in range(self.num_balls):
            f = self._ball_flight_at(bid, t_loop)
            if f is not None and f["t0"] <= t_loop <= f["hold_until"]:
                n += 1
        return n >= self.num_balls

    def _seg_at(self, hand, t_ms):
        """Hand Hermite segment covering t_ms, or None (binary search)."""
        segs = self.hand_segs.get(hand) or []
        if not segs:
            return None
        lo = 0
        hi = len(segs) - 1
        best = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if segs[mid]["t0"] <= t_ms:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best < 0:
            return None
        s = segs[best]
        if t_ms <= s["t1"]:
            return s
        return None

    def _hands_ready(self, t_loop):
        """True if every hand that has motion is on a Hermite seg (not pre-seg rest)."""
        for h in (RIGHT, LEFT):
            segs = self.hand_segs.get(h) or []
            if not segs:
                continue  # never moves — resting is correct
            if self._seg_at(h, t_loop) is None:
                return False
        return True

    def _steady_at(self, t_loop):
        return self._all_balls_present(t_loop) and self._hands_ready(t_loop)

    def _measure_seamless_loop(self):
        """Find warmup_ms + loop_ms so labeled state repeats (no teleport wrap)."""
        step = self._pair_ms()
        if step <= 0:
            self.warmup_ms = 0.0
            self.loop_ms = self.beat_ms
            return

        max_t = 0.0
        for f in self.flights:
            if f["hold_until"] > max_t:
                max_t = f["hold_until"]
        for h in (RIGHT, LEFT):
            for s in self.hand_segs.get(h) or []:
                if s["t1"] > max_t:
                    max_t = s["t1"]

        # Warmup: past startup so idle hands aren't still at pre-motion rest.
        warmup = 0.0
        found_warm = False
        probe = 0.0
        probe_step = step * 0.5
        while probe <= max_t:
            if self._steady_at(probe):
                warmup = probe
                found_warm = True
                break
            probe += probe_step
        if not found_warm:
            warmup = step * float(max(1, self.num_balls))

        period = max(1, len(self.beats))
        max_n = max(2 * self.num_balls * period, 4 * period, 24)
        margin = step * float(2 * period + 2)
        loop_ms = step * float(period)
        found = False
        # Labeled orbit length is a multiple of the siteswap period.
        for n in range(period, max_n + 1, period):
            cand = step * float(n)
            if warmup + cand + margin > max_t:
                break
            # Must match at the wrap point itself (d=0), not only mid-loop probes.
            ok = True
            for frac in (0.0, 0.25, 0.5, 0.75):
                tl = warmup + frac * cand
                if not self._steady_at(tl) or not self._steady_at(tl + cand):
                    ok = False
                    break
                if self._state_key(tl) != self._state_key(tl + cand):
                    ok = False
                    break
            if ok:
                loop_ms = cand
                found = True
                break
        if not found:
            n = 2 * max(1, self.num_balls) * period
            loop_ms = step * float(n)
            if warmup + loop_ms + margin > max_t:
                loop_ms = max(step, max_t - warmup - margin)

        self.warmup_ms = warmup
        self.loop_ms = max(step, loop_ms)

    def _resimulate(self, cycles):
        beats = self.beats
        period = len(beats)
        cycles_period = cycles * period
        hands = {RIGHT: [], LEFT: []}
        next_ball = [0]
        flights = []
        early_beats = _beats_one_throw_early(self.dwell)
        early_ms = early_beats * self.beat_ms
        pair_ms = self._pair_ms()

        def acquire(hand_id, t_ms):
            q = hands[hand_id]
            best_i = -1
            best_t = None
            for i, (avail, bid) in enumerate(q):
                if avail <= t_ms + 0.5:
                    if best_t is None or avail < best_t:
                        best_t = avail
                        best_i = i
            if best_i >= 0:
                _, bid = q.pop(best_i)
                return bid
            bid = next_ball[0]
            next_ball[0] += 1
            return bid

        def release(hand_id, ball, t_ms):
            hands[hand_id].append((t_ms, ball))

        def emit_toss(hand_id, height, crossing, beat_t, solo=False):
            if height == 1:
                t0 = beat_t - early_ms
            else:
                t0 = beat_t
            ball = acquire(hand_id, t0)
            dest = (
                hand_id
                if not crossing
                else (LEFT if hand_id == RIGHT else RIGHT)
            )
            air_ms = self._air_ms(height, self.beat_ms)
            land = t0 + air_ms
            flights.append(
                {
                    "ball": ball,
                    "t0": t0,
                    "t1": land,
                    "hand0": hand_id,
                    "hand1": dest,
                    "height": height,
                    "crossing": crossing,
                    "solo": solo,
                }
            )
            release(dest, ball, land)

        def sync_real_throws(throws, hand_id, gi, beat_t):
            out = []
            for height, crossing in throws:
                if height == 0:
                    continue
                if _is_hold_2(
                    height, crossing, beats, True, gi, hand_id, cycles_period
                ):
                    ball = acquire(hand_id, beat_t)
                    release(hand_id, ball, beat_t)
                    continue
                out.append((height, crossing))
            return out

        def side_empty(throws):
            """True only for a real empty (0) — hold-2 means a ball is still there."""
            return not any(h != 0 for h, _ in throws)

        hand = RIGHT
        for cycle in range(cycles):
            for bi, beat in enumerate(beats):
                gi = cycle * period + bi
                if self.is_sync:
                    # JL: each sync pair occupies 2 beat-index units at 1/bps each.
                    beat_t = gi * pair_ms
                    r_throws = sync_real_throws(beat[1], RIGHT, gi, beat_t)
                    l_throws = sync_real_throws(beat[2], LEFT, gi, beat_t)
                    # Center column only when the other hand is truly empty (0),
                    # not when it holds a 2 (tennis / yo-yo style).
                    solo_r = bool(r_throws) and side_empty(beat[2])
                    solo_l = bool(l_throws) and side_empty(beat[1])
                    for height, crossing in r_throws:
                        emit_toss(RIGHT, height, crossing, beat_t, solo=solo_r)
                    for height, crossing in l_throws:
                        emit_toss(LEFT, height, crossing, beat_t, solo=solo_l)
                else:
                    beat_t = gi * self.beat_ms
                    for height, crossing in beat:
                        if height == 0:
                            continue
                        if _is_hold_2(
                            height,
                            crossing,
                            beats,
                            False,
                            gi,
                            hand,
                            cycles_period,
                        ):
                            ball = acquire(hand, beat_t)
                            release(hand, ball, beat_t)
                            continue
                        emit_toss(hand, height, crossing, beat_t)
                    hand = LEFT if hand == RIGHT else RIGHT

        return flights

    def _attach_paths(self, flights):
        """TossPath coeffs, hold_until, and per-hand Hermite carry segments."""
        for f in flights:
            # JL same-hand: throw near midline, catch further out → circular fountain.
            x0, z0 = throw_xz(f["hand0"], f["height"], f["crossing"])
            x1, z1 = catch_xz(f["hand1"], f["height"])
            T = max(1e-4, (f["t1"] - f["t0"]) / 1000.0)
            f["x0"] = x0
            f["z0"] = z0
            f["x1"] = x1
            f["z1"] = z1
            f["toss"] = _toss_coeffs(x0, z0, x1, z1, T)

        # Only real tosses get throw/catch knots — hold-2s emit no events, so
        # softcatch of the prior toss Hermites straight into the next real throw
        # (dip then rise into the throw), matching JL layoutHandPaths.
        events = {RIGHT: [], LEFT: []}
        for f in flights:
            tc = f["toss"]
            svx, svz = _toss_start_vel(tc)
            evx, evz = _toss_end_vel(tc)
            events[f["hand0"]].append(
                {
                    "t": f["t0"],
                    "x": f["x0"],
                    "z": f["z0"],
                    "vx": svx * _HAND_VEL_SCALE,
                    "vz": svz * _HAND_VZ_SCALE,
                    "kind": "throw",
                }
            )
            events[f["hand1"]].append(
                {
                    "t": f["t1"],
                    "x": f["x1"],
                    "z": f["z1"],
                    "vx": evx * _HAND_VEL_SCALE,
                    "vz": evz * _HAND_VZ_SCALE,
                    "kind": "catch",
                }
            )

        for h in (RIGHT, LEFT):
            events[h].sort(key=lambda e: (e["t"], 0 if e["kind"] == "catch" else 1))

        # hold_until = next real throw from catching hand (spans hold-2 beats).
        throws_by_hand = {
            RIGHT: [e for e in events[RIGHT] if e["kind"] == "throw"],
            LEFT: [e for e in events[LEFT] if e["kind"] == "throw"],
        }
        for f in flights:
            hu = None
            for e in throws_by_hand[f["hand1"]]:
                if e["t"] > f["t1"] + 0.5:
                    hu = e["t"]
                    break
            if hu is None:
                hu = f["t1"] + self.dwell * self.beat_ms
            f["hold_until"] = hu

        segs = {RIGHT: [], LEFT: []}
        for h in (RIGHT, LEFT):
            evs = events[h]
            for i in range(len(evs) - 1):
                a = evs[i]
                b = evs[i + 1]
                dt_ms = b["t"] - a["t"]
                if dt_ms < 1.0:
                    continue
                T = dt_ms / 1000.0
                segs[h].append(
                    {
                        "t0": a["t"],
                        "t1": b["t"],
                        "cx": _hermite_coeffs(a["x"], a["vx"], b["x"], b["vx"], T),
                        "cz": _hermite_coeffs(a["z"], a["vz"], b["z"], b["vz"], T),
                    }
                )
        self.hand_segs = segs

    def _hand_xz(self, hand, t_ms):
        s = self._seg_at(hand, t_ms)
        if s is None:
            return resting_xz(hand)
        t = (t_ms - s["t0"]) / 1000.0
        x = _eval_cubic(s["cx"], t)
        z = _eval_cubic(s["cz"], t)
        if z < _HAND_Z_MIN:
            z = _HAND_Z_MIN
        elif z > _HAND_Z_MAX:
            z = _HAND_Z_MAX
        return (x, z)

    def state_at(self, t_ms=None):
        """Fill reusable frame buffers (hand_*/ball_*). Returns self — no per-tick dicts."""
        if t_ms is None:
            t_ms = self.elapsed_ms()
        self._ensure_frame_bufs()
        loop = self.loop_ms
        warm = getattr(self, "warmup_ms", 0.0)
        if loop > 0:
            t_loop = warm + (t_ms % loop)
        else:
            t_loop = t_ms

        ox, oy, sc = self.origin_x, self.origin_y, self.scale
        rx, rz = self._hand_xz(RIGHT, t_loop)
        lx, lz = self._hand_xz(LEFT, t_loop)
        self._hand_x[RIGHT] = ox + rx * sc
        self._hand_y[RIGHT] = oy - rz * sc
        self._hand_x[LEFT] = ox + lx * sc
        self._hand_y[LEFT] = oy - lz * sc

        n = self.num_balls
        for bid in range(n):
            self._ball_on[bid] = False
        for bid in range(n):
            f = self._ball_flight_at(bid, t_loop)
            if f is None:
                h = RIGHT if (bid % 2 == 0) else LEFT
                bx = rx if h == RIGHT else lx
                bz = rz if h == RIGHT else lz
            elif t_loop <= f["t1"]:
                bx, bz = _toss_pos(f["toss"], (t_loop - f["t0"]) / 1000.0)
            else:
                h = f["hand1"]
                bx = rx if h == RIGHT else lx
                bz = rz if h == RIGHT else lz
            self._ball_on[bid] = True
            self._ball_x[bid] = ox + bx * sc
            self._ball_y[bid] = oy - (bz * _BALL_Z_BOOST) * sc

        self._frame_t = t_ms
        return self
