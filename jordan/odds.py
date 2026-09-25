"""Odds conversion, de-vigging, EV and stake sizing.

Everything Jordan says about a bet eventually reduces to two numbers: the price
the book is offering, and the probability Jordan actually believes. This module
owns the plumbing between them.
"""

import math

# ---------------------------------------------------------------- conversions


def american_to_decimal(american):
    """-110 -> 1.909, +150 -> 2.50"""
    american = float(american)
    if american == 0:
        raise ValueError("american odds of 0 are not a price")
    if american > 0:
        return 1.0 + american / 100.0
    return 1.0 + 100.0 / abs(american)


def decimal_to_american(decimal):
    """1.909 -> -110, 2.50 -> +150"""
    decimal = float(decimal)
    if decimal <= 1.0:
        raise ValueError("decimal odds must exceed 1.0")
    if decimal >= 2.0:
        return round((decimal - 1.0) * 100.0)
    return round(-100.0 / (decimal - 1.0))


def american_to_prob(american):
    """Implied probability *including* the vig."""
    return 1.0 / american_to_decimal(american)


def prob_to_decimal(prob):
    if not 0.0 < prob < 1.0:
        raise ValueError("probability must be strictly between 0 and 1")
    return 1.0 / prob


def prob_to_american(prob):
    return decimal_to_american(prob_to_decimal(prob))


def fmt_american(american):
    american = int(round(american))
    return "+%d" % american if american > 0 else "%d" % american


def hold(prices):
    """Book hold (juice) on a market: sum of implied probs minus 1."""
    return sum(american_to_prob(p) for p in prices) - 1.0


# ------------------------------------------------------------------- de-vigging
#
# A two-way market priced -110/-110 implies 52.4% + 52.4% = 104.8%. The 4.8% is
# the book's hold. Removing it -- "de-vigging" -- is the single highest-leverage
# calculation in betting, and *how* you remove it matters more than most bettors
# think. On a longshot prop the method choice can move the fair number by
# several cents.


def devig_multiplicative(prices):
    """Proportional / normalised de-vig. Fast, and right for tight markets."""
    raw = [american_to_prob(p) for p in prices]
    total = sum(raw)
    return [r / total for r in raw]


def devig_additive(prices):
    """Spread the hold evenly in probability space.

    Charges the favourite and the longshot the same number of points of vig,
    which is usually too generous to the longshot.
    """
    raw = [american_to_prob(p) for p in prices]
    excess = (sum(raw) - 1.0) / len(raw)
    out = [max(r - excess, 1e-6) for r in raw]
    total = sum(out)
    return [o / total for o in out]


def devig_power(prices, tol=1e-12, max_iter=200):
    """Solve for k with sum(raw_i ** k) == 1.

    Books apply proportionally *more* vig to longshots (the favourite-longshot
    bias). The power method reproduces that shape, so it is the right default
    for player props and any market with a leg priced longer than about +200.
    """
    raw = [american_to_prob(p) for p in prices]
    lo, hi = 0.05, 10.0
    for _ in range(max_iter):
        k = 0.5 * (lo + hi)
        total = sum(r ** k for r in raw)
        if abs(total - 1.0) < tol:
            break
        if total > 1.0:
            lo = k  # need a larger exponent to shrink probabilities
        else:
            hi = k
    out = [r ** k for r in raw]
    total = sum(out)
    return [o / total for o in out]


def devig_shin(prices, tol=1e-12, max_iter=200):
    """Shin (1993): assumes the hold is compensation for insider money.

    Solves for the insider fraction z, then backs out the fair probabilities.
    Behaves between multiplicative and power; favoured by a lot of quant shops.
    """
    raw = [american_to_prob(p) for p in prices]
    total_raw = sum(raw)
    normalised = [r / total_raw for r in raw]

    def probs_for(z):
        if z <= 0:
            return list(normalised)
        out = []
        for q in normalised:
            root = math.sqrt(z * z + 4.0 * (1.0 - z) * q * q * total_raw)
            out.append((root - z) / (2.0 * (1.0 - z)))
        return out

    lo, hi = 0.0, 0.5
    for _ in range(max_iter):
        z = 0.5 * (lo + hi)
        s = sum(probs_for(z))
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            lo = z
        else:
            hi = z
    out = probs_for(z)
    total = sum(out)
    return [o / total for o in out]


DEVIG_METHODS = {
    "multiplicative": devig_multiplicative,
    "additive": devig_additive,
    "power": devig_power,
    "shin": devig_shin,
}


def conservative_probs(prices):
    """The paranoid line: for each side, the *least* favourable fair probability
    any method gives it.

    Walters' instinct in one function -- if a bet is only +EV under the
    friendliest de-vig assumption, it is not a bet.

    Deliberately NOT a probability distribution: the returned numbers sum to
    less than 1, because every side is being quoted pessimistically at once and
    they cannot all be right. That is the point. Use it to stress-test an edge,
    never as an input to a simulation.
    """
    methods = (devig_multiplicative(prices), devig_power(prices), devig_shin(prices))
    return [min(m[i] for m in methods) for i in range(len(prices))]


def survives_every_devig(prices, index=0, min_ev=0.0):
    """Is this side still +EV under every de-vig method, including the worst?

    The question Jordan asks before any real money moves.
    """
    price = prices[index]
    results = {}
    for name, fn in DEVIG_METHODS.items():
        results[name] = ev_percent(fn(prices)[index], price)
    results["conservative"] = ev_percent(conservative_probs(prices)[index], price)
    return {
        "by_method": results,
        "worst_ev": min(results.values()),
        "survives": min(results.values()) > min_ev,
    }


def devig(prices, method="power"):
    if method not in DEVIG_METHODS:
        raise ValueError("unknown de-vig method %r (have: %s)"
                         % (method, ", ".join(sorted(DEVIG_METHODS))))
    return DEVIG_METHODS[method](prices)


def fair_price(prices, method="power", index=0):
    """Fair (no-vig) american price for one side of a market."""
    return prob_to_american(devig(prices, method)[index])


def recommended_devig(prices):
    """Pick a method the way a human would: by market shape."""
    longest = max(prices)
    n = len(prices)
    if n > 2:
        return "power"      # multiway markets are longshot-heavy by nature
    if longest >= 200:
        return "power"      # favourite-longshot bias is live
    if hold(prices) > 0.08:
        return "shin"       # fat hold, assume some of it is information
    return "multiplicative"


# ----------------------------------------------------------------- EV & sizing


def expected_value(prob, american, stake=1.0):
    """Expected profit per `stake` units at this price and this true probability."""
    dec = american_to_decimal(american)
    return stake * (prob * (dec - 1.0) - (1.0 - prob))


def ev_percent(prob, american):
    return 100.0 * expected_value(prob, american)


def cents_scale(american):
    """Map an american price onto a continuous scale where cents are subtractable.

    American odds have a discontinuity at the century: +100 and -100 are the
    same price, but they are 200 apart as integers. Subtract two prices that
    straddle it and you get nonsense -- -110 against a +100 fair number is ten
    cents of juice, not two hundred and ten.

    This maps positive prices to themselves and negative prices to
    200 - |price|, giving one monotone axis: -150 -> 50, -110 -> 90,
    +/-100 -> 100, +110 -> 110. Differences on it are cents.
    """
    american = float(american)
    return american if american > 0 else 200.0 + american


def cents_between(price_a, price_b):
    """Signed cents from price_b to price_a. Positive means price_a is better."""
    return cents_scale(price_a) - cents_scale(price_b)


def edge_in_cents(prob, american):
    """How many cents of price the bettor is getting over fair.

    Reported the way traders talk: "I got +140 on a +125 fair number, 15 cents."
    """
    return cents_between(american, prob_to_american(prob))


def kelly_fraction(prob, american):
    """Full-Kelly stake as a fraction of bankroll. Negative means no bet."""
    b = american_to_decimal(american) - 1.0
    if b <= 0:
        return 0.0
    return (prob * b - (1.0 - prob)) / b


def kelly_stake(prob, american, bankroll, multiplier=0.25, cap=0.02):
    """Fractional Kelly with a hard cap.

    Full Kelly is theoretically optimal and practically insane: it assumes your
    probability estimate is exactly right. Every long-term winner in this book's
    lineage bets a fraction of it. Quarter-Kelly with a 2% cap is the default.
    """
    f = kelly_fraction(prob, american)
    if f <= 0:
        return 0.0
    return min(f * multiplier, cap) * bankroll


# ------------------------------------------------------------------ parlay math


def parlay_decimal(prices):
    """Book's parlay price = product of the leg decimals (straight parlays)."""
    dec = 1.0
    for p in prices:
        dec *= american_to_decimal(p)
    return dec


def parlay_american(prices):
    return decimal_to_american(parlay_decimal(prices))


def parlay_hold(markets, method="power"):
    """Effective hold on an uncorrelated parlay -- the number that kills people.

    `markets` is a list of two-way (or multiway) price lists, one per leg, with
    the bet side first: [[-110, -110], [+120, -145], ...]. Each leg is de-vigged
    on its own market, and the true product is compared to what the parlay pays.

    Each leg's vig compounds. Six -110 legs turn a 4.5%-hold market into a
    ~24%-hold market, which is why the shops that buy billboards advertise
    parlays and the shops that take Jordan's action do not.
    """
    fair = 1.0
    prices = []
    for market in markets:
        fair *= devig(market, method)[0]
        prices.append(market[0])
    return 1.0 - fair * parlay_decimal(prices)


def parlay_ev(true_prob, prices, stake=1.0):
    """EV of a parlay given Jordan's own joint probability for all legs hitting.

    `true_prob` is the *joint* probability -- for correlated legs that is not
    the product of the leg probabilities, which is the entire point of the
    correlation module.
    """
    return expected_value(true_prob, parlay_american(prices), stake)


def breakeven_prob(american):
    return 1.0 / american_to_decimal(american)
