"""What you must know before you are allowed to have an opinion.

You cannot make a game a sure thing. Even with perfect information the outcome
stays random -- that is what a game is. What information buys you is a *better
probability*, and the honest way to run a daily card is to be explicit about
how much of the picture you actually have.

So every pick carries a completeness score. Miss the injury report and Jordan
does not quietly guess: the confidence cap drops, the stake shrinks, and if
enough is missing the card passes regardless of how good the number looks.

"Barring injuries" is not a disclaimer you attach after the fact. It is an
input, and if you do not have it you do not have the bet.
"""


class Item:
    def __init__(self, key, label, weight, why):
        self.key = key
        self.label = label
        self.weight = weight
        self.why = why


# Weights are relative within a sport and reflect how much the item moves a
# number, not how hard it is to look up.
CHECKLISTS = {
    "nfl": [
        Item("qb_status", "Starting QB confirmed active", 10,
             "The single largest price mover in the sport. A backup QB is worth "
             "six to nine points of spread."),
        Item("injury_report", "Final injury report / actives (90 min pre-kick)", 9,
             "Wednesday practice reports are noise. The Friday designation and "
             "the inactives list are the signal."),
        Item("ol_dl_availability", "Offensive and defensive line availability", 6,
             "Two starting linemen out reshapes the whole run/pass distribution "
             "and nobody prices it until late."),
        Item("weather", "Wind, precipitation, temperature", 6,
             "Wind above 15mph is the one weather variable that reliably moves "
             "totals and kills passing props. Cold alone mostly does not."),
        Item("snap_share", "Recent snap counts and target share", 7,
             "The driver behind every player prop. Project usage before you "
             "project production."),
        Item("line_movement", "Open-to-current line movement and where", 8,
             "Who moved it and at what limit. Pillar I."),
        Item("rest_travel", "Rest days, travel, time zone, short week", 4,
             "Thursday games and west-to-east body clock spots are real but "
             "small, and already partly priced."),
        Item("pace_tendency", "Pace and pass-rate tendencies of both coaches", 5,
             "Sets the plausible range of the total and every counting stat."),
        Item("key_numbers", "Where the line sits relative to 3 and 7", 6,
             "Decides whether a half point is worth 26 cents or 6."),
        Item("ref_crew", "Referee crew penalty and pace tendencies", 2,
             "Small and often overstated, but free to look up."),
    ],
    "nba": [
        Item("injury_report", "Injury report and load-management status", 10,
             "The dominant variable. A star ruled out an hour before tip moves "
             "a total four points and every prop on the board."),
        Item("minutes_trend", "Recent minutes and rotation pattern", 9,
             "Minutes drive every counting stat. Voulgaris built a career on "
             "knowing them before the market did."),
        Item("back_to_back", "Back-to-back / third-in-four scheduling", 7,
             "Predicts rest, reduced minutes and lower effort in ways the "
             "market underprices early in the season."),
        Item("pace", "Both teams' pace and expected possessions", 7,
             "Shared input across every player in the building."),
        Item("lineup_news", "Confirmed starting five", 6,
             "Late scratches cascade through the whole rotation."),
        Item("line_movement", "Open-to-current line movement and where", 8,
             "Pillar I."),
        Item("matchup_splits", "On/off and matchup splits for the key players", 5,
             "Where a genuine model edge lives, if you have the data."),
        Item("travel", "Travel and time zone", 3,
             "Real but small and largely priced."),
    ],
    "mlb": [
        Item("starting_pitchers", "Both starters confirmed", 10,
             "A scratched starter can be worth a run and a half of total. "
             "Never bet a game with an unconfirmed arm."),
        Item("bullpen_usage", "Bullpen usage over the last three days", 8,
             "A gassed pen turns a good starter's game into a coin flip after "
             "the sixth, and totals rarely price it."),
        Item("lineup_card", "Posted lineups", 7,
             "A regular resting changes team totals and every player prop."),
        Item("weather_park", "Wind direction and speed, temperature, park factors", 8,
             "Wind blowing out at the right park is the biggest single input "
             "into a baseball total."),
        Item("umpire", "Home plate umpire strike-zone tendencies", 5,
             "Measurable and persistent; moves strikeout props and totals."),
        Item("platoon_splits", "Handedness and platoon splits", 6,
             "Decides who actually plays and how they hit."),
        Item("line_movement", "Open-to-current line movement and where", 8,
             "Pillar I."),
        Item("travel_rest", "Travel, day-after-night, series position", 3,
             "Small."),
    ],
    "generic": [
        Item("availability", "Confirmed availability of key participants", 10,
             "If you do not know who is playing, you do not have a bet."),
        Item("line_movement", "Open-to-current line movement and where", 8,
             "Pillar I applies to every sport."),
        Item("form_usage", "Recent form and usage of the relevant participants", 7,
             "The driver behind whatever you are projecting."),
        Item("conditions", "Conditions -- weather, surface, venue", 5,
             "Sport-specific but usually cheap to check."),
        Item("rest_schedule", "Rest, travel and schedule spot", 4,
             "Real but small."),
        Item("motivation", "Stakes and motivation for both sides", 4,
             "Matters most at the end of a season and in dead rubbers."),
    ],
}


def checklist(sport):
    return CHECKLISTS.get(sport.lower(), CHECKLISTS["generic"])


def completeness(sport, known):
    """Weighted share of the checklist you actually have.

    `known` is an iterable of item keys you have checked, or a dict of
    {key: bool}.
    """
    items = checklist(sport)
    if isinstance(known, dict):
        have = {k for k, v in known.items() if v}
    else:
        have = set(known or ())
    total = sum(i.weight for i in items)
    got = sum(i.weight for i in items if i.key in have)
    return got / total if total else 0.0


def missing(sport, known):
    """The items you have not checked, heaviest first."""
    items = checklist(sport)
    if isinstance(known, dict):
        have = {k for k, v in known.items() if v}
    else:
        have = set(known or ())
    out = [i for i in items if i.key not in have]
    out.sort(key=lambda i: -i.weight)
    return out


# Completeness -> what you are allowed to do about it.
CONFIDENCE_BANDS = [
    (0.90, 1.00, "Full", "Everything that matters is known. Bet the number."),
    (0.75, 0.60, "Good", "Minor gaps. Size down to 60% of the Kelly stake."),
    (0.60, 0.35, "Partial", "Real gaps. Quarter stake at most, and only on a "
                            "large edge."),
    (0.00, 0.00, "Insufficient", "You do not know enough to have a number. "
                                 "Forecast it if you like, but do not bet it."),
]


def confidence(sport, known):
    """Completeness turned into a hard cap on stake."""
    score = completeness(sport, known)
    for threshold, multiplier, label, note in CONFIDENCE_BANDS:
        if score >= threshold:
            return {
                "completeness": score,
                "stake_multiplier": multiplier,
                "label": label,
                "note": note,
                "missing": [i.label for i in missing(sport, known)[:4]],
            }
    return {"completeness": score, "stake_multiplier": 0.0,
            "label": "Insufficient", "note": CONFIDENCE_BANDS[-1][3],
            "missing": [i.label for i in missing(sport, known)[:4]]}


def render_checklist(sport, known=None, width=78):
    items = checklist(sport)
    if isinstance(known, dict):
        have = {k for k, v in known.items() if v}
    else:
        have = set(known or ())
    out = ["=" * width, ("RESEARCH CHECKLIST -- %s" % sport.upper()).center(width),
           "=" * width]
    conf = confidence(sport, have)
    out.append("Completeness: %.0f%%   Confidence: %s   Stake cap: %.0f%% of Kelly"
               % (100 * conf["completeness"], conf["label"],
                  100 * conf["stake_multiplier"]))
    out.append(conf["note"])
    out.append("-" * width)
    for i in items:
        mark = "[x]" if i.key in have else "[ ]"
        out.append("  %s %-46s weight %2d" % (mark, i.label, i.weight))
        out.append("        %s" % i.why)
    out.append("=" * width)
    return "\n".join(out)
