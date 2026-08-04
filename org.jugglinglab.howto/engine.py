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

    Async vanilla: the other hand throws on i+1, so this is false → hold-2.
    Sync (e.g. (2,2)): same hand throws every beat → toss-2.
    """
    period = len(beats)
    if period == 0:
        return False
    ni = beat_index + 1
    if ni >= cycles_period:
        return False
    if is_sync:
        beat = beats[ni % period]
        throws = beat[1] if hand_id == RIGHT else beat[2]
        for h, _c in throws:
            if h != 0:
                return True
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

    def __init__(self, pattern, bps=3.0, dwell=None, width=320, height=200):
        self.pattern = pattern
        self.bps = float(bps) if bps else 3.0
        self.dwell = float(dwell) if dwell is not None else _DWELL_DEFAULT
        self.width = width
        self.height = height
        self.beats, self.is_sync = parse_siteswap(pattern)
        self.beat_ms = 1000.0 / self.bps
        self.num_balls = max(1, average_balls(self.beats, self.is_sync))
        self.flights = []
        self.hand_segs = {RIGHT: [], LEFT: []}
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
        z_max = SHOULDER_H + NECK_H + HEAD_H + 8.0
        # Room for toss peaks (height-3 @ ~3 bps peaks ~40cm; leave headroom).
        if z_max < 85.0:
            z_max = 85.0
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
        self.beat_ms = 1000.0 / self.bps
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

    def _build_schedule(self):
        period = len(self.beats)
        if period == 0:
            self.flights = []
            self.hand_segs = {RIGHT: [], LEFT: []}
            self.loop_ms = self.beat_ms
            return

        cycles = 8
        flights = self._resimulate(cycles)
        self._attach_paths(flights)
        self.flights = flights
        self.loop_ms = period * self.beat_ms
        if self.is_sync:
            # Sync beats are spaced by one full beat_ms in our timeline base.
            self.loop_ms = period * self.beat_ms
        if self.loop_ms <= 0:
            self.loop_ms = self.beat_ms
        ids = set(f["ball"] for f in flights)
        if ids:
            self.num_balls = max(ids) + 1
        else:
            self.num_balls = max(1, average_balls(self.beats, self.is_sync))

    def _resimulate(self, cycles):
        beats = self.beats
        period = len(beats)
        cycles_period = cycles * period
        hands = {RIGHT: [], LEFT: []}
        next_ball = [0]
        flights = []

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

        hand = RIGHT
        for cycle in range(cycles):
            for bi, beat in enumerate(beats):
                gi = cycle * period + bi
                if self.is_sync:
                    unit = self.beat_ms / 2.0
                    t_ms = gi * self.beat_ms
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
                                # Hold: ball stays in hand; no TossPath flight.
                                ball = acquire(hand_id, t_ms)
                                release(hand_id, ball, t_ms)
                                continue
                            ball = acquire(hand_id, t_ms)
                            dest = (
                                hand_id
                                if not crossing
                                else (LEFT if hand_id == RIGHT else RIGHT)
                            )
                            air_ms = self._air_ms(height, unit)
                            land = t_ms + air_ms
                            flights.append(
                                {
                                    "ball": ball,
                                    "t0": t_ms,
                                    "t1": land,
                                    "hand0": hand_id,
                                    "hand1": dest,
                                    "height": height,
                                    "crossing": crossing,
                                }
                            )
                            release(dest, ball, land)
                else:
                    t_ms = gi * self.beat_ms
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
                            ball = acquire(hand, t_ms)
                            release(hand, ball, t_ms)
                            continue
                        ball = acquire(hand, t_ms)
                        dest = hand if not crossing else (LEFT if hand == RIGHT else RIGHT)
                        air_ms = self._air_ms(height, self.beat_ms)
                        land = t_ms + air_ms
                        flights.append(
                            {
                                "ball": ball,
                                "t0": t_ms,
                                "t1": land,
                                "hand0": hand,
                                "hand1": dest,
                                "height": height,
                                "crossing": crossing,
                            }
                        )
                        release(dest, ball, land)
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
                unit = self.beat_ms / 2.0 if self.is_sync else self.beat_ms
                hu = f["t1"] + self.dwell * unit
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
        if loop > 0:
            span = loop * 4
            if span > 0:
                t_loop = (t_ms % span) + loop
            else:
                t_loop = t_ms
        else:
            t_loop = t_ms

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
                x, z = _toss_pos(f["toss"], t)
                balls[b] = (x, z)
            elif t1 < t_loop <= hold_until:
                # Carry (includes JL hold-2 beats): ball follows catching hand
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
