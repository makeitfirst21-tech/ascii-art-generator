"""Jordan -- a betting analyst you can actually audit.

    from jordan import analyse_parlay, Leg, NormalStat, MarketTracker

Four pillars, four modules:

    jordan.market       real-time tracking and market signals
    jordan.simulate     projection distributions and Monte Carlo
    jordan.correlation  correlation priors and SGP construction
    jordan.odds         de-vigging, EV, Kelly, arbitrage

`jordan.persona` holds who Jordan is and the house rules he will not break.
Read jordan/KNOWLEDGE.md before trusting any number this package prints.
"""

from .odds import (american_to_decimal, american_to_prob, decimal_to_american,
                   devig, fair_price, expected_value, ev_percent, edge_in_cents,
                   kelly_fraction, kelly_stake, parlay_american, parlay_hold,
                   parlay_ev, fmt_american, hold, prob_to_american,
                   recommended_devig, conservative_probs,
                   survives_every_devig)
from .simulate import (Leg, Simulation, NormalStat, LognormalStat, CountStat,
                       BernoulliStat, leg_from_spec, spread_to_win_prob,
                       win_prob_to_spread)
from .correlation import prior, build_matrix, describe_matrix
from .market import MarketTracker, Snapshot, arbitrage, middle, book_weight
from .parlay import analyse_parlay, grade_leg, best_subset, record_grade
from .persona import brief, DOCTRINES, HOUSE_RULES, DISCLAIMER

__version__ = "1.0.0"

__all__ = [
    "american_to_decimal", "american_to_prob", "decimal_to_american", "devig",
    "fair_price", "expected_value", "ev_percent", "edge_in_cents",
    "kelly_fraction", "kelly_stake", "parlay_american", "parlay_hold",
    "parlay_ev", "fmt_american", "hold", "prob_to_american", "recommended_devig",
    "conservative_probs", "survives_every_devig",
    "Leg", "Simulation", "NormalStat", "LognormalStat", "CountStat",
    "BernoulliStat", "leg_from_spec", "spread_to_win_prob", "win_prob_to_spread",
    "prior", "build_matrix", "describe_matrix",
    "MarketTracker", "Snapshot", "arbitrage", "middle", "book_weight",
    "analyse_parlay", "grade_leg", "best_subset", "record_grade",
    "brief", "DOCTRINES", "HOUSE_RULES", "DISCLAIMER",
]
