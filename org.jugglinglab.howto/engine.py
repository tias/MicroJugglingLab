# Lightweight siteswap engine for MicroPythonOS (async, sync, multiplex).
# Ballistic arcs between fixed hand positions — not a full Juggling Lab port.

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

    Each beat is a list of throws: (height, crossing) where crossing is True
    if the throw goes to the other hand (odd height or explicit 'x').
    Sync patterns alternate as both-hands beats: [('R', throws), ('L', throws)]
    stored as a single beat with key 'sync': (right_throws, left_throws).

    Returns (beats, is_sync) where beats is a list.
    For async: each item is a list of (height, crossing).
    For sync: each item is ('sync', right_list, left_list).
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
        """Parse throws for one hand: digit, digitx, or [multiplex]. Returns (list, new_index)."""
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
                # even throw with x = cross; odd with x is already cross
                cross_force = True
                j += 1
            throws.append(parse_throw_token(ch, cross_force))
        return throws, j

    while i < n:
        if s[i] == "(":
            is_sync = True
            i += 1
            # (right,left) or (left,right) — Juggling Lab / common: (R,L)
            right, i = parse_hand_throws(s, i)
            if i >= n or s[i] != ",":
                raise ValueError("expected comma in sync")
            i += 1
            left, i = parse_hand_throws(s, i)
            if i >= n or s[i] != ")":
                raise ValueError("unclosed sync")
            i += 1
            # optional trailing x on whole beat — ignore
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
    """Number of balls = sum(heights) / beats_per_cycle (time units)."""
    total = 0
    units = 0
    for b in beats:
        if is_sync:
            _, right, left = b
            for h, _ in right + left:
                total += h
            units += 2  # sync beat spans 2 async units
        else:
            for h, _ in b:
                total += h
            units += 1
    if units == 0:
        return 0
    return int(round(total / units))


# Hand indices
RIGHT = 0
LEFT = 1


class JuggleEngine:
    """Simulate siteswap and report ball/hand positions over time."""

    def __init__(self, pattern, bps=3.0, dwell=0.35, width=320, height=200):
        self.pattern = pattern
        self.bps = float(bps) if bps else 3.0
        self.dwell = float(dwell)
        self.width = width
        self.height = height
        self.beats, self.is_sync = parse_siteswap(pattern)
        self.beat_ms = 1000.0 / self.bps
        self.num_balls = max(1, average_balls(self.beats, self.is_sync))
        self._flights = []  # active/completed flight records for current window
        self._held = {}  # ball_id -> hand
        self._t0 = _now_ms()
        self._paused_at = None
        self._pause_accum = 0
        self.playing = True
        self._build_schedule()
        self._layout()

    def _layout(self):
        cx = self.width // 2
        hand_y = int(self.height * 0.78)
        spread = int(self.width * 0.18)
        self.hand_pos = {
            RIGHT: (cx + spread, hand_y),
            LEFT: (cx - spread, hand_y),
        }
        self.body = (cx, int(self.height * 0.55))
        self.head = (cx, int(self.height * 0.38))
        self.floor_y = hand_y + 8
        # max throw height in pattern for scaling
        max_h = 1
        for b in self.beats:
            if self.is_sync:
                for h, _ in b[1] + b[2]:
                    max_h = max(max_h, h)
            else:
                for h, _ in b:
                    max_h = max(max_h, h)
        self.max_h = max_h
        self.peak_scale = (self.height * 0.55) / max(3, max_h)

    def set_bps(self, bps):
        self.bps = max(0.5, min(8.0, float(bps)))
        self.beat_ms = 1000.0 / self.bps
        # rebuild with same pattern, keep playhead roughly
        t = self.elapsed_ms()
        self._build_schedule()
        # shift schedule so current elapsed maps similarly (restart from t=0 feel)
        self._t0 = _now_ms()
        self._pause_accum = 0
        self._paused_at = None
        if not self.playing:
            self._paused_at = self._t0
        # discard unused t — speed change restarts animation cleanly
        _ = t

    def elapsed_ms(self):
        now = _now_ms()
        if self._paused_at is not None:
            return self._pause_accum + _diff_ms(self._t0, self._paused_at)
        return self._pause_accum + _diff_ms(self._t0, now)

    def play(self):
        if self.playing:
            return
        # resume: move t0 so elapsed continues
        paused_for = _diff_ms(self._paused_at, _now_ms()) if self._paused_at else 0
        self._pause_accum = self.elapsed_ms()
        self._t0 = _now_ms()
        self._paused_at = None
        self.playing = True
        _ = paused_for

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

    def _build_schedule(self):
        """Precompute flights for several pattern cycles."""
        period = len(self.beats)
        if period == 0:
            self.flights = []
            self.loop_ms = self.beat_ms
            return

        cycles = 8
        flights = self._resimulate(cycles)
        self.flights = flights
        # One pattern cycle in ms (sync beats are spaced by beat_ms).
        self.loop_ms = period * self.beat_ms
        if self.loop_ms <= 0:
            self.loop_ms = self.beat_ms
        ids = set(f["ball"] for f in flights)
        if ids:
            self.num_balls = max(ids) + 1
        else:
            self.num_balls = max(1, average_balls(self.beats, self.is_sync))

    def _resimulate(self, cycles):
        """Causal ball assignment with hand occupancy timelines."""
        beats = self.beats
        period = len(beats)
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
                if self.is_sync:
                    # Sync unit = half an async beat; (4,4) lands after 4 units = 2 sync beats.
                    unit = self.beat_ms / 2.0
                    t_ms = (cycle * period + bi) * 2 * unit
                    for hand_id, throws in ((RIGHT, beat[1]), (LEFT, beat[2])):
                        for height, crossing in throws:
                            if height == 0:
                                continue
                            ball = acquire(hand_id, t_ms)
                            dest = hand_id if not crossing else (LEFT if hand_id == RIGHT else RIGHT)
                            # Air time must match siteswap height exactly so balls are not reused early.
                            air_ms = max(1.0, height * unit)
                            land = t_ms + air_ms
                            dwell_ms = self.dwell * unit
                            flights.append(
                                {
                                    "ball": ball,
                                    "t0": t_ms,
                                    "t1": land,
                                    "hold_until": land + dwell_ms,
                                    "hand0": hand_id,
                                    "hand1": dest,
                                    "height": height,
                                }
                            )
                            # Available only after landing (strict), so overlapping throws need extra balls.
                            release(dest, ball, land)
                else:
                    t_ms = (cycle * period + bi) * self.beat_ms
                    for height, crossing in beat:
                        if height == 0:
                            continue
                        ball = acquire(hand, t_ms)
                        dest = hand if not crossing else (LEFT if hand == RIGHT else RIGHT)
                        air_ms = max(1.0, height * self.beat_ms)
                        land = t_ms + air_ms
                        dwell_ms = self.dwell * self.beat_ms
                        flights.append(
                            {
                                "ball": ball,
                                "t0": t_ms,
                                "t1": land,
                                "hold_until": land + dwell_ms,
                                "hand0": hand,
                                "hand1": dest,
                                "height": height,
                            }
                        )
                        release(dest, ball, land)
                    hand = LEFT if hand == RIGHT else RIGHT

        return flights

    def _pos_on_arc(self, x0, y0, x1, y1, height, u):
        """u in [0,1]; peak proportional to throw height."""
        x = x0 + (x1 - x0) * u
        base = y0 + (y1 - y0) * u
        peak = self.peak_scale * height
        y = base - 4.0 * peak * u * (1.0 - u)
        return x, y

    def state_at(self, t_ms=None):
        """Return dict with hands, balls[{id,x,y}], body, head for drawing."""
        if t_ms is None:
            t_ms = self.elapsed_ms()
        loop = self.loop_ms
        if loop > 0:
            # Use middle cycles for stable state
            span = loop * 4
            if span > 0:
                t_loop = (t_ms % span) + loop  # offset into warmed-up region
            else:
                t_loop = t_ms
        else:
            t_loop = t_ms

        balls = {}
        hand_holding = {RIGHT: None, LEFT: None}

        for f in self.flights:
            b = f["ball"]
            t0, t1 = f["t0"], f["t1"]
            hold_until = f["hold_until"]
            if t_loop < t0:
                continue
            if t0 <= t_loop <= t1:
                u = 0.0 if t1 == t0 else (t_loop - t0) / (t1 - t0)
                x0, y0 = self.hand_pos[f["hand0"]]
                x1, y1 = self.hand_pos[f["hand1"]]
                x, y = self._pos_on_arc(x0, y0, x1, y1, f["height"], u)
                balls[b] = (x, y)
            elif t1 < t_loop <= hold_until:
                x1, y1 = self.hand_pos[f["hand1"]]
                balls[b] = (x1, y1)
                hand_holding[f["hand1"]] = b

        # Fill missing balls at last known hand (held before first throw in window)
        for bid in range(self.num_balls):
            if bid not in balls:
                # find most recent flight for this ball ending before t_loop
                best = None
                for f in self.flights:
                    if f["ball"] != bid:
                        continue
                    if f["t1"] <= t_loop:
                        if best is None or f["t1"] > best["t1"]:
                            best = f
                if best is not None:
                    x, y = self.hand_pos[best["hand1"]]
                    balls[bid] = (x, y)
                else:
                    # waiting to start — park near a hand
                    h = RIGHT if (bid % 2 == 0) else LEFT
                    x, y = self.hand_pos[h]
                    balls[bid] = (x + (bid - self.num_balls / 2) * 3, y)

        # Hand aim: toward ball being thrown or resting
        hands_xy = {
            RIGHT: self.hand_pos[RIGHT],
            LEFT: self.hand_pos[LEFT],
        }
        return {
            "balls": balls,
            "hands": hands_xy,
            "body": self.body,
            "head": self.head,
            "floor_y": self.floor_y,
            "t": t_ms,
        }
