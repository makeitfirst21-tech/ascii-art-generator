"""Jordan -- a betting analyst you can actually audit.

    from jordan import analyse_parlay, Leg, NormalStat, MarketTracker

Four pillars, four modules:

    jordan.market       real-time tracking and market signals
    jordan.simulate     projection distributions and Monte Carlo
    jordan.correlation  correlation priors and SGP construction
    jordan.odds         de-vigging, EV, Kelly, arbitrage
    jordan.keynumbers   NFL key numbers and the price of a half point
    jordan.research     what you must know before you may have an opinion
    jordan.card         the daily card: one forecast a day, bet or not
    jordan.ledger       pick history and proper scoring (Brier, calibration)

`jordan.persona` holds who Jordan is and the house rules he will not break.
Read jordan/KNOWLEDGE.md before trusting any number this package prints.
"""

from .odds import (american_to_decimal, american_to_prob, decimal_to_american,
                   devig, fair_price, expected_value, ev_percent, edge_in_cents,
                   kelly_fraction, kelly_stake, parlay_american, parlay_hold,
                   parlay_ev, fmt_american, hold, prob_to_american,
                   recommended_devig, conservative_probs,
                   survives_every_devig, cents_scale, cents_between)
from .simulate import (Leg, Simulation, NormalStat, LognormalStat, CountStat,
                       BernoulliStat, leg_from_spec, spread_to_win_prob,
                       win_prob_to_spread)
from .correlation import (prior, build_matrix, describe_matrix,
                          flip_for_sides, context_scale)
from .market import MarketTracker, Snapshot, arbitrage, middle, book_weight
from .keynumbers import (margin_mass, is_key_number, half_point_value,
                         buy_points, key_number_report)
from .parlay import analyse_parlay, grade_leg, best_subset, record_grade
from .research import checklist, completeness, confidence, missing
from .card import Candidate, build as build_card, required_edge
from .ledger import (Ledger, Pick, brier, log_loss, skill_score,
                     calibration, record as ledger_record,
                     bootstrap_brier_gap)
from .persona import brief, DOCTRINES, HOUSE_RULES, DISCLAIMER

__version__ = "1.2.0"

__all__ = [
    "american_to_decimal", "american_to_prob", "decimal_to_american", "devig",
    "fair_price", "expected_value", "ev_percent", "edge_in_cents",
    "kelly_fraction", "kelly_stake", "parlay_american", "parlay_hold",
    "parlay_ev", "fmt_american", "hold", "prob_to_american", "recommended_devig",
    "conservative_probs", "survives_every_devig", "cents_scale", "cents_between",
    "Leg", "Simulation", "NormalStat", "LognormalStat", "CountStat",
    "BernoulliStat", "leg_from_spec", "spread_to_win_prob", "win_prob_to_spread",
    "prior", "build_matrix", "describe_matrix", "flip_for_sides",
    "context_scale",
    "MarketTracker", "Snapshot", "arbitrage", "middle", "book_weight",
    "margin_mass", "is_key_number", "half_point_value", "buy_points",
    "key_number_report",
    "analyse_parlay", "grade_leg", "best_subset", "record_grade",
    "checklist", "completeness", "confidence", "missing",
    "Candidate", "build_card", "required_edge",
    "Ledger", "Pick", "brier", "log_loss", "skill_score", "calibration",
    "ledger_record", "bootstrap_brier_gap",
    "brief", "DOCTRINES", "HOUSE_RULES", "DISCLAIMER",
]
