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
_SCREEN_PEAK_Z_4 = 70.0
_LAYOUT_Z_MAX = 85.0
_SCREEN_TOP_MARGIN_PX = 6.0
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
    origin_y = stage_h * 0.78
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
        self.loop_ms = self.beat_ms
        self.warmup_ms = 0.0
        self._t0 = _now_ms()
        self._paused_at = None
        self._pause_accum = 0
        self.playing = True
        self._layout()
        self._build_schedule()

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
        self.origin_y = self.height * 0.78

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

    def set_bps(self, bps):
        self.bps = max(0.5, min(8.0, float(bps)))
        self.bps = _clamp_bps_for_screen(
            self.bps, self.beats, self.is_sync, self.dwell, self.height
        )
        self.beat_ms = 1000.0 / self.bps
        self._layout()
        self._build_schedule()
        self._t0 = _now_ms()
        self._pause_accum = 0
        self._paused_at = None
        if not self.playing:
            self._paused_at = self._t0

    def elapsed_ms(self):
        now = _now_ms()
        if self._paused_at is not None:
            return self._pause_accum + _diff_ms(self._t0, self._paused_at)
        return self._pause_accum + _diff_ms(self._t0, now)

    def play(self):
        if self.playing:
            return
        self._pause_accum = self.elapsed_ms()
        self._t0 = _now_ms()
        self._paused_at = None
        self.playing = True

    def pause(self):
        if not self.playing:
            return
        self._paused_at = _now_ms()
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

    def _build_schedule(self):
        period = len(self.beats)
        if period == 0:
            self.flights = []
            self.hand_segs = {RIGHT: [], LEFT: []}
            self.loop_ms = self.beat_ms
            self.warmup_ms = 0.0
            return

        cycles = max(48, 16 * period)
        flights = self._resimulate(cycles)
        self._apply_squeeze(flights)
        self._attach_paths(flights)
        self.flights = flights
        ids = set(f["ball"] for f in flights)
        if ids:
            self.num_balls = max(ids) + 1
        else:
            self.num_balls = max(1, average_balls(self.beats, self.is_sync))
        self._measure_seamless_loop()

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

    def _balls_cm_at(self, t_loop, hands_cm=None):
        """Labeled ball positions in cm at absolute schedule time t_loop."""
        if hands_cm is None:
            hands_cm = {
                RIGHT: self._hand_xz(RIGHT, t_loop),
                LEFT: self._hand_xz(LEFT, t_loop),
            }
        balls = {}
        for f in self.flights:
            b = f["ball"]
            t0, t1 = f["t0"], f["t1"]
            hold_until = f["hold_until"]
            if t_loop < t0:
                continue
            if t0 <= t_loop <= t1:
                t = (t_loop - t0) / 1000.0
                balls[b] = _toss_pos(f["toss"], t)
            elif t1 < t_loop <= hold_until:
                balls[b] = hands_cm[f["hand1"]]
        for bid in range(self.num_balls):
            if bid in balls:
                continue
            best = None
            for f in self.flights:
                if f["ball"] != bid:
                    continue
                if f["t1"] <= t_loop:
                    if best is None or f["t1"] > best["t1"]:
                        best = f
            if best is not None:
                balls[bid] = hands_cm[best["hand1"]]
            else:
                h = RIGHT if (bid % 2 == 0) else LEFT
                balls[bid] = hands_cm[h]
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
        hands = {
            RIGHT: self._hand_xz(RIGHT, t_loop),
            LEFT: self._hand_xz(LEFT, t_loop),
        }
        balls = {}
        for f in self.flights:
            b = f["ball"]
            if f["t0"] <= t_loop <= f["hold_until"]:
                balls[b] = True
        return len(balls) >= self.num_balls

    def _measure_seamless_loop(self):
        """Find warmup_ms + loop_ms so labeled state repeats (no teleport wrap)."""
        step = self._pair_ms()
        if step <= 0:
            self.warmup_ms = 0.0
            self.loop_ms = self.beat_ms
            return

        # Warmup: first time every ball is in play.
        warmup = 0.0
        max_t = 0.0
        for f in self.flights:
            if f["hold_until"] > max_t:
                max_t = f["hold_until"]
        probe = 0.0
        found_warm = False
        while probe <= max_t:
            if self._all_balls_present(probe):
                warmup = probe
                found_warm = True
                break
            probe += step * 0.25
        if not found_warm:
            warmup = step * float(self.num_balls)

        # Need warmup + loop well inside the schedule (leave ~2 periods of tail).
        period = max(1, len(self.beats))
        max_n = max(2 * self.num_balls * period, 4 * period, 12)
        margin = step * float(2 * period + 2)
        loop_ms = step * float(period)
        found = False
        for n in range(period, max_n + 1):
            cand = step * float(n)
            if warmup + cand + margin > max_t:
                break
            ok = True
            for i in range(5):
                tl = warmup + (0.15 + 0.17 * i) * cand
                if self._state_key(tl) != self._state_key(tl + cand):
                    ok = False
                    break
            if ok:
                loop_ms = cand
                found = True
                break
        if not found:
            # Fallback: 2*balls*period (odd async hand return) or 2*period.
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

        def emit_toss(hand_id, height, crossing, beat_t):
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
                }
            )
            release(dest, ball, land)

        hand = RIGHT
        for cycle in range(cycles):
            for bi, beat in enumerate(beats):
                gi = cycle * period + bi
                if self.is_sync:
                    # JL: each sync pair occupies 2 beat-index units at 1/bps each.
                    beat_t = gi * pair_ms
                    for hand_id, throws in ((RIGHT, beat[1]), (LEFT, beat[2])):
                        for height, crossing in throws:
                            if height == 0:
                                continue
                            if _is_hold_2(
                                height,
                                crossing,
                                beats,
                                True,
                                gi,
                                hand_id,
                                cycles_period,
                            ):
                                ball = acquire(hand_id, beat_t)
                                release(hand_id, ball, beat_t)
                                continue
                            emit_toss(hand_id, height, crossing, beat_t)
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
        segs = self.hand_segs.get(hand) or []
        for s in segs:
            if s["t0"] <= t_ms <= s["t1"]:
                t = (t_ms - s["t0"]) / 1000.0
                x = _eval_cubic(s["cx"], t)
                z = _eval_cubic(s["cz"], t)
                if z < _HAND_Z_MIN:
                    z = _HAND_Z_MIN
                elif z > _HAND_Z_MAX:
                    z = _HAND_Z_MAX
                return (x, z)
        return resting_xz(hand)

    def state_at(self, t_ms=None):
        if t_ms is None:
            t_ms = self.elapsed_ms()
        loop = self.loop_ms
        warm = getattr(self, "warmup_ms", 0.0)
        if loop > 0:
            t_loop = warm + (t_ms % loop)
        else:
            t_loop = t_ms

        hands_cm = {
            RIGHT: self._hand_xz(RIGHT, t_loop),
            LEFT: self._hand_xz(LEFT, t_loop),
        }
        balls = self._balls_cm_at(t_loop, hands_cm)

        balls_px = {}
        for bid, (x, z) in balls.items():
            balls_px[bid] = self.to_screen(x, z * _BALL_Z_BOOST)

        return {
            "balls": balls_px,
            "hands": {
                RIGHT: self.to_screen(*hands_cm[RIGHT]),
                LEFT: self.to_screen(*hands_cm[LEFT]),
            },
            "shoulders": self.shoulders,
            "waist": self.waist,
            "head": self.head,
            "body": self.body,
            "floor_y": self.floor_y,
            "t": t_ms,
            # cm scale so avatar IK uses matching arm lengths in px
            "scale": self.scale,
        }
