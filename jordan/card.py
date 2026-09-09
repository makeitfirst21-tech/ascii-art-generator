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


def required_edge(completeness):
    for threshold, floor in EDGE_FLOOR:
        if completeness >= threshold:
            return floor
    return 1.0


class Candidate:
    """One thing Jordan could bet, with a stated probability behind it."""

    def __init__(self, description, price, prob, sport="generic",
                 market_prices=None, book=None, notes=None):
        self.description = description
        self.price = float(price)
        self.prob = float(prob)
        self.sport = sport
        self.market_prices = market_prices
        self.book = book
        self.notes = notes

    @property
    def market_prob(self):
        if not self.market_prices:
            return None
        return odds.devig(self.market_prices,
                          odds.recommended_devig(self.market_prices))[0]

    @property
    def ev_pct(self):
        return odds.ev_percent(self.prob, self.price)

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
                   spec.get("market"), spec.get("book"), spec.get("notes"))


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
        out.append("  Price ................ %s at %s"
                   % (odds.fmt_american(p.price), p.book or "unspecified book"))
        out.append("  Jordan's probability .. %.1f%%" % (100 * p.prob))
        mk = p.market_prob
        if mk is not None:
            out.append("  Market's probability .. %.1f%%  (de-vigged)" % (100 * mk))
            out.append("  Disagreement .......... %+.1f points -- this is the "
                       "entire claim" % (100 * p.disagreement()))
        out.append("  Break-even at price ... %.1f%%"
                   % (100 * odds.breakeven_prob(p.price)))
        out.append("  Edge .................. %+.1f points   EV %+.2f%%"
                   % (100 * p.edge, p.ev_pct))
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
            out.append("ALSO CONSIDERED")
            out.append(thin)
            for cand in self.candidates[1:6]:
                out.append("  %-46s %7s  EV %+6.2f%%"
                           % (cand.description[:46], odds.fmt_american(cand.price),
                              cand.ev_pct))
            out.append("")
        out.append(line)
        return "\n".join(out)


def build(candidates, date, sport=None, known=None, bankroll=1000.0):
    """Rank the board, apply the information gate, produce a card.

    The best candidate by EV becomes the forecast regardless of whether it is
    bettable. The stake is decided separately.
    """
    if not candidates:
        raise ValueError("no candidates -- give Jordan something to price")
    ranked = sorted(candidates, key=lambda c: -c.ev_pct)
    pick = ranked[0]
    sport = sport or pick.sport
    conf = research.confidence(sport, known)
    floor = required_edge(conf["completeness"])

    reasons = []
    stake = 0.0
    if pick.ev_pct <= 0:
        verdict = "NO BET"
        reasons.append("Best thing on the board is %+.2f%%. Nothing here is a bet, "
                       "which is the normal answer." % pick.ev_pct)
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
        full = odds.kelly_stake(pick.prob, pick.price, bankroll,
                                multiplier=BANKROLL["kelly_multiplier"],
                                cap=BANKROLL["single_bet_cap"])
        stake = full * conf["stake_multiplier"]
        verdict = "BET"
        reasons.append("Edge of %.1f points clears the %.1f-point floor at %.0f%% "
                       "research completeness."
                       % (100 * pick.edge, 100 * floor, 100 * conf["completeness"]))
        reasons.append("Quarter Kelly, capped at 2%% of bankroll, then scaled to "
                       "%.0f%% for the information gaps."
                       % (100 * conf["stake_multiplier"]))

    if pick.disagreement() is not None and abs(pick.disagreement()) > 0.08:
        reasons.append("Jordan disagrees with the market by %.1f points. That is a "
                       "large claim -- it is usually the model that is wrong, so "
                       "check the inputs before the stake."
                       % (100 * abs(pick.disagreement())))

    reasons.append("The forecast is logged either way. Betting and forecasting are "
                   "separate skills and only one of them is free.")
    return Card(date, pick, ranked, conf, stake, verdict, reasons, bankroll)
