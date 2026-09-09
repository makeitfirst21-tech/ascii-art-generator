"""Real-time tracking and market signals.

Walters' organisation did not beat football by picking winners. It beat football
by knowing, minute to minute, which numbers were moving, who moved them, and
which shops had not caught up yet. This module is the ledger that makes that
possible: feed it price snapshots, ask it what the market is telling you.
"""

import math
import time
from collections import defaultdict

from .odds import (american_to_prob, devig, prob_to_american, fmt_american,
                   american_to_decimal, hold,
                   cents_between as odds_cents_between)

# ---------------------------------------------------------------------------
# Not all books are evidence.
#
# A price at a shop that will take $50k from a known winner is information. A
# price at a shop that limits you to $200 and bans you for beating the closing
# line is marketing. Weight accordingly.
# ---------------------------------------------------------------------------

BOOK_WEIGHTS = {
    "pinnacle": 1.00,
    "circa": 0.95,
    "bookmaker": 0.85,
    "betcris": 0.80,
    "cris": 0.80,
    "heritage": 0.60,
    "betonline": 0.55,
    "fanduel": 0.50,
    "draftkings": 0.50,
    "bet365": 0.45,
    "betmgm": 0.40,
    "caesars": 0.40,
    "pointsbet": 0.30,
    "espnbet": 0.25,
    "fanatics": 0.25,
    "hardrock": 0.20,
    "prizepicks": 0.15,
    "underdog": 0.15,
}

SHARP_BOOKS = {"pinnacle", "circa", "bookmaker", "betcris", "cris"}


def book_weight(book):
    return BOOK_WEIGHTS.get(book.lower().replace(" ", ""), 0.30)


class Snapshot:
    """One price, at one book, at one moment."""

    def __init__(self, book, price, timestamp=None, limit=None, opposite=None,
                 ticket_pct=None, handle_pct=None):
        self.book = book
        self.price = float(price)
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.limit = float(limit) if limit else None
        self.opposite = float(opposite) if opposite is not None else None
        self.ticket_pct = ticket_pct   # % of bet slips on this side
        self.handle_pct = handle_pct   # % of money on this side

    def fair_prob(self, method="power"):
        if self.opposite is None:
            return american_to_prob(self.price)
        return devig([self.price, self.opposite], method)[0]

    def __repr__(self):
        return "<%s %s @ %s>" % (self.book, fmt_american(self.price),
                                 time.strftime("%H:%M:%S", time.localtime(self.timestamp)))


class Signal:
    """Something the market did that Jordan wants you to know about."""

    def __init__(self, kind, strength, message, detail=None):
        self.kind = kind
        self.strength = max(0.0, min(1.0, float(strength)))   # 0-1
        self.message = message
        self.detail = detail or {}

    def __repr__(self):
        return "<Signal %s %.2f: %s>" % (self.kind, self.strength, self.message)

    def bar(self, width=10):
        filled = int(round(self.strength * width))
        return "#" * filled + "." * (width - filled)


class MarketTracker:
    """Holds the price history for one side of one market and reads it."""

    def __init__(self, name, devig_method="power"):
        self.name = name
        self.devig_method = devig_method
        self.snapshots = defaultdict(list)   # book -> [Snapshot]

    # ---------------------------------------------------------------- ingest

    def record(self, snapshot):
        self.snapshots[snapshot.book.lower()].append(snapshot)
        self.snapshots[snapshot.book.lower()].sort(key=lambda s: s.timestamp)
        return self

    def add(self, book, price, **kw):
        return self.record(Snapshot(book, price, **kw))

    # ---------------------------------------------------------------- reads

    def latest(self, book=None):
        if book:
            hist = self.snapshots.get(book.lower())
            return hist[-1] if hist else None
        return {b: h[-1] for b, h in self.snapshots.items() if h}

    def opener(self, book):
        hist = self.snapshots.get(book.lower())
        return hist[0] if hist else None

    def sharp_consensus(self):
        """Limit- and reputation-weighted fair probability.

        Weight = book weight * log-scaled limit. A $500 price at Pinnacle and a
        $50,000 price at Pinnacle are not the same statement.
        """
        num = den = 0.0
        for book, hist in self.snapshots.items():
            if not hist:
                continue
            snap = hist[-1]
            w = book_weight(book)
            if snap.limit:
                w *= 1.0 + math.log10(max(snap.limit, 100.0) / 100.0)
            num += w * snap.fair_prob(self.devig_method)
            den += w
        return num / den if den else None

    def consensus_price(self):
        p = self.sharp_consensus()
        return prob_to_american(p) if p else None

    def best_available(self):
        """Best price on this side across every book -- line shopping in one call.

        Half a cent per bet, taken every bet, is the difference between a
        winning year and an expensive hobby.
        """
        best = None
        for book, hist in self.snapshots.items():
            if not hist:
                continue
            snap = hist[-1]
            if best is None or snap.price > best.price:
                best = snap
        return best

    def outliers(self, threshold=0.02):
        """Books whose price is materially better than the sharp consensus.

        This is the +EV list: a stale number at a soft shop against a market
        that has already moved.
        """
        fair = self.sharp_consensus()
        if fair is None:
            return []
        out = []
        for book, hist in self.snapshots.items():
            if not hist or book in SHARP_BOOKS:
                continue
            snap = hist[-1]
            offered = american_to_prob(snap.price)
            edge = fair - offered
            if edge >= threshold:
                out.append({
                    "book": snap.book,
                    "price": snap.price,
                    "fair_price": prob_to_american(fair),
                    "edge_prob": edge,
                    "ev_pct": 100.0 * (fair * (american_to_decimal(snap.price) - 1.0)
                                       - (1.0 - fair)),
                })
        out.sort(key=lambda d: -d["ev_pct"])
        return out

    # -------------------------------------------------------------- signals

    def steam(self, window_seconds=600, min_books=3, min_cents=8):
        """Several books move the same way, fast: someone big is in the market."""
        now = max((s.timestamp for h in self.snapshots.values() for s in h), default=None)
        if now is None:
            return None
        cutoff = now - window_seconds
        movers = []
        for book, hist in self.snapshots.items():
            if len(hist) < 2:
                continue
            # Baseline is the last price *before* the window opened, so a book
            # that has quoted once in the last ten minutes still counts as having
            # moved. Fall back to the earliest in-window quote.
            before = [s for s in hist if s.timestamp <= cutoff]
            recent = [s for s in hist if s.timestamp > cutoff]
            if not recent:
                continue
            base = before[-1] if before else recent[0]
            if base is recent[0] and len(recent) < 2:
                continue
            delta = recent[-1].price - base.price
            if abs(delta) >= min_cents:
                movers.append((book, delta))
        if len(movers) < min_books:
            return None
        same_way = [d for _, d in movers if d < 0]
        direction = "shortening (money on this side)" if len(same_way) > len(movers) / 2 \
            else "drifting (money on the other side)"
        agree = max(len(same_way), len(movers) - len(same_way))
        if agree < min_books:
            return None
        avg = sum(abs(d) for _, d in movers) / len(movers)
        strength = min(1.0, (agree / 6.0) * 0.6 + min(avg / 25.0, 1.0) * 0.4)
        return Signal(
            "steam", strength,
            "Steam: %d books moved %.0f cents on average, %s" % (agree, avg, direction),
            {"books": [b for b, _ in movers], "avg_cents": avg, "direction": direction})

    def reverse_line_movement(self, min_cents=5, public_threshold=60.0):
        """The tell that outlives every other tell.

        `ticket_pct` is the share of bet *slips* on the side this tracker is
        following. Reverse line movement means the price moved against where the
        tickets are -- which is the book telling you that the money and the
        tickets are not the same people.

        The two cases that matter, and the two that do not:

          few tickets here + price shortens  -> sharp money is on THIS side
          many tickets here + price drifts   -> sharp money is on the OTHER side
          many tickets here + price shortens -> ordinary public flow, low information
          few tickets here + price drifts    -> ordinary public flow, low information

        A price "shortens" when it gets worse for the bettor (-108 to -120);
        it "drifts" when it gets better (-108 to -101).
        """
        best = None
        for book, hist in self.snapshots.items():
            if len(hist) < 2:
                continue
            first, last = hist[0], hist[-1]
            tickets = last.ticket_pct if last.ticket_pct is not None else first.ticket_pct
            if tickets is None:
                continue
            move = last.price - first.price           # negative = shortening
            if abs(move) < min_cents:
                continue
            quiet = 100.0 - public_threshold          # e.g. 40%

            if tickets <= quiet and move <= -min_cents:
                lean = tickets
                kind, direction = "reverse_line_movement", "this side"
                msg = ("RLM at %s: only %.0f%% of tickets on this side, yet the price "
                       "shortened %.0f cents. The line is moving toward the unpopular "
                       "side -- that is respected money, not volume."
                       % (book, tickets, abs(move)))
            elif tickets >= public_threshold and move >= min_cents:
                lean = 100.0 - tickets
                kind, direction = "reverse_line_movement", "the other side"
                msg = ("RLM at %s: %.0f%% of tickets on this side and the price still "
                       "drifted %.0f cents. The book is happy to take more of this -- "
                       "the money it respects is on the other side."
                       % (book, tickets, move))
            else:
                # Line moved the way the tickets did. That is what is supposed to
                # happen and it tells you almost nothing.
                continue

            strength = min(1.0, (abs(50.0 - tickets) / 30.0) * 0.5
                           + min(abs(move) / 20.0, 1.0) * 0.5)
            sig = Signal(kind, strength, msg,
                         {"book": book, "ticket_pct": tickets, "move": move,
                          "sharp_side": direction, "public_lean": lean})
            if best is None or sig.strength > best.strength:
                best = sig
        return best

    def public_flow(self, min_cents=5, public_threshold=60.0):
        """Line moved with the tickets -- normal, and worth naming so it is not
        mistaken for a signal."""
        out = []
        for book, hist in self.snapshots.items():
            if len(hist) < 2:
                continue
            first, last = hist[0], hist[-1]
            tickets = last.ticket_pct if last.ticket_pct is not None else first.ticket_pct
            if tickets is None:
                continue
            move = last.price - first.price
            if abs(move) < min_cents:
                continue
            if tickets >= public_threshold and move <= -min_cents:
                out.append(Signal("public_flow", 0.2,
                                  "%s: %.0f%% of tickets here and the price shortened "
                                  "%.0f cents -- the book moved with the crowd. Normal, "
                                  "not information." % (book, tickets, abs(move)),
                                  {"book": book, "move": move}))
        return out

    def handle_ticket_divergence(self, gap=20.0):
        """Few bets, lots of money: the classic signature of a syndicate wager."""
        out = []
        for book, hist in self.snapshots.items():
            if not hist:
                continue
            s = hist[-1]
            if s.ticket_pct is None or s.handle_pct is None:
                continue
            d = s.handle_pct - s.ticket_pct
            if abs(d) >= gap:
                side = "this side" if d > 0 else "the other side"
                out.append(Signal(
                    "handle_divergence", min(1.0, abs(d) / 45.0),
                    "%s: %.0f%% of tickets but %.0f%% of money -- big wagers on %s"
                    % (book, s.ticket_pct, s.handle_pct, side),
                    {"book": book, "gap": d}))
        return out

    def market_tightening(self):
        """Falling hold as game time nears means the market has an opinion.

        Books widen when they are unsure and tighten when they are confident.
        A market that has tightened to a 2-cent hold has been vetted; a market
        still sitting at 12 cents has not, which is where the mistakes live.
        """
        holds = []
        for book, hist in self.snapshots.items():
            for s in hist:
                if s.opposite is not None:
                    holds.append((s.timestamp, book, hold([s.price, s.opposite])))
        if len(holds) < 2:
            return None
        holds.sort()
        first, last = holds[0][2], holds[-1][2]
        change = last - first
        msg = ("Market %s: hold moved from %.1f%% to %.1f%%"
               % ("tightening -- prices are being vetted" if change < -0.005
                  else "widening -- books are uncertain" if change > 0.005
                  else "stable", 100 * first, 100 * last))
        return Signal("market_tightening", min(1.0, abs(change) / 0.06), msg,
                      {"open_hold": first, "current_hold": last})

    def closing_line_value(self, bet_price, closing_price=None, method="power"):
        """CLV: did you beat the number the market closed at?

        The only performance metric that is not mostly noise. Results over a
        season are a coin-flip story; consistent CLV is the season's real grade.
        """
        if closing_price is None:
            # The *consensus* close, not the best price on the board. A stale
            # soft number is not what the market concluded, and grading yourself
            # against it flatters the result.
            closing_price = self.consensus_price()
        if closing_price is None:
            return None
        bet_p = american_to_prob(bet_price)
        close_p = american_to_prob(closing_price)
        cents = odds_cents_between(bet_price, closing_price)
        return {
            "bet_price": bet_price,
            "closing_price": closing_price,
            "cents": cents,
            "prob_edge": close_p - bet_p,
            "beat_close": close_p > bet_p,
            "roi_estimate": 100.0 * (american_to_decimal(bet_price) * close_p - 1.0),
        }

    def all_signals(self):
        out = []
        for sig in (self.steam(), self.reverse_line_movement(), self.market_tightening()):
            if sig:
                out.append(sig)
        out.extend(self.handle_ticket_divergence())
        out.extend(self.public_flow())
        out.sort(key=lambda s: -s.strength)
        return out


# ------------------------------------------------------------ cross-book tools


def arbitrage(price_a, price_b, bankroll=1000.0):
    """Two prices on opposite sides that sum to under 100%."""
    pa, pb = american_to_prob(price_a), american_to_prob(price_b)
    total = pa + pb
    if total >= 1.0:
        return None
    stake_a = bankroll * pa / total
    return {
        "profit_pct": 100.0 * (1.0 / total - 1.0),
        "stake_a": stake_a,
        "stake_b": bankroll - stake_a,
        "guaranteed_return": bankroll / total,
    }


def middle(low_line, low_price, high_line, high_price, center=None, sd=13.2,
           sport=None, stake=1.0, favorite_share=0.60):
    """Buy both sides with a gap between them; win both if the result lands inside.

    You are betting the OVER (or the favourite) at `low_line` and the UNDER (or
    the dog) at `high_line`, with low_line < high_line. Three outcomes, and the
    only correct way to judge one is to price all three:

        result inside the gap   both bets win
        result above the gap    the low-line bet wins, the other loses
        result below the gap    the high-line bet wins, the other loses

    Note what that means: a middle is not "free" -- outside the gap you pay the
    vig on the loser, which is a small guaranteed bleed against a large
    occasional score. The old comparison of middle probability against the
    overround is not the same calculation and gets the answer wrong on any
    non-standard price.

    `center` is what the market expects the result to be; it defaults to the
    midpoint of the two lines, which is the right assumption if you bought both
    sides around the current number.
    """
    lo, hi = float(low_line), float(high_line)
    if hi <= lo:
        return None
    if center is None:
        center = 0.5 * (lo + hi)

    from .stats import norm_cdf
    z_lo = (lo - center) / sd
    z_hi = (hi - center) / sd
    p_low = norm_cdf(z_lo)                    # result below the gap
    p_mid = norm_cdf(z_hi) - norm_cdf(z_lo)   # inside -- both win
    p_high = 1.0 - norm_cdf(z_hi)             # above the gap

    d_low = american_to_decimal(low_price)    # the over / favourite side
    d_high = american_to_decimal(high_price)  # the under / dog side

    ev = stake * (
        p_mid * ((d_low - 1.0) + (d_high - 1.0))
        + p_high * ((d_low - 1.0) - 1.0)
        + p_low * ((d_high - 1.0) - 1.0))
    outlay = 2.0 * stake

    # On an NFL spread the gap is won by landing on specific integer margins,
    # and those integers are wildly unequal. The normal approximation cannot see
    # that -- it prices a gap spanning 3 the same as one spanning 2. So when the
    # sport is known, price the gap off the margin distribution instead.
    spanned, key_mass, discrete_mid = [], 0.0, None
    if sport and sport.lower() == "nfl":
        from . import keynumbers
        discrete_mid = 0.0
        for n in range(int(math.floor(lo)) + 1, int(math.ceil(hi))):
            share = favorite_share if n > 0 else (1.0 - favorite_share)
            mass = keynumbers.margin_mass(n) * (1.0 if n == 0 else share)
            discrete_mid += mass
            if keynumbers.is_key_number(n):
                spanned.append(abs(n))
                key_mass += mass
        # Rebalance the outside outcomes around the better middle estimate.
        remaining = max(0.0, 1.0 - discrete_mid)
        outside = p_high + p_low
        if outside > 0:
            p_high = remaining * p_high / outside
            p_low = remaining * p_low / outside
        p_mid = discrete_mid
        ev = stake * (
            p_mid * ((d_low - 1.0) + (d_high - 1.0))
            + p_high * ((d_low - 1.0) - 1.0)
            + p_low * ((d_high - 1.0) - 1.0))

    return {
        "width": hi - lo,
        "middle_prob": p_mid,
        "priced_from": "nfl margin distribution" if discrete_mid is not None
                       else "normal approximation",
        "prob_above": p_high,
        "prob_below": p_low,
        "ev": ev,
        "ev_pct": 100.0 * ev / outlay,
        "outlay": outlay,
        "worth_it": ev > 0,
        "breakeven_middle_prob": _breakeven_middle_prob(d_low, d_high),
        "key_numbers_spanned": spanned,
        "key_number_mass": key_mass,
    }


def _breakeven_middle_prob(d_low, d_high):
    """How often the middle must land to break even at these two prices.

    For two -110s it is about 4.8%. Quote this at anyone calling a middle free
    money.
    """
    # EV = p*(a+b) + (1-p)*(worst case one side wins) ... solved for p, assuming
    # the outside outcomes split evenly between the two sides.
    a, b = d_low - 1.0, d_high - 1.0
    win_both = a + b
    outside = 0.5 * ((a - 1.0) + (b - 1.0))
    if win_both - outside <= 0:
        return None
    return max(0.0, -outside / (win_both - outside))
