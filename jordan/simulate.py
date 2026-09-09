"""Projection models and Monte Carlo simulation.

Voulgaris' edge in the NBA was not a hunch about the Lakers; it was a model
that produced a distribution for every game and every rotation, then bet the
places where the market disagreed with the distribution. This module is the
small, honest version of that: give every leg a shape, then roll the dice a
lot of times.
"""

import math
import random

from . import stats
from .odds import prob_to_american

# ------------------------------------------------------------------ marginals


class Marginal:
    """A stat's distribution: knows its mean, and how to turn a uniform draw
    into a value."""

    name = "marginal"

    def ppf(self, u):
        raise NotImplementedError

    def mean(self):
        raise NotImplementedError

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

    def ppf(self, u):
        return math.exp(self.mu_log + self.sigma_log * stats.norm_ppf(u))

    def mean(self):
        return self._mean

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

    def __init__(self, mean, variance=None):
        self.mu = float(mean)
        self.var = float(variance) if variance is not None else float(mean) * 1.35

    def ppf(self, u):
        return float(stats.negbin_ppf(u, self.mu, self.var))

    def mean(self):
        return self.mu

    def prob_over(self, line, samples=None, rng=None):
        """P(X > line). Summing the pmf directly beats inverting the cdf here."""
        k = math.floor(line)
        if self.var <= self.mu:
            return 1.0 - stats.poisson_cdf(k, self.mu)
        p = self.mu / self.var
        r = self.mu * p / (1.0 - p)
        prob = p ** r
        total = prob
        for i in range(1, int(k) + 1):
            prob *= (r + i - 1.0) / i * (1.0 - p)
            total += prob
        return max(0.0, 1.0 - total)


class BernoulliStat(Marginal):
    """Anytime touchdown, to record a sack, first basket."""

    name = "bernoulli"

    def __init__(self, prob):
        self.p = min(max(float(prob), 0.0), 1.0)

    def ppf(self, u):
        return 1.0 if u > (1.0 - self.p) else 0.0

    def mean(self):
        return self.p

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
    """Monte Carlo over a set of legs with an optional correlation matrix."""

    def __init__(self, legs, correlation=None, trials=50000, seed=None):
        self.legs = list(legs)
        self.trials = int(trials)
        self.rng = random.Random(seed)
        n = len(self.legs)
        if correlation is None:
            correlation = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        self.correlation = stats.nearest_correlation(correlation)
        self.copula = stats.GaussianCopula(self.correlation, rng=self.rng)

    def run(self):
        """Returns a SimResult with joint and marginal hit rates."""
        n = len(self.legs)
        all_hit = 0
        leg_hits = [0] * n
        hit_counts = [0] * (n + 1)
        for _ in range(self.trials):
            us = self.copula.sample_uniforms()
            hits = 0
            for i, leg in enumerate(self.legs):
                value = leg.marginal.ppf(us[i])
                if leg.hits(value):
                    leg_hits[i] += 1
                    hits += 1
            hit_counts[hits] += 1
            if hits == n:
                all_hit += 1
        return SimResult(self.legs, all_hit / self.trials,
                         [h / self.trials for h in leg_hits],
                         [c / self.trials for c in hit_counts],
                         self.trials, self.correlation)


class SimResult:
    def __init__(self, legs, joint_prob, leg_probs, hit_distribution, trials, correlation):
        self.legs = legs
        self.joint_prob = joint_prob
        self.leg_probs = leg_probs
        self.hit_distribution = hit_distribution
        self.trials = trials
        self.correlation = correlation

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
