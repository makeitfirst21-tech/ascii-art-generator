"""Key numbers and the price of a half point.

Walters' doctrine, made computable.

NFL scoring comes in threes and sevens, so final margins are not smooth: they
pile up on 3 and 7 and, to a lesser extent, on 6, 10 and 14. A half point is
therefore worth wildly different amounts depending on where you buy it. Moving
-3 to -2.5 is one of the most valuable half points in sports. Moving -8 to -7.5
is worth a fraction of that, and moving -11 to -10.5 barely registers.

The frequencies below are approximate historical shares of regular-season NFL
final margins, rounded to the nearest tenth of a percent. They are the right
shape and roughly the right size; they are not a fitted model of this season,
and they should be replaced with your own counts if you have them.
"""

import math

from . import odds

# Absolute final margin -> share of games. Ties included at 0.
NFL_MARGIN_PMF = {
    0: 0.004, 1: 0.040, 2: 0.035, 3: 0.095, 4: 0.045, 5: 0.035,
    6: 0.046, 7: 0.073, 8: 0.035, 9: 0.025, 10: 0.046, 11: 0.024,
    12: 0.019, 13: 0.023, 14: 0.034, 15: 0.017, 16: 0.022, 17: 0.026,
    18: 0.014, 19: 0.013, 20: 0.016, 21: 0.017, 22: 0.011, 23: 0.011,
    24: 0.012, 25: 0.008, 26: 0.008, 27: 0.007, 28: 0.007, 29: 0.005,
    30: 0.005,
}

# NBA margins are far smoother -- no scoring increment dominates -- which is
# why key-number logic is an NFL discipline and mostly noise elsewhere.
KEY_NUMBERS_NFL = (3, 7, 6, 10, 14, 4)


def margin_pmf(sport="nfl"):
    if sport.lower() != "nfl":
        raise ValueError("key-number logic is an NFL tool; other sports have "
                         "smooth margin distributions and no meaningful spikes")
    return dict(NFL_MARGIN_PMF)


def margin_mass(margin, sport="nfl"):
    """Share of games landing on exactly this absolute margin."""
    pmf = margin_pmf(sport)
    m = int(round(abs(margin)))
    if m in pmf:
        return pmf[m]
    # Beyond the table, fall back to a smooth tail with no spikes worth naming.
    tail = max(0.0, 1.0 - sum(pmf.values()))
    return tail * math.exp(-(m - 30) / 9.0) / 9.0 if m > 30 else 0.0


def is_key_number(margin, sport="nfl"):
    return int(round(abs(margin))) in KEY_NUMBERS_NFL


def points_crossed(from_spread, to_spread, favorite_share=0.60, sport="nfl"):
    """Probability mass crossed by moving a spread from one number to another.

    `favorite_share` splits an absolute margin between the favourite winning by
    it and the underdog winning by it. Roughly 0.6 for a normal favourite; push
    it toward 0.5 for a pick'em and toward 0.75 for a heavy chalk.

    Returns the probability that the result lands strictly between the two
    numbers -- which is what you gain (or give away) by moving across them.
    """
    lo, hi = sorted((float(from_spread), float(to_spread)))
    total = 0.0
    for margin in range(0, 61):
        # a margin sits "between" the numbers if it is covered by one and not
        # the other, in absolute terms
        for signed in (margin, -margin):
            if lo < signed < hi or (margin == 0 and lo < 0 < hi):
                share = favorite_share if signed > 0 else (1.0 - favorite_share)
                if margin == 0:
                    share = 1.0
                total += margin_mass(margin, sport) * share
                if margin == 0:
                    break
    return total


def half_point_value(spread, direction="toward", favorite_share=0.60, sport="nfl"):
    """What the half point on either side of this number is worth, in probability.

    Moving -3 to -2.5 converts every push at 3 into a win. Moving -3 to -3.5
    converts every push at 3 into a loss, which is why books charge so much to
    move the other way.
    """
    m = int(round(abs(spread)))
    mass = margin_mass(m, sport)
    share = favorite_share if spread < 0 else (1.0 - favorite_share)
    return mass * share


def buy_points(win_prob, push_prob, price_before, price_after, stake=1.0):
    """Is buying the half point worth the worse price?

    The only correct way to answer: price both bets properly. A push returns the
    stake, so the original bet is not a simple binary -- and ignoring that is how
    people talk themselves into paying -130 for a point that isn't there.
    """
    lose_prob = max(0.0, 1.0 - win_prob - push_prob)
    dec_before = odds.american_to_decimal(price_before)
    dec_after = odds.american_to_decimal(price_after)

    ev_before = stake * (win_prob * (dec_before - 1.0) - lose_prob)
    # after buying, the pushes become wins
    win_after = win_prob + push_prob
    ev_after = stake * (win_after * (dec_after - 1.0) - (1.0 - win_after))

    # The worst price you could pay for the bought number and still be no worse
    # off than you were. Anything shorter than this and you are donating.
    breakeven = None
    if win_after > 0:
        dec_breakeven = (1.0 + ev_before / stake) / win_after
        if dec_breakeven > 1.0:
            breakeven = odds.decimal_to_american(dec_breakeven)

    return {
        "ev_before": ev_before,
        "ev_after": ev_after,
        "gain": ev_after - ev_before,
        "worth_it": ev_after > ev_before,
        "push_prob": push_prob,
        "breakeven_price": breakeven,
    }


def key_number_report(sport="nfl", favorite_share=0.60):
    """Every number that matters, ranked, with the half point priced."""
    pmf = margin_pmf(sport)
    rows = []
    for margin, mass in sorted(pmf.items(), key=lambda kv: -kv[1]):
        if margin == 0:
            continue
        rows.append({
            "margin": margin,
            "mass": mass,
            "key": is_key_number(margin, sport),
            "half_point_prob": mass * favorite_share,
            "half_point_cents": _cents_for(mass * favorite_share),
        })
    return rows


def _cents_for(prob_gain, base_prob=0.5):
    """Roughly how many cents of price a probability gain is worth at a coin flip."""
    if prob_gain <= 0:
        return 0
    return abs(odds.cents_between(odds.prob_to_american(base_prob + prob_gain),
                                 odds.prob_to_american(base_prob)))
