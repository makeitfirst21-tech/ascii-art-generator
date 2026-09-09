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

python3 -m jordan sgp examples/ticket_nfl_stack.json --search
python3 -m jordan market examples/market_nfl_side.json
```

## The four pillars

| Pillar | Module | What it does |
|---|---|---|
| Real-Time Tracking & Market Signals | `jordan.market` | line history, limit-weighted sharp consensus, steam, reverse line movement, handle/ticket divergence, CLV |
| Advanced Simulation & Projection Models | `jordan.simulate` | normal / lognormal / negative-binomial / Bernoulli marginals through a Monte Carlo engine, blended against the de-vigged market |
| Correlation Data (the SGP weapon) | `jordan.correlation` | empirical priors by sport and relationship, sign-flipped by side, repaired to a legal matrix, sampled through a Gaussian copula |
| Market Inefficiencies & +EV | `jordan.odds` | four de-vig methods plus a conservative stress test, EV in percent and cents, fractional Kelly, arbitrage and middles |

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
- `overrides` — your own correlation, replacing the prior

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
