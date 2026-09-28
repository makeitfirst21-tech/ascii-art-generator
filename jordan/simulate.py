"""Projection models and Monte Carlo simulation.

Voulgaris' edge in the NBA was not a hunch about the Lakers; it was a model
that produced a distribution for every game and every rotation, then bet the
places where the market disagreed with the distribution. This module is the
small, honest version of that: give every leg a shape, then roll the dice a
lot of times.
"""

import math
import random

from . import odds as odds_module
from . import stats
from .odds import prob_to_american

# ------------------------------------------------------------------ marginals


class Marginal:
    """A stat's distribution: knows its mean, and how to turn a uniform draw
    into a value."""

    name = "marginal"
    continuous = True   # False for stats where an "effective line" is meaningless

    def ppf(self, u):
        raise NotImplementedError

    def mean(self):
        raise NotImplementedError

    def sd(self):
        """Standard deviation on the stat's own scale."""
        raise NotImplementedError

    def push_prob(self, line):
        """P(stat lands exactly on the line). Zero for continuous stats."""
        return 0.0

    def prob_over(self, line, samples=200000, rng=None):
        """Analytic where possible, otherwise sampled."""
        rng = rng or random.Random(0)
        hits = 0
        for _ in range(samples):
            if self.ppf(rng.random()) > line:
                hits += 1
        return hits / samples


class NormalStat(Marginal):
    """Continuous volume stats: passing yards, points, total bases allowed."""

    name = "normal"

    def __init__(self, mu, sigma):
        self.mu = float(mu)
        self.sigma = max(float(sigma), 1e-9)

    def ppf(self, u):
        return self.mu + self.sigma * stats.norm_ppf(u)

    def mean(self):
        return self.mu

    def sd(self):
        return self.sigma

    def prob_over(self, line, samples=None, rng=None):
        return 1.0 - stats.norm_cdf((line - self.mu) / self.sigma)


class LognormalStat(Marginal):
    """Right-skewed yardage stats.

    Receiving yards are not symmetric: the floor is zero and the ceiling is an
    80-yard catch-and-run. A normal distribution prices the over on a big
    receiving line too cheaply, which is exactly the leg the books want in your
    parlay.
    """

    name = "lognormal"

    def __init__(self, mu, sigma):
        mu, sigma = float(mu), max(float(sigma), 1e-9)
        if mu <= 0:
            raise ValueError("lognormal mean must be positive")
        var = sigma * sigma
        self.sigma_log = math.sqrt(math.log(1.0 + var / (mu * mu)))
        self.mu_log = math.log(mu) - 0.5 * self.sigma_log ** 2
        self._mean = mu
        self._sd = sigma

    def ppf(self, u):
        return math.exp(self.mu_log + self.sigma_log * stats.norm_ppf(u))

    def mean(self):
        return self._mean

    def sd(self):
        return self._sd

    def prob_over(self, line, samples=None, rng=None):
        if line <= 0:
            return 1.0
        return 1.0 - stats.norm_cdf((math.log(line) - self.mu_log) / self.sigma_log)


class CountStat(Marginal):
    """Receptions, strikeouts, made threes, rebounds.

    Uses a negative binomial when the variance exceeds the mean, which it
    almost always does once game script is involved.
    """

    name = "count"
    continuous = False

    def __init__(self, mean, variance=None):
        self.mu = float(mean)
        self.var = float(variance) if variance is not None else float(mean) * 1.35

    def ppf(self, u):
        return float(stats.negbin_ppf(u, self.mu, self.var))

    def mean(self):
        return self.mu

    def sd(self):
        return math.sqrt(self.var)

    def push_prob(self, line):
        """A count stat on a whole-number line can land exactly on it."""
        if abs(line - round(line)) > 1e-9:
            return 0.0
        k = int(round(line))
        if k < 0:
            return 0.0
        return max(0.0, self._cdf(k) - self._cdf(k - 1))

    def _cdf(self, k):
        if k < 0:
            return 0.0
        if self.var <= self.mu:
            return stats.poisson_cdf(k, self.mu)
        p = self.mu / self.var
        r = self.mu * p / (1.0 - p)
        prob = p ** r
        total = prob
        for i in range(1, int(k) + 1):
            prob *= (r + i - 1.0) / i * (1.0 - p)
            total += prob
        return min(total, 1.0)

    def prob_over(self, line, samples=None, rng=None):
        """P(X > line). Summing the pmf directly beats inverting the cdf here."""
        return max(0.0, 1.0 - self._cdf(math.floor(line)))


class BernoulliStat(Marginal):
    """Anytime touchdown, to record a sack, first basket."""

    name = "bernoulli"
    continuous = False

    def __init__(self, prob):
        self.p = min(max(float(prob), 0.0), 1.0)

    def ppf(self, u):
        return 1.0 if u > (1.0 - self.p) else 0.0

    def mean(self):
        return self.p

    def sd(self):
        return math.sqrt(self.p * (1.0 - self.p))

    def prob_over(self, line=0.5, samples=None, rng=None):
        return self.p


# ---------------------------------------------------------------- projections


class Leg:
    """One side of one bet, with Jordan's own distribution behind it.

    `price` is what the book is offering. `market_prices` is the full two-way
    market when available, so the leg can be de-vigged instead of guessed at.
    """

    def __init__(self, label, marginal, line, side="over", price=-110,
                 market_prices=None, weight_model=0.5):
        if side not in ("over", "under", "yes", "no"):
            raise ValueError("side must be over/under/yes/no")
        self.label = label
        self.marginal = marginal
        self.line = float(line)
        self.side = side
        self.price = price
        self.market_prices = market_prices
        self.weight_model = min(max(float(weight_model), 0.0), 1.0)

    def model_prob(self):
        over = self.marginal.prob_over(self.line)
        return over if self.side in ("over", "yes") else 1.0 - over

    def market_prob(self, method="power"):
        """De-vigged market probability for this side, if the market is known."""
        if not self.market_prices:
            return None
        from .odds import devig
        return devig(self.market_prices, method)[0]

    def blended_prob(self, method="power"):
        """Model and market, blended.

        The market is the single best model anyone has ever built. A projection
        that disagrees with a well-limited market is usually wrong, so Jordan
        never fully trusts his own number -- he weights it against the market
        and bets the residual.
        """
        m = self.model_prob()
        mk = self.market_prob(method)
        if mk is None:
            return m
        w = self.weight_model
        return w * m + (1.0 - w) * mk

    def hits(self, value):
        if self.side in ("over", "yes"):
            return value > self.line
        return value < self.line

    def __repr__(self):
        return "<Leg %s %s %g @ %s>" % (self.label, self.side, self.line, self.price)


# ------------------------------------------------------------ the simulator


class Simulation:
    """Monte Carlo over a set of legs with an optional correlation matrix.

    Two things are worth understanding about how this works, because they are
    where naive parlay tools go wrong.

    **The correlation matrix is on the STAT scale, not the bet scale.** A +0.55
    between passing yards and receiving yards stays +0.55 here, whichever side of
    each line you are betting. The simulation derives the bet-level relationship
    itself by sampling stats and checking them against the lines -- so flipping
    the sign for an over/under pair before handing it over would flip it twice
    and invert the answer. `correlation.flip_for_sides` exists for reasoning
    about bets on paper, not for feeding this class.

    **Each leg is evaluated at its blended probability, not its raw model
    probability.** The leg grades and the parlay price therefore agree, and the
    market gets its say in the joint probability instead of being consulted for
    display purposes and then discarded.
    """

    def __init__(self, legs, correlation=None, trials=50000, seed=None,
                 devig_method="power"):
        self.legs = list(legs)
        self.trials = int(trials)
        self.rng = random.Random(seed)
        self.devig_method = devig_method
        n = len(self.legs)
        if correlation is None:
            correlation = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        self.correlation = stats.nearest_correlation(correlation)
        self.copula = stats.GaussianCopula(self.correlation, rng=self.rng)

        # Target hit probability per leg -- model and market, blended.
        self.target_probs = [leg.blended_prob(devig_method) for leg in self.legs]
        # Probability the stat lands exactly on the line (whole-number lines on
        # discrete stats only). A push voids the leg and reduces the parlay.
        self.push_probs = [leg.marginal.push_prob(leg.line) for leg in self.legs]
        # Keep the blend honest when a push is possible: win + push + lose = 1.
        for i, (p, push) in enumerate(zip(self.target_probs, self.push_probs)):
            if p + push > 1.0:
                self.push_probs[i] = max(0.0, 1.0 - p)

    def effective_line(self, index):
        """The line the blended probability actually corresponds to.

        If the model says 270 yards but the market disagrees, this reports the
        number Jordan is really betting into -- often the most revealing single
        figure in the whole report.
        """
        leg = self.legs[index]
        p = self.target_probs[index]
        u = (1.0 - p) if leg.side in ("over", "yes") else p
        return leg.marginal.ppf(min(max(u, 1e-9), 1.0 - 1e-9))

    def _outcome(self, index, u):
        """1 win, 0 push, -1 loss, from a copula uniform.

        The uniform is monotone in the stat, so the hit region sits at the top
        for an over and the bottom for an under. That is what carries the
        correlation sign through to the bet.
        """
        p = self.target_probs[index]
        push = self.push_probs[index]
        if self.legs[index].side in ("over", "yes"):
            if u > 1.0 - p:
                return 1
            if u > 1.0 - p - push:
                return 0
            return -1
        if u < p:
            return 1
        if u < p + push:
            return 0
        return -1

    def run(self, offered_price=None):
        """Simulate. `offered_price` lets the payout be graded per trial, with
        pushed legs correctly removed from the ticket."""
        n = len(self.legs)
        decimals = [odds_module.american_to_decimal(l.price) for l in self.legs]
        full_decimal = 1.0
        for d in decimals:
            full_decimal *= d
        offered_decimal = (odds_module.american_to_decimal(offered_price)
                           if offered_price is not None else full_decimal)

        all_hit = 0
        any_push = 0
        leg_hits = [0] * n
        hit_counts = [0] * (n + 1)
        indicators = [[] for _ in range(n)]
        payout_total = 0.0
        sample_cap = min(self.trials, 20000)

        for t in range(self.trials):
            us = self.copula.sample_uniforms()
            wins = 0
            live = 0
            pushed_decimal = 1.0
            lost = False
            pushed = False
            for i in range(n):
                out = self._outcome(i, us[i])
                if t < sample_cap:
                    indicators[i].append(1.0 if out > 0 else 0.0)
                if out > 0:
                    leg_hits[i] += 1
                    wins += 1
                    live += 1
                elif out == 0:
                    pushed = True
                    pushed_decimal *= decimals[i]
                else:
                    lost = True
                    live += 1
            hit_counts[wins] += 1
            if pushed:
                any_push += 1
            if not lost:
                # Every surviving leg won. A pushed leg is removed from the
                # ticket, so the payout shrinks by that leg's decimal.
                if wins == n:
                    all_hit += 1
                payout_total += offered_decimal / pushed_decimal
        ev_per_unit = payout_total / self.trials - 1.0

        return SimResult(self.legs, all_hit / self.trials,
                         [h / self.trials for h in leg_hits],
                         [c / self.trials for c in hit_counts],
                         self.trials, self.correlation,
                         target_probs=list(self.target_probs),
                         push_probs=list(self.push_probs),
                         push_rate=any_push / self.trials,
                         ev_per_unit=ev_per_unit,
                         indicators=indicators,
                         effective_lines=[self.effective_line(i) for i in range(n)])


class SimResult:
    def __init__(self, legs, joint_prob, leg_probs, hit_distribution, trials,
                 correlation, target_probs=None, push_probs=None, push_rate=0.0,
                 ev_per_unit=None, indicators=None, effective_lines=None):
        self.legs = legs
        self.joint_prob = joint_prob
        self.leg_probs = leg_probs
        self.hit_distribution = hit_distribution
        self.trials = trials
        self.correlation = correlation
        self.target_probs = target_probs or list(leg_probs)
        self.push_probs = push_probs or [0.0] * len(legs)
        self.push_rate = push_rate
        self.ev_per_unit = ev_per_unit
        self.indicators = indicators or []
        self.effective_lines = effective_lines or []

    @property
    def independent_prob(self):
        """What the book charges you for: the product of the legs."""
        p = 1.0
        for lp in self.leg_probs:
            p *= lp
        return p

    @property
    def correlation_multiplier(self):
        """> 1 means the legs help each other and the parlay is underpriced
        relative to a straight multiplication; < 1 means you are being sold a
        combination that is fighting itself."""
        ind = self.independent_prob
        if ind <= 0:
            return 0.0
        return self.joint_prob / ind

    def realized_bet_correlation(self):
        """Measured correlation between the legs *as bets*, from the simulation.

        Not the same number as the stat correlation that went in, and it should
        not be: thresholding a continuous stat at a line attenuates the
        relationship, and betting opposite sides inverts its sign. This is the
        number that actually decides whether the ticket is worth more or less
        than the product of its legs.
        """
        n = len(self.legs)
        out = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        if not self.indicators or len(self.indicators[0]) < 2:
            return out
        for i in range(n):
            for j in range(i + 1, n):
                rho = stats.pearson(self.indicators[i], self.indicators[j])
                out[i][j] = out[j][i] = rho
        return out

    @property
    def standard_error(self):
        p = self.joint_prob
        return math.sqrt(max(p * (1.0 - p), 0.0) / self.trials)

    def fair_price(self):
        if self.joint_prob <= 0:
            return None
        return prob_to_american(self.joint_prob)


# --------------------------------------------------------- convenience models


def game_total_model(team_total_a, team_total_b, sd_a=None, sd_b=None):
    """Two team totals into a game total distribution."""
    sd_a = sd_a if sd_a is not None else 0.55 * math.sqrt(max(team_total_a, 1.0)) * 2.2
    sd_b = sd_b if sd_b is not None else 0.55 * math.sqrt(max(team_total_b, 1.0)) * 2.2
    return NormalStat(team_total_a + team_total_b, math.sqrt(sd_a ** 2 + sd_b ** 2))


def spread_to_win_prob(spread, sd=13.2):
    """NFL default sd 13.2 points; NBA is closer to 11.5, college football 16."""
    return stats.norm_cdf(-spread / sd)


def win_prob_to_spread(prob, sd=13.2):
    return -stats.norm_ppf(prob) * sd


# ------------------------------------------------------------ spec loading

DISTRIBUTIONS = {
    "normal": lambda s: NormalStat(s["mean"], s.get("sd", s.get("sigma"))),
    "lognormal": lambda s: LognormalStat(s["mean"], s.get("sd", s.get("sigma"))),
    "count": lambda s: CountStat(s["mean"], s.get("variance")),
    "bernoulli": lambda s: BernoulliStat(s.get("prob", s.get("mean"))),
}


def marginal_from_spec(spec):
    kind = spec.get("dist", "normal").lower()
    if kind not in DISTRIBUTIONS:
        raise ValueError("unknown distribution %r (have: %s)"
                         % (kind, ", ".join(sorted(DISTRIBUTIONS))))
    return DISTRIBUTIONS[kind](spec)


def leg_from_spec(spec):
    """Build a Leg from a plain dict, as loaded from JSON.

    Recognised keys: label, stat, dist, mean, sd/variance/prob, line, side,
    price, market, weight_model.
    """
    leg = Leg(
        label=spec.get("label", "leg"),
        marginal=marginal_from_spec(spec),
        line=spec.get("line", 0.5),
        side=spec.get("side", "over"),
        price=spec.get("price", -110),
        market_prices=spec.get("market"),
        weight_model=spec.get("weight_model", 0.5),
    )
    leg.stat = spec.get("stat")
    leg.entity = spec.get("entity")
    return leg
