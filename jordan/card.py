"""The daily card.

One pick a day, every day, whatever is on. Two things are deliberately kept
apart here, because conflating them is how people lose money:

    THE FORECAST   Jordan names a game and states a probability, every single
                   day, whether or not there is a bet in it. That number goes in
                   the ledger and gets scored on Brier and log loss. Forecasting
                   is a skill you practise daily.

    THE BET        Whether any money goes down. Most days the answer is no,
                   because the price does not clear the edge required after the
                   research gaps are accounted for. A forecast is free; a bet
                   is not.

So the card always produces something to grade and usually produces nothing to
back. That is not a bug -- it is the difference between the two disciplines.
"""

from . import odds, research
from .persona import BANKROLL

# Minimum edge required before Jordan will stake anything, by how much of the
# research checklist is filled. Thin information demands a fatter edge.
EDGE_FLOOR = [
    (0.90, 0.020),   # everything known: 2% edge is enough
    (0.75, 0.035),
    (0.60, 0.060),
    (0.00, 1.000),   # below 60% complete: no edge is enough
]


# How much Jordan trusts his own number against the market's. The ceiling is the
# same even split a simulate.Leg uses by default; it scales down with research
# completeness, because a number built on two-thirds of the facts has not earned
# half the say. The market gets the rest.
MODEL_WEIGHT_MAX = 0.5

# Overround assumed when only one side of a market is posted -- anytime TD,
# player to score, first basket. US books typically run 6-8% on these. Assuming
# too much is the safe direction: it lowers the market's fair number and with it
# the blended probability Jordan is allowed to bet.
ONE_SIDED_OVERROUND = 0.07


def model_weight(completeness):
    return MODEL_WEIGHT_MAX * min(max(completeness, 0.0), 1.0)


def fair_prob_one_sided(price, overround=ONE_SIDED_OVERROUND):
    """The market's no-vig probability when you can only see one side.

    Synthesises the hidden side from an assumed overround and de-vigs the pair
    the same way a two-way market would be, so longshots carry their share of
    the favourite-longshot bias instead of an even split of the vig.
    """
    shown = odds.american_to_prob(price)
    hidden = 1.0 + overround - shown
    if hidden >= 0.999:
        # Past roughly +1300 the hidden side would need to be a certainty. Fall
        # back to taking the whole overround proportionally off the shown side.
        return shown / (1.0 + overround)
    prices = [price, odds.prob_to_american(hidden)]
    return odds.devig(prices, odds.recommended_devig(prices))[0]


def required_edge(completeness):
    for threshold, floor in EDGE_FLOOR:
        if completeness >= threshold:
            return floor
    return 1.0


class Candidate:
    """One thing Jordan could bet, with a stated probability behind it.

    `market_prices` is the full two-way market, ideally from a sharp book. When
    it is missing, the offered price stands in for the market -- a soft price
    that is a genuine outlier gets under-credited that way, which is why the
    sharp market is worth supplying. `known` overrides the card's research list
    for this candidate alone. `price_verified` is False for a price that was
    estimated rather than read off a book: it can be forecast, never bet.
    """

    def __init__(self, description, price, prob, sport="generic",
                 market_prices=None, book=None, notes=None, known=None,
                 price_verified=True, overround=ONE_SIDED_OVERROUND):
        self.description = description
        self.price = float(price)
        self.prob = float(prob)
        self.sport = sport
        self.market_prices = market_prices
        self.book = book
        self.notes = notes
        self.known = known
        self.price_verified = bool(price_verified)
        self.overround = overround
        # Filled in by build(), once the research state is known.
        self.conf = None
        self.weight = None
        self.blended = None

    @property
    def market_prob(self):
        if self.market_prices:
            return odds.devig(self.market_prices,
                              odds.recommended_devig(self.market_prices))[0]
        return fair_prob_one_sided(self.price, self.overround)

    @property
    def market_source(self):
        if self.market_prices:
            return "de-vigged two-way market"
        return "inferred from the price, %.0f%% overround assumed" % (100 * self.overround)

    def blended_prob(self, completeness):
        w = model_weight(completeness)
        return w * self.prob + (1.0 - w) * self.market_prob

    @property
    def ev_pct(self):
        return odds.ev_percent(self.prob, self.price)

    @property
    def blended_ev_pct(self):
        return odds.ev_percent(self.blended, self.price)

    @property
    def edge(self):
        """Probability edge over the price's break-even."""
        return self.prob - odds.breakeven_prob(self.price)

    def disagreement(self):
        """How far Jordan's number sits from the market's own."""
        mk = self.market_prob
        return None if mk is None else self.prob - mk

    @classmethod
    def from_spec(cls, spec):
        return cls(spec.get("description", "unnamed"), spec["price"],
                   spec["prob"], spec.get("sport", "generic"),
                   spec.get("market"), spec.get("book"), spec.get("notes"),
                   spec.get("known"), spec.get("price_verified", True),
                   spec.get("overround", ONE_SIDED_OVERROUND))


class Card:
    def __init__(self, date, pick, candidates, conf, stake, verdict, reasons,
                 bankroll):
        self.date = date
        self.pick = pick
        self.candidates = candidates
        self.confidence = conf
        self.stake = stake
        self.verdict = verdict
        self.reasons = reasons
        self.bankroll = bankroll

    def render(self, width=78):
        line, thin = "=" * width, "-" * width
        out = [line, ("JORDAN'S CARD -- %s" % self.date).center(width), line, ""]

        p = self.pick
        out.append("THE FORECAST  (graded whether or not it is bet)")
        out.append(thin)
        out.append("  %s" % p.description)
        out.append("  Sport ................ %s" % p.sport)
        out.append("  Price ................ %s at %s%s"
                   % (odds.fmt_american(p.price), p.book or "unspecified book",
                      "" if p.price_verified else "  (ESTIMATED -- verify)"))
        out.append("  Jordan's probability .. %.1f%%" % (100 * p.prob))
        mk = p.market_prob
        if mk is not None:
            out.append("  Market's probability .. %.1f%%  (%s)"
                       % (100 * mk, p.market_source))
            out.append("  Disagreement .......... %+.1f points -- this is the "
                       "entire claim" % (100 * p.disagreement()))
        out.append("  Break-even at price ... %.1f%%"
                   % (100 * odds.breakeven_prob(p.price)))
        out.append("  Edge .................. %+.1f points   EV %+.2f%%"
                   % (100 * p.edge, p.ev_pct))
        out.append("  Blended ............... %.1f%%  (%.0f%% Jordan, %.0f%% market)"
                   "   EV %+.2f%%"
                   % (100 * p.blended, 100 * p.weight, 100 * (1 - p.weight),
                      p.blended_ev_pct))
        out.append("")

        c = self.confidence
        out.append("INFORMATION")
        out.append(thin)
        out.append("  Research completeness . %.0f%%  (%s)"
                   % (100 * c["completeness"], c["label"]))
        out.append("  Edge required to bet .. %.1f points"
                   % (100 * required_edge(c["completeness"])))
        if c["missing"]:
            out.append("  Still unknown ......... %s" % "; ".join(c["missing"]))
        out.append("  %s" % c["note"])
        out.append("")

        out.append("THE BET")
        out.append(thin)
        out.append("  Verdict ............... %s" % self.verdict)
        if self.stake > 0:
            out.append("  Stake ................. %.2f units (%.2f on a %.0f "
                       "bankroll)" % (100 * self.stake / self.bankroll
                                      if self.bankroll else 0,
                                      self.stake, self.bankroll))
        else:
            out.append("  Stake ................. 0 units")
        for r in self.reasons:
            out.append("  * %s" % r)
        out.append("")

        if len(self.candidates) > 1:
            out.append("ALSO CONSIDERED%sJORDAN  MARKET   EV raw  blended"
                       % (" " * 30))
            out.append(thin)
            for cand in self.candidates[1:]:
                out.append("  %-36s %6s%s %5.1f%%  %5.1f%%  %+6.1f%%  %+6.1f%%"
                           % (cand.description[:36], odds.fmt_american(cand.price),
                              " " if cand.price_verified else "*",
                              100 * cand.prob, 100 * cand.market_prob,
                              cand.ev_pct, cand.blended_ev_pct))
            if not all(c.price_verified for c in self.candidates[1:]):
                out.append("  * estimated price -- verify before trusting the EV")
            out.append("")
        out.append(line)
        return "\n".join(out)


def build(candidates, date, sport=None, known=None, bankroll=1000.0):
    """Rank the board, apply the information gate, produce a card.

    Every candidate is judged on its blended probability -- Jordan's number
    pulled toward the market's by however little research backs it. Ranking on
    raw EV instead would crown whichever estimate strays furthest from the
    market, which is usually the one with the biggest error in it.

    The top candidate becomes the forecast regardless of whether it is
    bettable. The stake is decided separately.
    """
    if not candidates:
        raise ValueError("no candidates -- give Jordan something to price")
    for c in candidates:
        c.conf = research.confidence(sport or c.sport,
                                     c.known if c.known is not None else known)
        c.weight = model_weight(c.conf["completeness"])
        c.blended = c.blended_prob(c.conf["completeness"])
    ranked = sorted(candidates, key=lambda c: -c.blended_ev_pct)
    pick = ranked[0]
    conf = pick.conf
    floor = required_edge(conf["completeness"])

    reasons = []
    stake = 0.0
    if not pick.price_verified:
        verdict = "NO BET -- price not verified"
        reasons.append("%s is an estimate, not a price read off a book. Check it "
                       "in your app; every number below depends on it."
                       % odds.fmt_american(pick.price))
    elif pick.ev_pct <= 0:
        verdict = "NO BET"
        reasons.append("Best thing on the board is %+.2f%%. Nothing here is a bet, "
                       "which is the normal answer." % pick.ev_pct)
    elif pick.blended_ev_pct <= 0:
        verdict = "NO BET -- the edge is all disagreement"
        reasons.append("%+.2f%% on Jordan's number, %+.2f%% once it is weighted "
                       "against the market's %.1f%%. The whole edge is the claim "
                       "that the market is wrong, and at %.0f%% research that "
                       "claim only gets %.0f%% of the say."
                       % (pick.ev_pct, pick.blended_ev_pct, 100 * pick.market_prob,
                          100 * conf["completeness"], 100 * pick.weight))
    elif pick.edge < floor:
        verdict = "NO BET -- edge too thin for what we know"
        reasons.append("Edge is %.1f points; %.1f is required at %.0f%% research "
                       "completeness. Fill the gaps or pass."
                       % (100 * pick.edge, 100 * floor, 100 * conf["completeness"]))
    elif conf["stake_multiplier"] <= 0:
        verdict = "NO BET -- not enough information"
        reasons.append("The number may be right, but %s is still unknown. Jordan "
                       "does not bet blind."
                       % (conf["missing"][0].lower() if conf["missing"] else "too much"))
    else:
        full = odds.kelly_stake(pick.blended, pick.price, bankroll,
                                multiplier=BANKROLL["kelly_multiplier"],
                                cap=BANKROLL["single_bet_cap"])
        stake = full * conf["stake_multiplier"]
        verdict = "BET"
        reasons.append("Edge of %.1f points clears the %.1f-point floor at %.0f%% "
                       "research completeness, and survives weighting against "
                       "the market (%+.2f%% blended)."
                       % (100 * pick.edge, 100 * floor, 100 * conf["completeness"],
                          pick.blended_ev_pct))
        reasons.append("Quarter Kelly on the blended probability, capped at 2%% "
                       "of bankroll, then scaled to %.0f%% for the information gaps."
                       % (100 * conf["stake_multiplier"]))

    if pick.disagreement() is not None and abs(pick.disagreement()) > 0.08:
        reasons.append("Jordan disagrees with the market by %.1f points. That is a "
                       "large claim -- it is usually the model that is wrong, so "
                       "check the inputs before the stake."
                       % (100 * abs(pick.disagreement())))

    reasons.append("The forecast is logged either way. Betting and forecasting are "
                   "separate skills and only one of them is free.")
    return Card(date, pick, ranked, conf, stake, verdict, reasons, bankroll)
