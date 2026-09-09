# Jordan — Knowledge Base

Everything Jordan reasons from, written down so you can argue with it.

The organising claim: **a bet is a disagreement with a price, sized by how
confident you are and how much you can afford to be wrong.** Everything below
serves that sentence.

---

## 0. The uncomfortable part, first

Parlays are the highest-margin product on the board. This is not opinion:

| Ticket | Legs at -110 | Expected loss per unit staked |
|---|---|---|
| Straight bet | 1 | 4.5% |
| Parlay | 2 | 8.9% |
| Parlay | 3 | 13.0% |
| Parlay | 4 | 17.0% |
| Parlay | 6 | 24.4% |
| Parlay | 8 | 31.1% |

(Reproduce with `python3 -m jordan parlay -110 -110 -110`.)

Two different numbers get called "hold" and it is worth keeping them apart. The
**overround** on a -110/-110 market is 4.76% — the implied probabilities sum to
104.76%. The **expected loss per unit staked** is 4.55%, because a fair coin at
1.909 decimal returns 0.9545 per unit. The table above uses the second, since
that is what actually comes out of your bankroll. `odds.hold()` gives the first,
`odds.parlay_hold()` the second.

Vig compounds. A six-leg parlay asks you to overcome a 24% house edge — no
handicapper alive beats that on picking ability. So Jordan takes exactly one
position on parlays:

> A parlay is only a bet when **correlation between the legs beats the book's
> own correlation pricing.** Otherwise it is a donation with a nice payout
> printed on it.

That is the whole thesis of the correlation pillar, and it is why the tool will
tell you to shorten your ticket more often than it tells you to bet it.

---

## 1. The bettors, and what actually transfers

### Steve Fezzik
Two-time Westgate SuperContest winner (2008, 2009) — one of very few public
handicappers with a verified, audited multi-year record.

**Method:** market-based handicapping. The market is treated as the best
available model; his own power ratings run alongside it; he bets only where the
two disagree by more than the noise. Heavy specialisation in **totals** and
**derivative markets** — first halves, team totals — where books do less work
than they do on primary sides.

**Transfers:**
- The market price is the baseline. Beat it or pass.
- Derivatives are priced off the full game *by formula*. Formulas break at the
  edges — a team whose scoring is back-loaded, a pitcher on a strict count.
- Totals absorb less sharp attention than sides. Same effort, softer market.
- A verified record beats anyone's screenshots.

**Doesn't transfer:** contest volume. Contests reward swinging at 50/50s
because you need variance to win a field of 3,000. A bankroll wants the
opposite.

### Haralabos "Bob" Voulgaris
Made a fortune on the NBA, then Director of Quantitative Research and
Development for the Dallas Mavericks, later an executive with Memphis.

**Method:** a real statistical model built on years of hand-tracked **rotation**
data — who plays with whom, for how long, under which coach, in which
situation — paired with a hired mathematician. Famously attacked **first-half
totals**, where pace and rotation knowledge paid before the market caught up.

**Transfers:**
- **Model the mechanism, not the outcome.** Minutes drive points. Pace drives
  totals. Rotations drive both. Project the driver, derive the stat.
- A niche you understand deeply beats a main market you understand slightly.
- Data nobody else collected outvalues analysis everybody can replicate.
- **Edges decay.** The first-half total edge closed once the market learned.
  Assume yours will too.

**Doesn't transfer:** the assumption that a modelling edge in one sport carries
to another. It generally does not.

### Billy Walters
Widely regarded as the most successful sports bettor in American history, over
a multi-decade run rooted in the Computer Group era.

**Method:** an organisation, not a hunch. Modelling plus an information network
(injuries, weather, personnel) plus a distribution operation of runners placing
bets across many books simultaneously — getting down at the best number
everywhere before the market could react.

**Transfers:**
- **Getting the best number is a discipline.** Half a point in the NFL, taken
  every week, is the entire margin.
- **Key numbers.** NFL margins cluster on 3 and 7. Moving from -3 to -2.5 is
  worth far more than moving -8 to -7.5. Buying points on and off key numbers is
  a calculation, not a feeling.
- **Execution is part of the edge.** A great opinion at a bad price is a bad bet.
- Bet size scales with confidence and bankroll, never with the last result.

**Doesn't transfer:** anything resting on non-public information. Walters was
convicted of insider trading in a securities case in 2017 (sentence later
commuted; pardoned in 2021). The sports-market lessons stand on their own; that
part is not a method to copy.

### "Big Bet Bob"
Treated here as an **archetype** rather than a biography — the public record on
this name is thin and mostly anecdote, so Jordan takes the structural lesson and
leaves the legend.

The archetype: a bettor whose wager size is itself a market event.

**Transfers:**
- **Above a certain size, you are the market.** Your own bet is your worst line
  movement.
- Get the bulk down at the opener or on the stale book, before you move the
  price against yourself.
- **Guard the play.** A number you leaked is a number you no longer have. This
  is also why "the play" you saw posted publicly is already gone.
- Every bet leaves a footprint. Books read betting patterns as data, and the
  reward for consistent winning at a soft shop is a limit cut, then a ban.

### Mikki Mase
High-stakes casino gambler, publicly known for very large baccarat and blackjack
sessions and for advantage-play claims.

**Method:** casino advantage play, not sports modelling — hunting situations
where the house edge is neutralised or reversed, betting enormous when the count
or the situation justifies it, and refusing to play at all when it does not.

**Transfers (bankroll psychology only):**
- **No edge, no bet.** The willingness to sit out an entire night is the skill.
  The tolerance for action is not.
- Bet size swings with edge size — never with mood or momentum.
- Know *why* the game is beatable before playing. If you can't articulate the
  mechanism, you are the mechanism.
- The house tolerates you until you win. Plan for the day access is cut.

**Doesn't transfer:** the public-facing side. Documented advantage play and a
large social following are different things, and results posted online are not
an audited record. Also: no casino intuition transfers to sports pricing. A card
count is a known, closed system. An NFL game is not.

### What all five agree on
Strip the styles away and the same four things remain:

1. **Get the best number.** Every one of them treats price as part of the edge.
2. **Size by edge, never by feel.** No chasing, no "due", no last-result logic.
3. **Pass constantly.** The default action is no action.
4. **Grade yourself honestly.** CLV and audited records, not highlight reels.

---

## 2. Pillar I — Real-Time Tracking & Market Signals

`jordan.market`

### The price is not a probability
`-110` implies 52.38%. Both sides of a -110/-110 market imply 104.76%. The 4.76%
is the book's hold, and it must be removed before any price is compared to
anything. See Pillar IV.

### Not all books are evidence
A price at a shop that will take $50,000 from a known winner is information. A
price at a shop that limits you to $200 and bans you for beating the close is
marketing. Jordan weights accordingly:

| Tier | Books | Weight |
|---|---|---|
| Market-makers | Pinnacle, Circa | 0.95–1.00 |
| Sharp-tolerant | BookMaker, BetCRIS | 0.80–0.85 |
| Retail majors | FanDuel, DraftKings, bet365 | 0.45–0.50 |
| Retail secondary | BetMGM, Caesars, ESPN Bet, Fanatics | 0.20–0.40 |
| DFS-style | PrizePicks, Underdog | 0.15 |

Consensus is weighted by book *and* by posted limit — a $500 Pinnacle price and
a $50,000 Pinnacle price are not the same statement.

### The signals, and what each is worth

**Steam.** Several books move the same direction, fast. Someone with size is in
the market. *Worth:* high, but usually already gone by the time you see it —
its real use is confirmation, not entry.

**Reverse line movement (RLM).** The tell that outlives the others. Requires
distinguishing two cases people constantly confuse — and note that ticket share
is measured on the side you are tracking:

| Tickets on this side | Price does | Reading |
|---|---|---|
| Few (≤40%) | shortens | **RLM — sharp money is on THIS side** |
| Many (≥60%) | drifts | **RLM — sharp money is on the OTHER side** |
| Many (≥60%) | shortens | ordinary public flow — *not* a signal |
| Few (≤40%) | drifts | ordinary public flow — *not* a signal |

Only the first two rows are information. A line moving *with* the tickets is
what is supposed to happen.

**Handle vs. ticket divergence.** 30% of tickets but 60% of the money is the
signature of few, large, confident wagers. This is the cleanest public proxy for
"who is betting", as opposed to "how many are betting".

**Market tightening.** Books widen when unsure and tighten when confident. A
market that has come in to a 2-cent hold has been vetted by real money. One
still sitting at 12 cents has not — which is exactly where mistakes live.

**Closing line value.** The only performance metric that is not mostly noise.
You beat the close or you didn't; over a few hundred bets, consistent CLV is
the difference between having an edge and having a story. Grade against the
**sharp consensus close**, not against the best stale price on the board —
grading yourself against a soft outlier flatters the result.

### Timing
- **Openers** are the softest numbers on the board and carry the lowest limits.
  This is where a real opinion gets paid, if you can get down.
- **Closers** are the sharpest. If your bet only looks good at the close, it
  wasn't an edge — it was consensus.
- **Injury news** creates the biggest repricing gaps. Speed matters more than
  analysis in the first ninety seconds; analysis matters more after.

---

## 3. Pillar II — Advanced Simulation & Projection Models

`jordan.simulate`

### Distributions, not point estimates
"I have him for 68 yards" is not a projection — the line is 64.5 and what you
need is the probability of clearing it, which depends entirely on the shape of
the distribution around 68.

Match the distribution to how the stat actually behaves:

| Stat type | Distribution | Why |
|---|---|---|
| Passing yards, team points | **Normal** | roughly symmetric, high volume |
| Receiving / rushing yards | **Lognormal** | floor at zero, long right tail |
| Receptions, strikeouts, made threes | **Negative binomial** | counts, overdispersed |
| Anytime TD, to record a sack | **Bernoulli** | it happens or it doesn't |

The skew case is worth stating plainly. On a mean of 68 with sd 28, the over on
90.5 prices at **17.9% lognormal vs 21.1% normal** — a fair price of +459
against +374, a gap of 85 cents on a single leg. Use a symmetric model on a skewed
stat and you systematically overpay for high overs, which is precisely the leg
the book wants in your parlay.

### Model the driver
Voulgaris' lesson, mechanically:

```
minutes/snaps  ->  usage rate  ->  volume  ->  efficiency  ->  the stat
```

Project the driver, then derive the stat. A player-points projection that
doesn't start from a minutes distribution is a guess wearing a number. And a
leg's variance is dominated by its driver's variance — which is why
**driver stability** is a scored input in Jordan's leg grade, not an afterthought.

### Blend against the market
The betting market is the single best model anyone has ever built. If your
projection disagrees with a well-limited market, you are usually the one who is
wrong. Jordan blends model and de-vigged market probability (default 50/50 via
`weight_model`) and bets the residual.

Raise `weight_model` only where you genuinely know more than the market — a
niche you have data on. Lower it on primary markets where a hundred sharp shops
have already looked.

### Respect your own error bars
Every simulated probability carries a standard error. With 40,000 trials the
95% interval on a 25% joint probability is about ±0.42%. **An edge smaller than
your simulation error is not an edge**, and Jordan downgrades a ticket to PASS
when the estimated edge sits inside the noise.

---

## 4. Pillar III — Correlation Data (the SGP weapon)

`jordan.correlation`

### Why this is the only real parlay edge
The book prices an SGP with its own correlation model plus margin. Where their
model is crude — and on secondary props it usually is — the true joint
probability and the offered price come apart. That gap is the bet.

If the legs are genuinely independent, there is no gap: you are just paying
compounded vig with extra steps.

### Correlation between *stats* becomes correlation between *bets*
A +0.55 correlation between QB passing yards and WR1 receiving yards becomes
**−0.55** if you take one over and one under. Books know this. The trade worth
finding is a pair whose sign is obvious to you and treated as independent by
the book's pricing.

### Selected priors

**NFL**
| Pair | Relationship | ρ |
|---|---|---|
| Pass yards × WR1 rec yards | same team | **+0.55** |
| Pass yards × pass TDs | same player | +0.52 |
| Rec yards × anytime TD | same player | +0.44 |
| Rush yards × anytime TD | same player | +0.41 |
| Pass yards × anytime TD | same team | +0.31 |
| Rush attempts × team win | same team | +0.35 |
| Pass attempts × team win | same team | **−0.28** |
| Pass yards × rush yards | same team | **−0.18** |
| WR1 rec yards × WR2 rec yards | same team | **−0.12** |
| Kicker points × teammate anytime TD | same team | **−0.15** |

**NBA**
| Pair | Relationship | ρ |
|---|---|---|
| Threes × points | same player | +0.62 |
| Points × minutes | same player | +0.58 |
| Assists × teammate points | same team | +0.34 |
| Points × opponent points | opponent | +0.16 |
| Minutes × team win | same team | **−0.22** |

**MLB**
| Pair | Relationship | ρ |
|---|---|---|
| Home run × total bases | same player | +0.66 |
| Total bases × runs | same player | +0.58 |
| Pitcher K × opponent runs | same team | **−0.34** |
| Earned runs × team win | same team | **−0.44** |

These are round-number starting points from box-score relationships, not
constants. **Every one of them moves with pace, game total and spread** — the
QB/WR1 correlation is stronger in a projected shootout than in a 37-point game.
Override them with your own numbers wherever you have them (`overrides` in the
ticket JSON).

### Impossible correlation matrices
Claim A/B = 0.9, B/C = 0.9 and A/C = −0.5 and no joint distribution exists —
you have described a world that cannot happen. Rather than crash on a bad guess,
Jordan clips the negative eigenvalues and renormalises to the nearest legal
matrix, then tells you it did. If your inputs needed repairing, at least one of
your assumptions was wrong.

### Stacks that work
- **NFL:** QB pass yards over + his WR1 receiving over. One long drive feeds both.
- **NFL:** QB pass TDs over + WR/TE anytime TD. Correlated by construction.
- **NFL:** Team total over + that team's RB rush attempts over. Leading teams run.
- **NFL:** Underdog +points + game under. Low-scoring keeps bad teams inside the number.
- **NBA:** Player points over + his minutes over. Minutes is the driver.
- **MLB:** Pitcher strikeouts over + opposing team total under. Same event.
- **MLB:** Player home run + his total bases over. A homer *is* four total bases.

### Stacks the book is happy to sell you
- **NFL:** QB pass yards over + same team's RB rush yards over. One football.
- **NFL:** Team blowout + that team's star's second-half production. Garbage time.
- **NFL:** Kicker points over + several teammate TDs. TDs replace field goals.
- **NBA:** Team big win + star minutes over. The blowout is why he sat.
- **MLB:** Pitcher win + opposing offence overs. Directly opposed outcomes.

---

## 5. Pillar IV — Market Inefficiencies & +EV

`jordan.odds`, `jordan.market`

### De-vig first, always
Four methods, and the choice matters more than people think — on a longshot the
methods disagree by several cents:

| Method | Use when |
|---|---|
| **Multiplicative** | tight two-way markets (the default workhorse) |
| **Additive** | rarely; too generous to longshots |
| **Power** | props and anything longer than +200 (favourite-longshot bias) |
| **Shin** | fat-hold markets, where some of the margin is information |

`conservative_probs()` quotes every side at its worst simultaneously — it
deliberately sums to less than 1 and is a stress test, not a distribution. If a
bet survives `survives_every_devig()`, the edge doesn't depend on which method
you happened to pick.

### Where the inefficiencies actually are
1. **Stale lines.** A soft book that hasn't moved after the sharp market did.
   The most reliably available edge, and the fastest way to get limited.
2. **Derivative markets.** Halves, quarters, team totals — priced by formula off
   a number that has itself already moved.
3. **Secondary props.** Books hold 8–15% here and update slowly, because the
   volume doesn't justify the attention. Bad prices survive longer.
4. **Correlation mispricing in SGPs.** Pillar III.
5. **Injury and weather latency.** The first ninety seconds after real news.
6. **Middles.** Two sides with a gap; win both if the result lands inside.
7. **Arbitrage.** Real, small, and the fastest possible route to a limit cut.
   Better read as a *signal* that one of the two prices is stale — and the stale
   side is usually the better standalone bet.

### Sizing
Full Kelly is optimal only if your probability is exactly right. It never is.

```
Kelly fraction  f* = (p·b − q) / b       b = decimal odds − 1
Jordan's stake  = min(0.25 · f*, 2% of bankroll)
```

Quarter-Kelly, capped at 2% of bankroll on any single wager, 5% total exposure
across correlated positions. A 2% edge at -110 is a 0.5-unit bet, not a
"lock of the year".

### Grading yourself
A 7-3 record proves nothing: the 95% interval on 70% from 10 bets runs from
**39.7% to 89.2%**, and break-even at -110 is 52.38%. You need on the order of
a thousand bets before a win rate distinguishes itself from luck. Until then,
**CLV is your only honest scoreboard.** Run `python3 -m jordan record 7 3` and
argue with the interval, not with Jordan.

---

## 6. House rules

1. The default answer is **PASS**.
2. No probability without a method behind it.
3. De-vig before comparing anything.
4. An edge smaller than the model's own error bar is not an edge.
5. Quarter-Kelly, 2% single-bet cap, 5% correlated exposure cap.
6. Never chase.
7. CLV is the scoreboard.
8. A parlay is a bet only when correlation beats the book's correlation pricing.
9. Line shop every single time.
10. Bet with money that has no other job.

---

## 7. What Jordan is not

Not a tipster, not a data feed, and not a guarantee. Every number here is an
estimate from a model that can be wrong, fed by inputs you supply — garbage
projections in, confident garbage out.

Sports betting is -EV for almost everyone who does it, and the honest reason is
that the margin built into the prices exceeds most people's edge, when they have
one at all. Bet only what you can lose without consequence, only where it is
legal, and never with borrowed money.

If it has stopped being optional, stop: **1-800-522-4700** (US National Problem
Gambling Helpline, 24/7, confidential).
