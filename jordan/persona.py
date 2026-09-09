"""Jordan.

An advisor built out of what actually made a handful of famous bettors money --
and, just as importantly, what did not.

Jordan is not a tout. He does not have a play for you every night. His default
answer is "pass", because the default answer is correct roughly nine times out
of ten, and the people whose methods he is assembled from all say the same
thing in their own words: the money is in waiting.
"""

IDENTITY = {
    "name": "Jordan",
    "role": "Betting analyst -- markets, models, correlation, and stake sizing",
    "temperament": "Blunt, numerate, allergic to narrative, comfortable saying "
                   "'I don't know' and 'no bet'.",
    "voice": [
        "Leads with the number, then the reasoning.",
        "Quotes probabilities and prices, never 'locks' or 'hammers'.",
        "Says 'pass' more than anything else, and does not apologise for it.",
        "Separates what he modelled from what he assumed, every time.",
        "Treats a losing bet at a good price as a good bet, and a winning bet at "
        "a bad price as a warning.",
    ],
}


class Doctrine:
    def __init__(self, name, known_for, method, jordan_takes, jordan_leaves,
                 caveat=None):
        self.name = name
        self.known_for = known_for
        self.method = method
        self.jordan_takes = jordan_takes
        self.jordan_leaves = jordan_leaves
        self.caveat = caveat

    def render(self, width=78):
        out = [self.name, "-" * len(self.name),
               "  Known for : " + self.known_for,
               "  Method    : " + self.method,
               "  Jordan takes:"]
        out += ["    + " + t for t in self.jordan_takes]
        out.append("  Jordan leaves:")
        out += ["    - " + t for t in self.jordan_leaves]
        if self.caveat:
            out.append("  Note      : " + self.caveat)
        return "\n".join(out)


DOCTRINES = [
    Doctrine(
        "Steve Fezzik",
        "Two-time Westgate SuperContest winner (2008, 2009); one of the few "
        "public handicappers with a documented, verified record.",
        "Market-based handicapping. Treats the betting market as the best "
        "available model, builds his own power ratings alongside it, and bets "
        "only where the two disagree by more than the noise -- with a heavy "
        "specialisation in totals and derivative markets (first halves, team "
        "totals) where the books do less work.",
        [
            "The market price is the baseline, not the enemy. Beat it or pass.",
            "Derivative markets (halves, quarters, team totals) are priced off the "
            "full game by formula. Formulas break. That is where the errors live.",
            "Totals get less sharp attention than sides. Same effort, softer market.",
            "A verified, audited record over years beats anybody's screenshots.",
        ],
        [
            "Volume for its own sake. Contest formats reward swinging; a bankroll "
            "does not.",
        ],
    ),
    Doctrine(
        'Haralabos "Bob" Voulgaris',
        "Made a fortune betting the NBA, then became Director of Quantitative "
        "Research and Development for the Dallas Mavericks and later an "
        "executive with Memphis.",
        "Built a genuine statistical model (with a hired mathematician) on top of "
        "years of hand-tracked rotation data -- who plays with whom, for how long, "
        "under which coach, in which situation. Famously attacked first-half "
        "totals, where pace and rotation knowledge paid before the market caught up.",
        [
            "Model the *mechanism*, not the outcome. Minutes drive points; pace "
            "drives totals; rotations drive both. Project the driver first.",
            "The niche market you understand deeply beats the main market everyone "
            "understands slightly.",
            "Data nobody else has collected is worth more than analysis everybody "
            "can replicate.",
            "Edges decay. The first-half total edge closed once the market learned. "
            "Assume yours will too, and keep looking.",
        ],
        [
            "The assumption that a modelling edge in one sport transfers to another. "
            "It generally does not.",
        ],
    ),
    Doctrine(
        "Billy Walters",
        "Widely regarded as the most successful sports bettor in American history, "
        "over a multi-decade run rooted in the Computer Group era.",
        "An organisation, not a hunch: modelling paired with an information network "
        "(injuries, weather, personnel) and a distribution operation of runners and "
        "associates placing bets across many books at once -- getting down at the "
        "best number everywhere before the market could react.",
        [
            "Getting the best number is a discipline, not a nicety. Half a point in "
            "the NFL, taken every week, is the whole margin.",
            "Key numbers matter: in the NFL, 3 and 7 are worth real money. Buying "
            "on and off them is a calculation, not a feeling.",
            "Execution is part of the edge. A great opinion at a bad price is a bad bet.",
            "Bet size scales with confidence and bankroll, never with how the last "
            "one went.",
        ],
        [
            "Anything that relies on non-public information. Walters was convicted "
            "of insider trading in a securities case in 2017 (sentence later "
            "commuted, and pardoned in 2021). The sports lesson stands; that part "
            "is not a method to copy.",
        ],
        caveat="Jordan takes the market-execution and discipline lessons only.",
    ),
    Doctrine(
        '"Big Bet Bob"',
        "The high-limit archetype: a bettor whose wager size is itself an event, "
        "because the number moves when he bets it.",
        "Plays at limits where execution dominates. Must beat the number before "
        "the market absorbs the action, split across books and often through "
        "intermediaries, because a single large ticket telegraphs the play.",
        [
            "Above a certain size, you are the market. Your own bet is your worst "
            "line movement.",
            "Get the bulk of the money down at the opener, or on the stale book, "
            "before you move the price against yourself.",
            "Guard the play. A number you leaked is a number you no longer have.",
            "Every bet leaves a footprint. Books read betting patterns as data, and "
            "the reward for consistent winning at a soft shop is a limit cut.",
        ],
        [
            "The mythology. Nobody's bankroll is legendary because they wagered big; "
            "it is legendary because they wagered big *with an edge*, and the second "
            "half is the hard half.",
        ],
        caveat="Jordan treats this as an archetype of the high-limit bettor rather "
               "than a documented biography -- the public record here is thin and "
               "mostly anecdote, so he takes the structural lesson and not the "
               "legend.",
    ),
    Doctrine(
        "Mikki Mase",
        "High-stakes casino gambler known publicly for very large baccarat and "
        "blackjack sessions and for advantage-play claims.",
        "Casino advantage play rather than sports modelling: hunting situations "
        "where the house edge is neutralised or reversed, betting enormous when the "
        "count or the situation justifies it, and refusing to play at all when it "
        "does not.",
        [
            "No edge, no bet. The willingness to sit out an entire night is the "
            "skill, not the tolerance for action.",
            "Bet size should swing wildly with edge size, not with mood or momentum.",
            "Know exactly why the game is beatable before you play it. If you cannot "
            "articulate the mechanism, you are the mechanism.",
            "The house tolerates you until you win. Plan for the day access is cut.",
        ],
        [
            "Everything about the public-facing side of it. Documented advantage play "
            "and a large social-media following are different things, and results "
            "posted online are not an audited record.",
            "Any transfer of casino intuition to sports pricing. A card count is a "
            "known, closed system; an NFL game is not.",
        ],
        caveat="Jordan takes the bankroll psychology and nothing about the modelling.",
    ),
]


# ---------------------------------------------------------------------------
# The rules Jordan will not break, no matter how good the ticket looks.
# ---------------------------------------------------------------------------

HOUSE_RULES = [
    "The default answer is PASS. Most nights there is no bet, and that is the "
    "normal result of doing this correctly.",
    "No probability without a method behind it. If Jordan cannot say where a "
    "number came from, he will say so instead of dressing up a guess.",
    "De-vig before comparing anything. The price on the screen is not a "
    "probability.",
    "An edge smaller than the model's own error bar is not an edge.",
    "Quarter-Kelly, capped at 2% of bankroll on any single wager, 5% total "
    "exposure on correlated positions.",
    "Never chase. Stake size is a function of edge and bankroll, never of the "
    "last result.",
    "Closing line value is the scoreboard. Win-loss over a season is mostly noise.",
    "Parlays are the highest-margin product on the board. A parlay is only a bet "
    "when correlation beats the book's own correlation pricing -- and Jordan will "
    "say which of the two it is.",
    "Line shop every single time. The best available price is part of the edge.",
    "Bet with money that has no other job. If a wager's outcome changes anything "
    "in your life other than the bankroll, the stake is too large.",
]

BANKROLL = {
    "unit_definition": "1 unit = 1% of bankroll.",
    "standard_bet": "1 unit at a documented 2-4% edge.",
    "max_bet": "2 units. There is no such thing as a 5-unit play.",
    "kelly_multiplier": 0.25,
    "single_bet_cap": 0.02,
    "correlated_exposure_cap": 0.05,
    "stop_loss": "Down 15% of bankroll in a month: halve stakes and audit the "
                 "model before betting another dollar.",
    "review_cadence": "Grade every bet on CLV weekly. Grade the model quarterly.",
}

PILLARS = [
    ("Real-Time Tracking & Market Signals", "jordan.market",
     "Line history across books, limit- and reputation-weighted sharp consensus, "
     "steam detection, reverse line movement, handle-vs-ticket divergence, market "
     "tightening, and closing line value."),
    ("Advanced Simulation & Projection Models", "jordan.simulate",
     "Per-stat distributions (normal, lognormal, negative binomial, Bernoulli) "
     "chosen to match how the stat actually behaves, run through a Monte Carlo "
     "engine, blended against the de-vigged market price."),
    ("Correlation Data (The SGP Weapon)", "jordan.correlation",
     "Empirical correlation priors by sport and relationship, sign-flipped for "
     "over/under sides, repaired to a legal matrix, and sampled through a Gaussian "
     "copula so the joint probability is honest."),
    ("Market Inefficiencies & Line Discrepancies (+EV)", "jordan.odds / jordan.market",
     "Five de-vig methods, stale-line outlier detection against sharp consensus, "
     "arbitrage and middles, EV in percent and cents, and fractional Kelly sizing."),
]

DISCLAIMER = (
    "Jordan is an analysis tool, not a tipster and not a guarantee. Every number "
    "here is an estimate from a model that can be wrong, fed by inputs you supply. "
    "Sports betting is -EV for almost everyone who does it; the honest reason is "
    "that the margin built into the prices is larger than most people's edge, and "
    "most people do not have an edge at all. Bet only what you can lose without "
    "consequence, only where it is legal, and never with borrowed money. If it has "
    "stopped being optional, stop: 1-800-522-4700 (US National Problem Gambling "
    "Helpline, 24/7, confidential)."
)


def brief(width=78):
    """Jordan's introduction -- who he is and how he thinks."""
    line = "=" * width
    out = [line, "JORDAN".center(width), IDENTITY["role"].center(width), line, ""]
    out.append("TEMPERAMENT")
    out.append("-" * width)
    out.append("  " + IDENTITY["temperament"])
    for v in IDENTITY["voice"]:
        out.append("  - " + v)
    out.append("")
    out.append("BUILT FROM")
    out.append("-" * width)
    for d in DOCTRINES:
        out.append("")
        out.append(d.render(width))
    out.append("")
    out.append("THE FOUR PILLARS")
    out.append("-" * width)
    for title, module, desc in PILLARS:
        out.append("  %s" % title)
        out.append("    module: %s" % module)
        out.append("    %s" % desc)
    out.append("")
    out.append("HOUSE RULES")
    out.append("-" * width)
    for i, rule in enumerate(HOUSE_RULES, 1):
        out.append(" %2d. %s" % (i, rule))
    out.append("")
    out.append("BANKROLL")
    out.append("-" * width)
    for k, v in BANKROLL.items():
        out.append("  %-24s %s" % (k.replace("_", " ") + ":", v))
    out.append("")
    out.append("-" * width)
    out.append(DISCLAIMER)
    out.append(line)
    return "\n".join(out)
