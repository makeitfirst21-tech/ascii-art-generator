"""Command line for Jordan.

    python3 -m jordan brief
    python3 -m jordan devig -110 -110
    python3 -m jordan ev --prob 0.55 --price -110 --bankroll 5000
    python3 -m jordan sgp ticket.json
    python3 -m jordan market snapshots.json
    python3 -m jordan stacks nfl
    python3 -m jordan record 57 43
"""

import argparse
import json
import sys

from . import correlation, market, odds, parlay, persona, simulate


def _load(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path) as fh:
        return json.load(fh)


def _pair_key(key):
    """'0-1' -> (0, 1)"""
    a, b = str(key).replace(",", "-").split("-")
    return (int(a), int(b))


# ------------------------------------------------------------------ commands


def cmd_brief(args):
    print(persona.brief())
    return 0


def cmd_devig(args):
    prices = [float(p) for p in args.prices]
    method = args.method or odds.recommended_devig(prices)
    probs = odds.devig(prices, method)
    print("Market : %s" % "  ".join(odds.fmt_american(p) for p in prices))
    print("Hold   : %.2f%%" % (100 * odds.hold(prices)))
    print("Method : %s%s" % (method, "" if args.method else "  (auto-selected)"))
    print()
    for price, prob in zip(prices, probs):
        print("  %-8s implied %6.2f%%   fair %6.2f%%   fair price %s"
              % (odds.fmt_american(price), 100 * odds.american_to_prob(price),
                 100 * prob, odds.fmt_american(odds.prob_to_american(prob))))
    if args.method is None:
        print()
        print("All methods, for comparison:")
        for name in ("multiplicative", "additive", "power", "shin"):
            got = odds.devig(prices, name)
            print("  %-15s %s" % (name, "  ".join("%.2f%%" % (100 * g) for g in got)))
        cons = odds.conservative_probs(prices)
        print("  %-15s %s   <- pessimistic on every side at once;"
              % ("conservative", "  ".join("%.2f%%" % (100 * g) for g in cons)))
        print("  %-15s    these do not sum to 100%% and are not meant to."
              % "")
        print()
        check = odds.survives_every_devig(prices, 0)
        print("First side at %s survives every method: %s (worst EV %+.2f%%)"
              % (odds.fmt_american(prices[0]),
                 "yes" if check["survives"] else "no", check["worst_ev"]))
    return 0


def cmd_ev(args):
    prob, price = args.prob, args.price
    ev = odds.ev_percent(prob, price)
    fair = odds.prob_to_american(prob)
    print("Price      : %s" % odds.fmt_american(price))
    print("Your prob  : %.2f%%   (break-even at this price: %.2f%%)"
          % (100 * prob, 100 * odds.breakeven_prob(price)))
    print("Fair price : %s   (you are getting %+.0f cents)"
          % (odds.fmt_american(fair), odds.edge_in_cents(prob, price)))
    print("EV         : %+.2f%% per unit staked" % ev)
    print("Full Kelly : %.2f%% of bankroll" % (100 * odds.kelly_fraction(prob, price)))
    stake = odds.kelly_stake(prob, price, args.bankroll,
                             multiplier=args.kelly, cap=args.cap)
    print("Stake      : %.2f  (%.0f%% Kelly, %.0f%% cap, bankroll %.2f)"
          % (stake, 100 * args.kelly, 100 * args.cap, args.bankroll))
    if ev <= 0:
        print()
        print("No bet. You need %.2f%% to break even here and you have %.2f%%."
              % (100 * odds.breakeven_prob(price), 100 * prob))
    elif ev < 2.0:
        print()
        print("Thin. A sub-2% edge is inside the error bar of almost any model.")
    return 0


def cmd_sgp(args):
    spec = _load(args.ticket)
    legs = [simulate.leg_from_spec(s) for s in spec["legs"]]
    rels = {_pair_key(k): v for k, v in (spec.get("relationships") or {}).items()}
    over = {_pair_key(k): float(v) for k, v in (spec.get("overrides") or {}).items()}
    stability = {s.get("label", "leg"): s.get("stability", 0.6) for s in spec["legs"]}
    signals = {s.get("label", "leg"): s.get("signal", 0.0) for s in spec["legs"]}

    report = parlay.analyse_parlay(
        legs,
        offered_price=spec.get("offered_price"),
        sport=spec.get("sport", "nfl"),
        overrides=over,
        relationships=rels,
        bankroll=spec.get("bankroll", 100.0),
        trials=args.trials,
        seed=args.seed,
        stability=stability,
        signals=signals,
        devig_method=spec.get("devig_method", "power"))
    print(report.render())

    if args.search and len(legs) > 2:
        print()
        print("ALTERNATIVE CONSTRUCTIONS (searching every subset)")
        print("-" * 78)
        best, all_reports = parlay.best_subset(
            legs, sport=spec.get("sport", "nfl"), overrides=over,
            relationships=rels, trials=max(args.trials // 4, 4000),
            bankroll=spec.get("bankroll", 100.0))
        for rep in all_reports[:6]:
            print("  %-52s EV %+7.2f%%  %s"
                  % (" + ".join(l.label for l in rep.legs)[:52],
                     rep.ev_pct, rep.verdict))
        print()
        if best and best.ev_pct <= 0:
            print("  Jordan's build: none of them. Every construction on this board is")
            print("  -EV, and the least bad one is still a losing bet. Pass the game.")
        elif best and len(best.legs) < len(legs):
            print("  Jordan's build: %s" % " + ".join(l.label for l in best.legs))
            print("  Shorter tickets win this search most of the time. Every leg you")
            print("  add multiplies the vig and adds a projection you can be wrong about.")
        elif best:
            print("  Jordan's build: the ticket as submitted -- no subset prices better.")
    print()
    print(persona.DISCLAIMER)
    return 0


def cmd_market(args):
    data = _load(args.snapshots)
    tracker = market.MarketTracker(data.get("name", "market"),
                                   devig_method=data.get("devig_method", "power"))
    for snap in data["snapshots"]:
        tracker.add(snap["book"], snap["price"],
                    timestamp=snap.get("timestamp"),
                    limit=snap.get("limit"),
                    opposite=snap.get("opposite"),
                    ticket_pct=snap.get("ticket_pct"),
                    handle_pct=snap.get("handle_pct"))

    print("=" * 78)
    print(("MARKET: %s" % tracker.name).center(78))
    print("=" * 78)
    consensus = tracker.sharp_consensus()
    if consensus:
        print("Sharp consensus fair : %s  (%.2f%%)"
              % (odds.fmt_american(tracker.consensus_price()), 100 * consensus))
    best = tracker.best_available()
    if best:
        print("Best available       : %s at %s"
              % (odds.fmt_american(best.price), best.book))
    print()

    print("SIGNALS")
    print("-" * 78)
    signals = tracker.all_signals()
    if not signals:
        print("  Nothing worth flagging. A quiet market is the normal state.")
    for sig in signals:
        print("  [%s] %-22s %s" % (sig.bar(), sig.kind, sig.message))
    print()

    outliers = tracker.outliers(args.threshold)
    print("+EV OUTLIERS (books behind the consensus)")
    print("-" * 78)
    if not outliers:
        print("  None past the %.1f%% threshold. This is the usual answer."
              % (100 * args.threshold))
    for o in outliers:
        print("  %-14s %-7s vs fair %-7s   EV %+.2f%%"
              % (o["book"], odds.fmt_american(o["price"]),
                 odds.fmt_american(o["fair_price"]), o["ev_pct"]))
    if data.get("bet_price") is not None:
        print()
        clv = tracker.closing_line_value(data["bet_price"], data.get("closing_price"))
        if clv:
            print("CLOSING LINE VALUE")
            print("-" * 78)
            print("  Bet %s vs close %s  ->  %+.0f cents, %s"
                  % (odds.fmt_american(clv["bet_price"]),
                     odds.fmt_american(clv["closing_price"]),
                     clv["cents"],
                     "beat the close" if clv["beat_close"] else "lost to the close"))
            print("  Implied long-run ROI at this CLV: %+.2f%%" % clv["roi_estimate"])
    print("=" * 78)
    return 0


def cmd_stacks(args):
    sport = args.sport.lower()
    print("=" * 78)
    print(("CORRELATION PRIORS -- %s" % sport.upper()).center(78))
    print("=" * 78)
    book = correlation.PRIOR_BOOKS.get(sport)
    if not book:
        print("No priors for %r. Have: %s"
              % (sport, ", ".join(sorted(correlation.PRIOR_BOOKS))))
        return 1
    for (a, b, rel), rho in sorted(book.items(), key=lambda kv: -abs(kv[1])):
        print("  %+.2f  %-18s x %-18s (%s)" % (rho, a, b, rel))
    print()
    print("STACKS THAT WORK")
    print("-" * 78)
    for sp, name, why in correlation.POSITIVE_STACKS:
        if sp == sport:
            print("  + %s" % name)
            print("      %s" % why)
    print()
    print("STACKS THE BOOK IS HAPPY TO SELL YOU")
    print("-" * 78)
    for sp, name, why in correlation.NEGATIVE_STACKS:
        if sp == sport:
            print("  - %s" % name)
            print("      %s" % why)
    print("=" * 78)
    return 0


def cmd_record(args):
    r = parlay.record_grade(args.wins, args.losses, args.pushes)
    print("Record      : %d-%d (%d bets)" % (args.wins, args.losses, r["n"]))
    if r["n"]:
        print("Win rate    : %.1f%%" % r["win_pct"])
        print("95%% interval: %.1f%% - %.1f%%" % (r["ci_low"], r["ci_high"]))
        print("Break-even  : %.2f%% at -110" % r["breakeven_pct"])
        print()
        print(r["note"])
    return 0


def cmd_arb(args):
    res = market.arbitrage(args.price_a, args.price_b, args.bankroll)
    if not res:
        print("No arbitrage: the two prices imply %.2f%%, which is over 100%%."
              % (100 * (odds.american_to_prob(args.price_a)
                        + odds.american_to_prob(args.price_b))))
        return 1
    print("Arbitrage found: %.3f%% guaranteed" % res["profit_pct"])
    print("  Stake %.2f on %s" % (res["stake_a"], odds.fmt_american(args.price_a)))
    print("  Stake %.2f on %s" % (res["stake_b"], odds.fmt_american(args.price_b)))
    print("  Returns %.2f on a %.2f outlay" % (res["guaranteed_return"], args.bankroll))
    print()
    print("Worth knowing: books void obvious arbs, and consistently taking them is")
    print("the fastest way to get limited. Treat it as a signal that one of the two")
    print("prices is stale -- the stale side is usually the better standalone bet.")
    return 0


def cmd_parlay(args):
    """Quick hold check on a straight parlay -- no model needed."""
    prices = [float(p) for p in args.prices]
    markets = [[p, -p if p > 0 else abs(p)] for p in prices]
    print("Legs        : %s" % "  ".join(odds.fmt_american(p) for p in prices))
    print("Parlay pays : %s" % odds.fmt_american(odds.parlay_american(prices)))
    print("Effective hold on this ticket: %.2f%%"
          % (100 * odds.parlay_hold(markets)))
    print()
    print("For comparison, one leg at %s holds %.2f%%."
          % (odds.fmt_american(prices[0]), 100 * odds.hold(markets[0])))
    print("Vig compounds. That is the entire business model of the parlay.")
    return 0


# -------------------------------------------------------------------- parser


def build_parser():
    p = argparse.ArgumentParser(
        prog="jordan",
        description="Jordan -- betting analysis: markets, models, correlation, EV.",
        epilog="Jordan's default answer is 'pass'. " + persona.DISCLAIMER)
    sub = p.add_subparsers(dest="command")

    s = sub.add_parser("brief", help="who Jordan is and how he thinks")
    s.set_defaults(func=cmd_brief)

    s = sub.add_parser("devig", help="strip the vig off a market")
    s.add_argument("prices", nargs="+", help="american prices, all sides")
    s.add_argument("--method", choices=sorted(odds.DEVIG_METHODS),
                   help="default: auto-selected by market shape")
    s.set_defaults(func=cmd_devig)

    s = sub.add_parser("ev", help="EV and stake for a probability and a price")
    s.add_argument("--prob", type=float, required=True, help="your true probability")
    s.add_argument("--price", type=float, required=True, help="american price offered")
    s.add_argument("--bankroll", type=float, default=100.0)
    s.add_argument("--kelly", type=float, default=0.25, help="Kelly multiplier")
    s.add_argument("--cap", type=float, default=0.02, help="max fraction of bankroll")
    s.set_defaults(func=cmd_ev)

    s = sub.add_parser("sgp", help="full same-game-parlay analysis from a JSON ticket")
    s.add_argument("ticket", help="path to ticket JSON, or - for stdin")
    s.add_argument("--trials", type=int, default=40000)
    s.add_argument("--seed", type=int, default=None)
    s.add_argument("--search", action="store_true",
                   help="also search every subset for a better construction")
    s.set_defaults(func=cmd_sgp)

    s = sub.add_parser("market", help="signals and +EV outliers from price snapshots")
    s.add_argument("snapshots", help="path to snapshots JSON, or - for stdin")
    s.add_argument("--threshold", type=float, default=0.02,
                   help="minimum probability edge to flag (default 0.02)")
    s.set_defaults(func=cmd_market)

    s = sub.add_parser("stacks", help="correlation priors and stack guidance")
    s.add_argument("sport", nargs="?", default="nfl", help="nfl, nba or mlb")
    s.set_defaults(func=cmd_stacks)

    s = sub.add_parser("record", help="what a win-loss record actually proves")
    s.add_argument("wins", type=int)
    s.add_argument("losses", type=int)
    s.add_argument("pushes", type=int, nargs="?", default=0)
    s.set_defaults(func=cmd_record)

    s = sub.add_parser("arb", help="check two prices for arbitrage")
    s.add_argument("price_a", type=float)
    s.add_argument("price_b", type=float)
    s.add_argument("--bankroll", type=float, default=1000.0)
    s.set_defaults(func=cmd_arb)

    s = sub.add_parser("parlay", help="effective hold on a straight parlay")
    s.add_argument("prices", nargs="+")
    s.set_defaults(func=cmd_parlay)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)
