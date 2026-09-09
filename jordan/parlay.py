"""Leg grading and parlay verdicts.

Jordan's actual job. Two questions, in order:

  1. Is this leg, on its own, a bet? (Almost always: no.)
  2. If several legs are going together, does the correlation between them beat
     the price the book put on the combination? (Rarely: yes.)

Everything else is decoration.
"""

import math

from . import odds, simulate, correlation
from .stats import wilson_interval

# ---------------------------------------------------------------------------
# Grading a single leg as parlay material.
#
# A leg can be a fine straight bet and terrible parlay material -- a coin-flip
# alternate line at -110 with a real 1% edge is a bet, but stack six of them and
# the vig eats the edge four times over. What makes a leg good *in a parlay* is
# different: a stable driver, a line near the meat of the distribution, a price
# the market agrees with, and something to correlate with.
# ---------------------------------------------------------------------------

GRADE_BANDS = [
    (85, "A", "Core piece. Build around it."),
    (72, "B", "Solid. Fine alongside a correlated partner."),
    (60, "C", "Playable filler. Don't let it be the reason for the ticket."),
    (45, "D", "Weak. You are paying for variance."),
    (0,  "F", "Do not put this in a parlay."),
]


def _band(score):
    for cut, letter, note in GRADE_BANDS:
        if score >= cut:
            return letter, note
    return "F", GRADE_BANDS[-1][2]


class LegGrade:
    def __init__(self, leg, score, components, prob, ev_pct, notes):
        self.leg = leg
        self.score = score
        self.components = components
        self.prob = prob
        self.ev_pct = ev_pct
        self.notes = notes
        self.letter, self.band_note = _band(score)

    def __repr__(self):
        return "<LegGrade %s %s %.0f>" % (self.leg.label, self.letter, self.score)


def grade_leg(leg, usage_stability=0.6, signal_strength=0.0, devig_method="power",
              correlation_potential=0.0):
    """Score a leg 0-100 as parlay material.

    usage_stability      0-1: how reliable the leg's *driver* is. A three-down
                         back on a 60% snap share is 0.85; a WR3 whose targets
                         swing with coverage is 0.35. This is the number most
                         bettors never think about and it decides more parlays
                         than the projection does.
    signal_strength      0-1: from the market module. Does live money agree?
    correlation_potential 0-1: how well this leg stacks with the rest of the
                         ticket. Set by the parlay builder.
    """
    prob = leg.blended_prob(devig_method)
    ev = odds.ev_percent(prob, leg.price)
    notes = []

    # 1. Raw edge. Anything under 2% is inside the error bars of the projection.
    edge_score = max(0.0, min(1.0, (ev + 2.0) / 10.0))
    if ev < 0:
        notes.append("Negative EV on its own (%.1f%%) -- only justifiable as a "
                     "correlated leg." % ev)
    elif ev < 2.0:
        notes.append("Edge (%.1f%%) is inside model error; treat as a coin flip." % ev)

    # 2. Distance from the projection, in standard deviations. Legs far out on
    #    the tail are lottery tickets no matter how nice the price looks.
    z = 0.0
    m = leg.marginal
    if hasattr(m, "mu") and hasattr(m, "sigma") and m.sigma:
        z = (leg.line - m.mu) / m.sigma
    elif hasattr(m, "mean") and callable(m.mean):
        mean = m.mean()
        if mean:
            z = (leg.line - mean) / max(math.sqrt(abs(mean)) * 1.2, 1e-9)
    tail = abs(z)
    tail_score = max(0.0, 1.0 - max(0.0, tail - 0.35) / 1.6)
    if tail > 1.25:
        notes.append("Line sits %.1f sd from the projection -- this is a tail bet, "
                     "not a value bet." % tail)

    # 3. Driver stability.
    stability_score = max(0.0, min(1.0, usage_stability))
    if usage_stability < 0.45:
        notes.append("Volatile driver (snaps/minutes/targets). One early "
                     "substitution kills the leg.")

    # 4. Market agreement.
    signal_score = max(0.0, min(1.0, signal_strength))

    # 5. Price efficiency: how much juice you are paying.
    juice = 0.0
    if leg.market_prices and len(leg.market_prices) >= 2:
        juice = odds.hold(leg.market_prices)
        if juice > 0.09:
            notes.append("Fat market (%.1f%% hold) -- the book is charging for "
                         "uncertainty it hasn't resolved." % (100 * juice))
    price_score = max(0.0, 1.0 - juice / 0.12)

    # 6. Correlation potential.
    corr_score = max(0.0, min(1.0, correlation_potential))

    components = {
        "edge": edge_score,
        "line_placement": tail_score,
        "driver_stability": stability_score,
        "market_agreement": signal_score,
        "price_efficiency": price_score,
        "correlation_fit": corr_score,
    }
    weights = {
        "edge": 0.30,
        "line_placement": 0.16,
        "driver_stability": 0.20,
        "market_agreement": 0.12,
        "price_efficiency": 0.10,
        "correlation_fit": 0.12,
    }
    score = 100.0 * sum(components[k] * weights[k] for k in weights)
    return LegGrade(leg, score, components, prob, ev, notes)


# ---------------------------------------------------------------------------
# The parlay itself.
# ---------------------------------------------------------------------------


class ParlayReport:
    def __init__(self, legs, grades, sim, offered_price, book_price_implied,
                 true_prob, ev_pct, kelly, verdict, reasons, bankroll):
        self.legs = legs
        self.grades = grades
        self.sim = sim
        self.offered_price = offered_price
        self.book_price_implied = book_price_implied
        self.true_prob = true_prob
        self.ev_pct = ev_pct
        self.kelly = kelly
        self.verdict = verdict
        self.reasons = reasons
        self.bankroll = bankroll

    @property
    def fair_price(self):
        return odds.prob_to_american(self.true_prob) if self.true_prob > 0 else None

    def render(self, width=78):
        line = "=" * width
        thin = "-" * width
        out = [line, "JORDAN -- PARLAY REPORT".center(width), line, ""]
        out.append("LEGS")
        out.append(thin)
        for g in self.grades:
            leg = g.leg
            out.append("  %-34s %-5s %6s   %5.1f%% true   EV %+6.2f%%   grade %s (%.0f)"
                       % (leg.label[:34],
                          leg.side,
                          odds.fmt_american(leg.price),
                          100 * g.prob,
                          g.ev_pct,
                          g.letter,
                          g.score))
            for note in g.notes:
                out.append("      - " + note)
        out.append("")

        pairs = correlation.describe_matrix(self.sim.correlation,
                                            [l.label for l in self.legs])
        if pairs:
            out.append("CORRELATION")
            out.append(thin)
            for rho, a, b in pairs[:8]:
                tag = ("helps" if rho > 0.08 else "hurts" if rho < -0.08 else "independent")
                out.append("  %-26s x %-26s %+.2f  (%s)" % (a[:26], b[:26], rho, tag))
            out.append("")

        out.append("PRICING")
        out.append(thin)
        out.append("  Book price ................ %s (implied %.2f%%)"
                   % (odds.fmt_american(self.offered_price), 100 * self.book_price_implied))
        out.append("  Independent legs .......... %.2f%%" % (100 * self.sim.independent_prob))
        out.append("  True joint (correlated) ... %.2f%%  +/- %.2f%%"
                   % (100 * self.true_prob, 100 * 1.96 * self.sim.standard_error))
        out.append("  Correlation multiplier .... %.3fx" % self.sim.correlation_multiplier)
        if self.fair_price:
            out.append("  Fair price ................ %s" % odds.fmt_american(self.fair_price))
        else:
            out.append("  Fair price ................ n/a (never hit in simulation)")
        out.append("  Expected value ............ %+.2f%%" % self.ev_pct)
        out.append("  Full Kelly ................ %.2f%% of bankroll" % (100 * self.kelly))
        stake = odds.kelly_stake(self.true_prob, self.offered_price, self.bankroll)
        units = 100.0 * stake / self.bankroll if self.bankroll else 0.0
        out.append("  Recommended stake ......... %.2f of a %.2f bankroll "
                   "(%.2f units, quarter Kelly, 2%% cap)"
                   % (stake, self.bankroll, units))
        out.append("")

        out.append("HIT DISTRIBUTION")
        out.append(thin)
        n = len(self.legs)
        for k in range(n, -1, -1):
            p = self.sim.hit_distribution[k]
            bar = "#" * int(round(p * 40))
            out.append("  %d/%d legs  %5.1f%%  %s" % (k, n, 100 * p, bar))
        out.append("")

        out.append("VERDICT: " + self.verdict)
        out.append(thin)
        for r in self.reasons:
            out.append("  * " + r)
        out.append(line)
        return "\n".join(out)


def analyse_parlay(legs, offered_price=None, sport="nfl", overrides=None,
                   relationships=None, bankroll=100.0, trials=40000, seed=None,
                   stability=None, signals=None, devig_method="power"):
    """Full parlay analysis: correlation, simulation, pricing, verdict.

    `offered_price` is the book's actual same-game-parlay price. Leave it None
    and the straight-multiplication price is assumed, which is what you get on
    an uncorrelated cross-game parlay.
    """
    matrix = correlation.build_matrix(legs, sport, overrides, relationships)
    sim = simulate.Simulation(legs, matrix, trials=trials, seed=seed).run()

    if offered_price is None:
        offered_price = odds.parlay_american([l.price for l in legs])

    true_prob = sim.joint_prob
    book_implied = odds.american_to_prob(offered_price)
    ev = odds.ev_percent(true_prob, offered_price)
    kelly = odds.kelly_fraction(true_prob, offered_price)

    # correlation potential per leg = mean |rho| with the rest of the ticket
    n = len(legs)
    stability = stability or {}
    signals = signals or {}
    grades = []
    for i, leg in enumerate(legs):
        if n > 1:
            corr_pot = sum(abs(matrix[i][j]) for j in range(n) if j != i) / (n - 1)
        else:
            corr_pot = 0.0
        grades.append(grade_leg(
            leg,
            usage_stability=stability.get(leg.label, 0.6),
            signal_strength=signals.get(leg.label, 0.0),
            devig_method=devig_method,
            correlation_potential=min(corr_pot / 0.5, 1.0)))

    verdict, reasons = _verdict(legs, grades, sim, ev, offered_price, true_prob)
    return ParlayReport(legs, grades, sim, offered_price, book_implied, true_prob,
                        ev, kelly, verdict, reasons, bankroll)


def _verdict(legs, grades, sim, ev, offered_price, true_prob):
    """Tier the ticket on EV, then downgrade it for the things EV can't see.

    EV alone is a seductive number: it is only as good as the projection behind
    it. A ticket showing +12% built on three legs Jordan is guessing at is worse
    than one showing +4% built on legs he can defend. So the EV sets the tier and
    the weaknesses take it back down.
    """
    reasons = []
    n = len(legs)
    mult = sim.correlation_multiplier
    se = sim.standard_error
    edge_prob = true_prob - odds.american_to_prob(offered_price)

    TIERS = ["PLAY", "THIN -- small stake only", "PASS", "NO BET"]
    if ev > 4.0:
        tier = 0
    elif ev > 0.5:
        tier = 1
    elif ev > -2.0:
        tier = 2
    else:
        tier = 3
    base_tier = tier

    # -- downgrades ---------------------------------------------------------
    if abs(edge_prob) < 2.0 * se and tier < 2:
        tier = 2
        reasons.append("Estimated edge (%.2f%%) sits inside simulation error "
                       "(+/-%.2f%%). That is not an edge, that is noise."
                       % (100 * edge_prob, 100 * 1.96 * se))

    weak = [g for g in grades if g.score < 60]
    if weak and tier < 3:
        tier += 1
        reasons.append("Downgraded for weak legs: %s. The EV is real only if those "
                       "projections are, and they are the ones Jordan trusts least."
                       % ", ".join("%s (%s)" % (g.leg.label, g.letter) for g in weak))

    negatives = [g for g in grades if g.ev_pct < 0]
    if len(negatives) == n and n > 1:
        reasons.append("Every leg is -EV standalone. Correlation has to carry the "
                       "entire ticket, and it rarely carries that much weight.")

    if n >= 5 and tier < 3:
        tier += 1
        reasons.append("%d legs. Effective hold on a ticket this long is punishing "
                       "even when every leg is sharp -- shorten it." % n)

    verdict = TIERS[min(tier, 3)]

    # -- headline, matched to the tier actually assigned ---------------------
    if tier == 0:
        headline = ("Priced %+.2f%% to the good with legs Jordan can defend. This is "
                    "the rare parlay that is actually a bet." % ev)
    elif tier == 1:
        headline = ("Playable at %+.2f%%, but small. A parlay edge this size "
                    "disappears with one bad correlation assumption." % ev)
    elif tier == 2:
        headline = ("Not enough here (%+.2f%% before accounting for being wrong). "
                    "No reason to take the variance." % ev)
    else:
        headline = ("Clearly -EV (%+.2f%%). The book is selling this for a reason." % ev)
    if tier > base_tier:
        headline += (" Raw EV alone would have graded this %s." % TIERS[base_tier])
    reasons.insert(0, headline)

    # -- correlation commentary --------------------------------------------
    if mult > 1.10:
        reasons.append("Legs are positively correlated (%.2fx). If the book priced this "
                       "as independent legs, that gap is the whole edge." % mult)
    elif mult < 0.92:
        reasons.append("Legs fight each other (%.2fx). You are being sold a combination "
                       "that is less likely than the sum of its parts." % mult)
    else:
        reasons.append("Legs are effectively independent (%.2fx) -- no correlation edge, "
                       "so this is just compounded vig." % mult)

    return verdict, reasons


def best_subset(legs, sport="nfl", overrides=None, relationships=None,
                min_legs=2, max_legs=None, trials=15000, seed=7, bankroll=100.0):
    """Search every subset of the legs for the highest-EV construction.

    Usually returns something shorter than what you walked in with. That is the
    correct answer more often than anyone wants to hear.
    """
    from itertools import combinations
    n = len(legs)
    max_legs = max_legs or n
    best = None
    results = []
    index = {id(l): i for i, l in enumerate(legs)}
    for size in range(min_legs, min(max_legs, n) + 1):
        for combo in combinations(legs, size):
            sub_over = {}
            sub_rel = {}
            if overrides:
                for (a, b), v in overrides.items():
                    ids = [index[id(l)] for l in combo]
                    if a in ids and b in ids:
                        sub_over[(ids.index(a), ids.index(b))] = v
            if relationships:
                for (a, b), v in relationships.items():
                    ids = [index[id(l)] for l in combo]
                    if a in ids and b in ids:
                        sub_rel[(ids.index(a), ids.index(b))] = v
            rep = analyse_parlay(list(combo), sport=sport, overrides=sub_over,
                                 relationships=sub_rel, trials=trials, seed=seed,
                                 bankroll=bankroll)
            results.append(rep)
            if best is None or rep.ev_pct > best.ev_pct:
                best = rep
    results.sort(key=lambda r: -r.ev_pct)
    return best, results


def record_grade(wins, losses, pushes=0):
    """What a betting record actually proves. Usually: nothing yet."""
    n = wins + losses
    if n == 0:
        return {"n": 0, "note": "No completed bets."}
    lo, hi = wilson_interval(wins, n)
    breakeven = 0.5238   # -110
    return {
        "n": n,
        "win_pct": 100.0 * wins / n,
        "ci_low": 100.0 * lo,
        "ci_high": 100.0 * hi,
        "breakeven_pct": 100.0 * breakeven,
        "proven_winner": lo > breakeven,
        "note": ("Even the low end of the confidence interval clears the -110 "
                 "break-even. That is a real edge."
                 if lo > breakeven else
                 "The confidence interval still contains break-even (%.1f%%-%.1f%%). "
                 "This record does not yet prove anything -- you need roughly "
                 "%d more bets at this rate to know."
                 % (100 * lo, 100 * hi, max(0, int(2500 - n)))),
    }
