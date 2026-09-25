"""The daily card ledger: log picks, grade them, score the forecasts.

Two people making picks every day need a scoreboard that is harder to fool than
win-loss. Win-loss over a season is mostly noise -- a 55% bettor and a 48%
bettor look identical for months. So the ledger scores the *probabilities*, not
just the outcomes, using the same proper scoring rules weather forecasters are
graded on:

    Brier score   mean squared error of the stated probability. Lower is better.
                  0.25 is what you get by saying "50%" to everything.

    Log loss      punishes confident wrongness far harder than Brier does.
                  0.693 is the coin-flip baseline. Say 95% and miss, and this
                  is the metric that notices.

    Calibration   when you say 60%, does it happen 60% of the time? A forecaster
                  can be well calibrated and useless, or sharp and overconfident.
                  This separates the two.

    Skill vs market   the only one that matters. Your Brier score against the
                  de-vigged market probability's Brier score on the same games.
                  Positive means you know something the market does not.
                  Zero or negative means you are an expensive index fund.

A pick is stored with the probability its author claimed at the time. That is
the number being graded, and it cannot be revised after the result -- which is
the entire point.
"""

import json
import math
import os
import random
from datetime import datetime

from . import odds
from .stats import wilson_interval

DEFAULT_PATH = os.environ.get("JORDAN_LEDGER", "jordan_ledger.json")

RESULTS = ("pending", "win", "loss", "push")


# --------------------------------------------------------------------- model


class Pick:
    def __init__(self, id, date, author, sport, description, price, prob,
                 stake=1.0, market_prob=None, book=None, result="pending",
                 closing_price=None, notes=None, confidence=None, legs=None):
        self.id = int(id)
        self.date = date
        self.author = author
        self.sport = sport
        self.description = description
        self.price = float(price)
        self.prob = float(prob)
        self.stake = float(stake)
        self.market_prob = float(market_prob) if market_prob is not None else None
        self.book = book
        self.result = result
        self.closing_price = float(closing_price) if closing_price is not None else None
        self.notes = notes
        self.confidence = confidence
        self.legs = legs or []

    # ---- derived

    @property
    def graded(self):
        return self.result in ("win", "loss")

    @property
    def outcome(self):
        """1 for a win, 0 for a loss, None if pending or pushed."""
        if self.result == "win":
            return 1.0
        if self.result == "loss":
            return 0.0
        return None

    @property
    def ev_pct(self):
        return odds.ev_percent(self.prob, self.price)

    def profit(self):
        """Units won or lost."""
        if self.result == "win":
            return self.stake * (odds.american_to_decimal(self.price) - 1.0)
        if self.result == "loss":
            return -self.stake
        return 0.0

    def clv(self):
        """Cents beaten (or lost) against the closing price."""
        if self.closing_price is None:
            return None
        return odds.cents_between(self.price, self.closing_price)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def __repr__(self):
        return "<Pick #%d %s %s %s %s>" % (self.id, self.date, self.author,
                                           self.description, self.result)


# -------------------------------------------------------------------- store


class Ledger:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.picks = []
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self.picks = []
            return self
        try:
            with open(self.path) as fh:
                text = fh.read().strip()
            raw = json.loads(text) if text else {"picks": []}
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            # This file is somebody's betting history. Refuse to silently
            # overwrite a damaged one -- say what is wrong and where the
            # backup would go.
            raise ValueError(
                "ledger at %s is not readable JSON (%s). It has not been "
                "modified. Move it aside or repair it before logging more picks."
                % (self.path, exc))
        picks = []
        for i, d in enumerate(raw.get("picks", [])):
            try:
                picks.append(Pick.from_dict(d))
            except (TypeError, ValueError) as exc:
                raise ValueError("ledger entry %d in %s is malformed: %s"
                                 % (i, self.path, exc))
        self.picks = picks
        return self

    def save(self):
        """Write atomically: a half-written ledger is worse than no ledger."""
        directory = os.path.dirname(os.path.abspath(self.path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump({"picks": [p.to_dict() for p in self.picks]}, fh, indent=2)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)   # atomic on POSIX and Windows
        return self

    def next_id(self):
        return max((p.id for p in self.picks), default=0) + 1

    def add(self, author, sport, description, price, prob, stake=1.0,
            date=None, market_prob=None, book=None, notes=None,
            confidence=None, legs=None):
        if not 0.0 < prob < 1.0:
            raise ValueError("probability must be strictly between 0 and 1 -- "
                             "a forecast of 0 or 1 is not a forecast")
        pick = Pick(self.next_id(), date or datetime.now().strftime("%Y-%m-%d"),
                    author, sport, description, price, prob, stake,
                    market_prob, book, "pending", None, notes, confidence, legs)
        self.picks.append(pick)
        return pick

    def get(self, pick_id):
        for p in self.picks:
            if p.id == int(pick_id):
                return p
        return None

    def grade(self, pick_id, result, closing_price=None):
        if result not in RESULTS:
            raise ValueError("result must be one of %s" % (RESULTS,))
        pick = self.get(pick_id)
        if pick is None:
            raise KeyError("no pick #%s" % pick_id)
        pick.result = result
        if closing_price is not None:
            pick.closing_price = float(closing_price)
        return pick

    def by_author(self, author):
        return [p for p in self.picks if p.author == author]

    def pending(self):
        return [p for p in self.picks if p.result == "pending"]

    def authors(self):
        return sorted({p.author for p in self.picks})


# ------------------------------------------------------------------ scoring


def _clamp(p, eps=1e-6):
    return min(max(p, eps), 1.0 - eps)


def brier(picks):
    """Mean squared error of the stated probabilities. Lower is better."""
    graded = [p for p in picks if p.graded]
    if not graded:
        return None
    return sum((p.prob - p.outcome) ** 2 for p in graded) / len(graded)


def log_loss(picks):
    """Punishes confident wrongness. Coin-flip baseline is 0.693."""
    graded = [p for p in picks if p.graded]
    if not graded:
        return None
    total = 0.0
    for p in graded:
        q = _clamp(p.prob)
        total += -(p.outcome * math.log(q) + (1 - p.outcome) * math.log(1 - q))
    return total / len(graded)


def brier_vs_market(picks):
    """Brier score of the market's own de-vigged probability on the same games.

    The benchmark that matters. Beating a coin flip is trivial; beating the
    closing market is the entire job.
    """
    graded = [p for p in picks if p.graded and p.market_prob is not None]
    if not graded:
        return None
    return sum((p.market_prob - p.outcome) ** 2 for p in graded) / len(graded)


def skill_score(picks):
    """Brier skill score against the market. Positive means real edge."""
    graded = [p for p in picks if p.graded and p.market_prob is not None]
    if len(graded) < 2:
        return None
    mine = sum((p.prob - p.outcome) ** 2 for p in graded) / len(graded)
    theirs = sum((p.market_prob - p.outcome) ** 2 for p in graded) / len(graded)
    if theirs <= 0:
        return None
    return 1.0 - mine / theirs


def calibration(picks, bins=5):
    """Stated probability against what actually happened, in bins.

    Answers the only question that matters about a forecaster: when you say
    60%, does it land 60% of the time?
    """
    graded = [p for p in picks if p.graded]
    edges = [i / bins for i in range(bins + 1)]
    rows = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        group = [p for p in graded
                 if (lo <= p.prob < hi) or (i == bins - 1 and p.prob == hi)]
        if not group:
            rows.append({"lo": lo, "hi": hi, "n": 0, "stated": None,
                         "actual": None, "gap": None})
            continue
        stated = sum(p.prob for p in group) / len(group)
        actual = sum(p.outcome for p in group) / len(group)
        rows.append({"lo": lo, "hi": hi, "n": len(group), "stated": stated,
                     "actual": actual, "gap": actual - stated})
    return rows


def record(picks):
    wins = sum(1 for p in picks if p.result == "win")
    losses = sum(1 for p in picks if p.result == "loss")
    pushes = sum(1 for p in picks if p.result == "push")
    n = wins + losses
    lo, hi = wilson_interval(wins, n) if n else (0.0, 1.0)
    profit = sum(p.profit() for p in picks)
    staked = sum(p.stake for p in picks if p.result in ("win", "loss"))
    clvs = [p.clv() for p in picks if p.clv() is not None]
    return {
        "n": n, "wins": wins, "losses": losses, "pushes": pushes,
        "pending": sum(1 for p in picks if p.result == "pending"),
        "win_pct": 100.0 * wins / n if n else None,
        "ci_low": 100.0 * lo, "ci_high": 100.0 * hi,
        "units": profit,
        "roi_pct": 100.0 * profit / staked if staked else None,
        "avg_clv": sum(clvs) / len(clvs) if clvs else None,
        "clv_beat_rate": 100.0 * sum(1 for c in clvs if c > 0) / len(clvs)
                         if clvs else None,
        "brier": brier(picks),
        "log_loss": log_loss(picks),
        "market_brier": brier_vs_market(picks),
        "skill": skill_score(picks),
    }


def bootstrap_brier_gap(picks_a, picks_b, trials=4000, seed=1):
    """Is the gap between two forecasters real, or is it a small sample?

    Resamples each side's graded picks and reports how often A actually beats B.
    Anything between roughly 20% and 80% means you do not know yet.
    """
    a = [(p.prob - p.outcome) ** 2 for p in picks_a if p.graded]
    b = [(p.prob - p.outcome) ** 2 for p in picks_b if p.graded]
    if len(a) < 3 or len(b) < 3:
        return None
    rng = random.Random(seed)
    wins = 0
    for _ in range(trials):
        sa = sum(rng.choice(a) for _ in a) / len(a)
        sb = sum(rng.choice(b) for _ in b) / len(b)
        if sa < sb:          # lower Brier is better
            wins += 1
    return {
        "a_better_pct": 100.0 * wins / trials,
        "a_brier": sum(a) / len(a),
        "b_brier": sum(b) / len(b),
        "n_a": len(a), "n_b": len(b),
        "conclusive": not (20.0 < 100.0 * wins / trials < 80.0),
    }
