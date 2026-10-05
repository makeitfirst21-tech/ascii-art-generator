"""Correlation priors and same-game-parlay construction.

The single most valuable thing in this package.

A book prices a same-game parlay by taking its own correlation model and adding
margin. Where their model is crude -- and on secondary props it usually is --
the true joint probability and the offered price come apart. That gap is the
only reason a parlay is ever a bet instead of a donation.

The priors below are round-number, publicly-known relationships from box-score
data. They are starting points to be overridden by your own numbers, not
gospel, and every one of them moves with pace, game total and spread.
"""

from . import stats

# ---------------------------------------------------------------------------
# Correlation priors, keyed by (stat_a, stat_b, relationship).
#
# relationship:
#   "same_player"  both legs are the same player
#   "same_team"    teammates
#   "opponent"     players on opposite teams in the same game
#
# Values are Pearson correlations on the underlying continuous stat.
# ---------------------------------------------------------------------------

NFL_PRIORS = {
    ("pass_yards", "rec_yards", "same_team"): 0.55,       # QB -> his WR1
    ("pass_yards", "rec_yards", "opponent"): 0.14,        # shootout effect
    ("pass_yards", "receptions", "same_team"): 0.46,
    ("pass_yards", "pass_tds", "same_player"): 0.52,
    ("pass_tds", "anytime_td", "same_team"): 0.38,
    ("pass_yards", "anytime_td", "same_team"): 0.31,   # volume feeds the end zone
    ("pass_yards", "team_total", "same_team"): 0.43,
    ("receptions", "anytime_td", "same_player"): 0.33,
    ("rush_attempts", "anytime_td", "same_player"): 0.36,
    ("rec_yards", "anytime_td", "same_player"): 0.44,
    ("rush_yards", "anytime_td", "same_player"): 0.41,
    ("rush_yards", "pass_yards", "same_team"): -0.18,     # they share one ball
    ("rush_yards", "team_total", "same_team"): 0.30,
    ("rush_attempts", "team_win", "same_team"): 0.35,     # leading = running
    ("pass_attempts", "team_win", "same_team"): -0.28,    # trailing = throwing
    ("rec_yards", "rec_yards", "same_team"): -0.12,       # WR1 vs WR2, same targets
    ("rec_yards", "rec_yards", "opponent"): 0.11,
    ("pass_yards", "game_total", "same_team"): 0.48,
    ("anytime_td", "game_total", "same_team"): 0.30,
    ("team_total", "game_total", "same_team"): 0.71,
    ("sacks", "pass_attempts", "opponent"): 0.24,
    ("kicker_points", "team_total", "same_team"): 0.42,
    ("kicker_points", "anytime_td", "same_team"): -0.15,  # TDs eat field goals
}

NBA_PRIORS = {
    ("points", "minutes", "same_player"): 0.58,
    ("points", "assists", "same_player"): 0.21,
    ("points", "rebounds", "same_player"): 0.18,
    ("assists", "points", "same_team"): 0.34,             # passer -> scorer
    ("points", "points", "same_team"): 0.08,
    ("points", "points", "opponent"): 0.16,               # pace is shared
    ("points", "team_total", "same_team"): 0.44,
    ("threes", "points", "same_player"): 0.62,
    ("threes", "team_total", "same_team"): 0.31,
    ("rebounds", "opponent_misses", "same_team"): 0.40,
    ("minutes", "team_win", "same_team"): -0.22,          # blowouts empty benches
    ("points", "game_total", "same_team"): 0.40,
    ("pace", "game_total", "same_team"): 0.66,
}

MLB_PRIORS = {
    ("strikeouts", "opp_runs", "same_team"): -0.34,
    ("strikeouts", "innings", "same_player"): 0.47,
    ("hits", "runs", "same_player"): 0.51,
    ("total_bases", "runs", "same_player"): 0.58,
    ("total_bases", "team_total", "same_team"): 0.36,
    ("home_run", "total_bases", "same_player"): 0.66,
    ("team_total", "game_total", "same_team"): 0.68,
    ("total_bases", "total_bases", "same_team"): 0.19,    # lineup turns over together
    ("earned_runs", "team_win", "same_team"): -0.44,
}

PRIOR_BOOKS = {"nfl": NFL_PRIORS, "nba": NBA_PRIORS, "mlb": MLB_PRIORS}


def prior(sport, stat_a, stat_b, relationship):
    """Look up a correlation prior in either direction; 0.0 if unknown."""
    book = PRIOR_BOOKS.get(sport.lower(), {})
    for key in ((stat_a, stat_b, relationship), (stat_b, stat_a, relationship)):
        if key in book:
            return book[key]
    return 0.0


def flip_for_sides(rho, side_a, side_b):
    """Sign of the relationship between two *bets*, given the stat correlation.

    Over/over keeps the sign; over/under flips it. Use this to reason about a
    pair on paper -- "these two overs help each other, this over and that under
    fight" -- and to read a book's SGP price.

    Do NOT use it to build the matrix you hand to `Simulation`. That class
    samples the stats themselves and works out the bet relationship by checking
    them against the lines, so pre-flipping the sign applies it twice and
    inverts the answer. `build_matrix` deliberately does not call this.
    """
    a_up = side_a in ("over", "yes")
    b_up = side_b in ("over", "yes")
    return rho if a_up == b_up else -rho


def context_scale(context):
    """Scale the priors to the game environment.

    Correlations are not constants. A quarterback and his WR1 move together far
    more tightly in a projected shootout, where one team is throwing on every
    down, than in a 37-point rock fight where the ball is on the ground and the
    sample of pass attempts is small.

    `context` is a dict with any of:
        pace        1.0 = league average (NBA possessions, NFL plays)
        total       projected game total
        base_total  the league-average total for the sport
        spread      absolute projected margin -- blowouts decouple everything
                    once the starters sit

    Returns a multiplier, clamped to [0.6, 1.4]. This is a documented heuristic,
    not a fitted model: it moves the priors in the direction the game script
    argues for, and refuses to move them far.
    """
    if not context:
        return 1.0
    scale = 1.0
    total = context.get("total")
    base = context.get("base_total")
    if total and base:
        scale *= 1.0 + 0.35 * ((float(total) / float(base)) - 1.0)
    pace = context.get("pace")
    if pace:
        scale *= 1.0 + 0.25 * (float(pace) - 1.0)
    spread = context.get("spread")
    if spread is not None:
        # Beyond about two touchdowns, garbage time starts breaking the links
        # between starters' stat lines.
        scale *= 1.0 - min(max((abs(float(spread)) - 14.0) / 20.0, 0.0), 0.3)
    return max(0.6, min(1.4, scale))


def build_matrix(legs, sport="nfl", overrides=None, relationships=None,
                 context=None):
    """STAT-level correlation matrix for a list of legs.

    The returned matrix describes how the underlying statistics move together,
    independent of which side of each line you are betting. The simulation
    derives the bet-level relationship from it. Overrides are read on the same
    scale -- give the correlation between the stats, not between the bets.

    `legs` may carry `.stat` and `.entity` attributes; otherwise pass
    `relationships` as {(i, j): "same_team"} and `overrides` as {(i, j): rho}.

    `context` optionally scales the priors to the game environment -- see
    `context_scale`.
    """
    n = len(legs)
    overrides = overrides or {}
    relationships = relationships or {}
    m = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if (i, j) in overrides:
                rho = overrides[(i, j)]
            elif (j, i) in overrides:
                rho = overrides[(j, i)]
            else:
                rel = relationships.get((i, j)) or relationships.get((j, i)) or "same_team"
                stat_a = getattr(legs[i], "stat", None)
                stat_b = getattr(legs[j], "stat", None)
                if stat_a and stat_b:
                    # Stat scale, deliberately unflipped -- see flip_for_sides.
                    rho = prior(sport, stat_a, stat_b, rel)
                    rho *= context_scale(context)
                else:
                    rho = 0.0
            m[i][j] = m[j][i] = max(min(rho, 0.98), -0.98)
    return stats.nearest_correlation(m)


def describe_matrix(matrix, labels):
    """Human-readable pair list, strongest first."""
    pairs = []
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((abs(matrix[i][j]), matrix[i][j], labels[i], labels[j]))
    pairs.sort(reverse=True)
    return [(rho, a, b) for _, rho, a, b in pairs]


# ------------------------------------------------------- construction guidance

POSITIVE_STACKS = [
    ("nfl", "QB pass yards over + his WR1 receiving yards over",
     "The canonical stack. One long drive feeds both legs."),
    ("nfl", "QB pass TDs over + WR/TE anytime TD",
     "Correlated by construction; books price the second leg near-independently."),
    ("nfl", "Team total over + that team's RB rush attempts over",
     "Scoring teams lead, leading teams run out the clock."),
    ("nfl", "Underdog +points + game under",
     "Low-scoring games keep bad teams inside the number."),
    ("nba", "Player points over + his minutes over",
     "Minutes is the driver of every counting stat on the board."),
    ("nba", "Game total over + both teams' star points overs",
     "Pace is a shared input across every player in the building."),
    ("mlb", "Pitcher strikeouts over + his team's opponent total under",
     "Dominant starts suppress runs directly."),
    ("mlb", "Player home run + his total bases over",
     "A home run is four total bases; the legs overlap mechanically."),
]

NEGATIVE_STACKS = [
    ("nfl", "QB pass yards over + same team's RB rush yards over",
     "One offense, one football. The book is happy to sell you both."),
    ("nfl", "Team blowout win + star player's 4th-quarter production",
     "Benched in garbage time."),
    ("nfl", "Kicker points over + multiple teammate anytime TDs",
     "Touchdowns replace the field goals the kicker needs."),
    ("nba", "Team big win + star player minutes over",
     "The 22-point win is the reason he sat the fourth."),
    ("mlb", "Pitcher win + opposing offense overs",
     "Directly opposed outcomes dressed up as separate bets."),
]
