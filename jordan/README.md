# Jordan

A betting analyst you can audit. Pure Python 3, standard library only, no
network calls, no data feeds, no picks.

Jordan's default answer is **pass**. That is not modesty — it is the correct
answer most of the time, and every bettor his methods are drawn from says so in
their own words.

Read **[KNOWLEDGE.md](KNOWLEDGE.md)** before trusting a number this package
prints. It documents where every prior, weight and threshold comes from.

## Quick start

```bash
python3 -m jordan brief                      # who Jordan is and how he thinks
python3 -m jordan devig -110 -110            # strip the vig off a market
python3 -m jordan devig 450 -700             # watch the methods disagree
python3 -m jordan ev --prob 0.55 --price -110 --bankroll 5000
python3 -m jordan parlay -110 -110 -110      # what a parlay really costs
python3 -m jordan stacks nfl                 # correlation priors and stacks
python3 -m jordan record 7 3                 # what your record actually proves
python3 -m jordan arb 115 -105
python3 -m jordan keys                       # NFL key numbers, half-point values
python3 -m jordan keys --buy -3              # is buying that half point worth it?
python3 -m jordan middle -3.5 -110 -2.5 -110 --sport nfl

# the daily card
python3 -m jordan checklist nfl              # what you need to know first
python3 -m jordan card slate.json --log      # Jordan forecasts one game, logged
python3 -m jordan card slate.json --log-all  # every candidate logged and graded
python3 -m jordan pick --author you --sport nfl \
    --desc "SEA -3.5" --price -110 --prob 0.58 --market -110 -110
python3 -m jordan grade 7 --result win --closing -118
python3 -m jordan scoreboard                 # Brier, log loss, skill vs market
python3 -m jordan calibration                # when you say 60%, is it 60%?

python3 -m jordan sgp examples/ticket_nfl_stack.json --search
python3 -m jordan market examples/market_nfl_side.json
```

### Slate candidates

```json
{"description": "Swift anytime TD", "price": 130, "prob": 0.49,
 "market": [120, -150], "known": ["qb_status", "weather"],
 "price_verified": false}
```

`market` is the two-way market from a sharp book, if you have it. `known`
overrides the card's research list for this candidate alone. `price_verified`
is false for an estimated price: it can be forecast, never bet.

The card bets on a **blended** probability: Jordan's number pulled toward the
market's, with Jordan getting at most half the say and less as research gaps
grow. Without `market`, the offered price stands in for it (one-sided props are
de-vigged against an assumed 7% overround). An edge that exists only because
Jordan disagrees with the market is reported, forecast, and not bet.

## The four pillars

| Pillar | Module | What it does |
|---|---|---|
| Real-Time Tracking & Market Signals | `jordan.market` | line history, limit-weighted sharp consensus, steam, reverse line movement, handle/ticket divergence, CLV |
| Advanced Simulation & Projection Models | `jordan.simulate` | normal / lognormal / negative-binomial / Bernoulli marginals through a Monte Carlo engine, blended against the de-vigged market |
| Correlation Data (the SGP weapon) | `jordan.correlation` | empirical priors by sport and relationship, sign-flipped by side, repaired to a legal matrix, sampled through a Gaussian copula |
| Market Inefficiencies & +EV | `jordan.odds` | four de-vig methods plus a conservative stress test, EV in percent and cents, fractional Kelly, arbitrage and properly priced middles |
| Key numbers | `jordan.keynumbers` | the NFL margin distribution, what a half point is worth at each number, and whether buying it is worth the ask |
| The daily card | `jordan.card`, `jordan.ledger`, `jordan.research` | one forecast a day whether or not it is bettable, a research checklist that gates the stake, and proper scoring of both forecasters (Brier, log loss, calibration, skill vs the market) |

## As a library

```python
from jordan import Leg, NormalStat, LognormalStat, analyse_parlay

qb = Leg("QB pass yards", NormalStat(268, 61), 249.5, "over", -114,
         market_prices=[-114, -106])
qb.stat = "pass_yards"

wr = Leg("WR1 rec yards", LognormalStat(72, 29), 64.5, "over", -110,
         market_prices=[-110, -110])
wr.stat = "rec_yards"

report = analyse_parlay([qb, wr], offered_price=260, sport="nfl",
                        relationships={(0, 1): "same_team"}, bankroll=5000)
print(report.render())
```

## Ticket JSON

```json
{
  "sport": "nfl",
  "offered_price": 425,
  "bankroll": 5000,
  "legs": [
    {"label": "QB1 pass yards", "stat": "pass_yards", "dist": "normal",
     "mean": 268, "sd": 61, "line": 249.5, "side": "over", "price": -114,
     "market": [-114, -106], "stability": 0.92, "signal": 0.45}
  ],
  "relationships": {"0-1": "same_team"},
  "overrides": {"0-1": 0.42}
}
```

- `dist` — `normal`, `lognormal`, `count` (give `variance`), or `bernoulli` (give `prob`)
- `market` — the full two-way market, so the leg can be de-vigged rather than guessed at
- `stability` — 0–1, how reliable the leg's *driver* is (snaps, minutes, targets)
- `signal` — 0–1, market agreement, from `jordan.market`
- `relationships` — `same_player`, `same_team` or `opponent`, keyed `"i-j"`
- `overrides` — your own correlation, replacing the prior. **On the stat scale**,
  not the bet scale: give the correlation between the statistics, and let the
  simulation work out what your chosen sides do to the sign.

Two things the engine does that most parlay tools do not: every leg is evaluated
at its blended model/market probability (so the leg grades and the ticket price
are the same number), and a leg that lands exactly on a whole-number line pushes
and drops out of the ticket rather than killing it.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## What this is not

Not a tipster, not a data feed, not a guarantee. Every number is an estimate
from a model that can be wrong, fed by inputs you supply.

Sports betting is -EV for almost everyone who does it. Bet only what you can
lose without consequence, only where it is legal, and never with borrowed money.
If it has stopped being optional, stop: **1-800-522-4700** (US National Problem
Gambling Helpline, 24/7, confidential).
