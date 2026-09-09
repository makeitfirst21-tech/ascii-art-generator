"""Tests for the Jordan package. Run: python3 -m unittest discover -s tests -v"""

import math
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jordan import (correlation, keynumbers, market, odds, parlay, persona,
                    simulate, stats)


class TestOdds(unittest.TestCase):

    def test_conversions_round_trip(self):
        for price in (-350, -110, -101, 100, 145, 900):
            dec = odds.american_to_decimal(price)
            self.assertAlmostEqual(odds.decimal_to_american(dec), price, delta=1)

    def test_known_values(self):
        self.assertAlmostEqual(odds.american_to_decimal(-110), 1.909090, places=5)
        self.assertAlmostEqual(odds.american_to_decimal(150), 2.5, places=9)
        self.assertAlmostEqual(odds.american_to_prob(-110), 0.523809, places=5)

    def test_hold_of_standard_market(self):
        self.assertAlmostEqual(odds.hold([-110, -110]), 0.047619, places=5)

    def test_devig_methods_all_sum_to_one(self):
        for prices in ([-110, -110], [+450, -700], [+120, -145], [+250, +260, +400]):
            for name in odds.DEVIG_METHODS:
                probs = odds.devig(prices, name)
                self.assertAlmostEqual(sum(probs), 1.0, places=8,
                                       msg="%s on %s" % (name, prices))
                for p in probs:
                    self.assertTrue(0.0 < p < 1.0)

    def test_conservative_probs_are_pessimistic_and_not_a_distribution(self):
        """Every side quoted at its worst at once -- so it must sum to under 1."""
        prices = [450, -700]
        cons = odds.conservative_probs(prices)
        self.assertLess(sum(cons), 1.0)
        for name in odds.DEVIG_METHODS:
            for c, m in zip(cons, odds.devig(prices, name)):
                self.assertLessEqual(c, m + 1e-12)

    def test_survives_every_devig(self):
        # a genuinely good price survives; a bad one does not
        good = odds.survives_every_devig([200, -300], 0)
        self.assertIn("conservative", good["by_method"])
        bad = odds.survives_every_devig([-120, -120], 0)
        self.assertFalse(bad["survives"])

    def test_devig_symmetric_market_is_a_coin_flip(self):
        for name in odds.DEVIG_METHODS:
            probs = odds.devig([-110, -110], name)
            self.assertAlmostEqual(probs[0], 0.5, places=6)

    def test_power_devig_charges_the_longshot_more(self):
        """The favourite-longshot bias: power should give the longshot a lower
        fair probability than plain proportional de-vigging does."""
        mult = odds.devig([+450, -700], "multiplicative")
        power = odds.devig([+450, -700], "power")
        self.assertLess(power[0], mult[0])

    def test_recommended_devig_picks_power_for_longshots(self):
        self.assertEqual(odds.recommended_devig([+450, -700]), "power")
        self.assertEqual(odds.recommended_devig([-110, -110]), "multiplicative")

    def test_ev_and_kelly_agree_on_sign(self):
        self.assertGreater(odds.ev_percent(0.55, -110), 0)
        self.assertGreater(odds.kelly_fraction(0.55, -110), 0)
        self.assertLess(odds.ev_percent(0.50, -110), 0)
        self.assertLessEqual(odds.kelly_fraction(0.50, -110), 0)

    def test_breakeven_is_ev_neutral(self):
        p = odds.breakeven_prob(-110)
        self.assertAlmostEqual(odds.expected_value(p, -110), 0.0, places=9)

    def test_kelly_stake_respects_cap(self):
        # a monster edge should still be capped at 2% of bankroll
        stake = odds.kelly_stake(0.90, +100, bankroll=1000.0)
        self.assertAlmostEqual(stake, 20.0, places=6)

    def test_kelly_stake_zero_when_no_edge(self):
        self.assertEqual(odds.kelly_stake(0.40, -110, 1000.0), 0.0)

    def test_parlay_price_is_product_of_decimals(self):
        self.assertEqual(odds.parlay_american([100, 100]), 300)
        self.assertEqual(odds.parlay_american([-110, -110, -110]), 596)

    def test_parlay_hold_compounds(self):
        """Known figures: a three-leg -110 parlay holds ~13%, six legs ~24%."""
        three = odds.parlay_hold([[-110, -110]] * 3)
        six = odds.parlay_hold([[-110, -110]] * 6)
        self.assertAlmostEqual(three, 0.1303, places=3)
        self.assertAlmostEqual(six, 0.2436, places=3)
        self.assertGreater(six, three)

    def test_edge_in_cents(self):
        self.assertAlmostEqual(odds.edge_in_cents(0.5, 120), 20, delta=1)


class TestStats(unittest.TestCase):

    def test_norm_ppf_inverts_cdf(self):
        for p in (0.001, 0.05, 0.25, 0.5, 0.75, 0.95, 0.999):
            self.assertAlmostEqual(stats.norm_cdf(stats.norm_ppf(p)), p, places=9)

    def test_norm_ppf_known_quantiles(self):
        self.assertAlmostEqual(stats.norm_ppf(0.975), 1.959964, places=5)
        self.assertAlmostEqual(stats.norm_ppf(0.5), 0.0, places=9)

    def test_poisson_cdf_matches_hand_calculation(self):
        # P(X<=1) for lambda=2 is 3*e^-2
        self.assertAlmostEqual(stats.poisson_cdf(1, 2.0), 3 * math.exp(-2), places=9)

    def test_negbin_mean_is_recovered(self):
        draws = [stats.negbin_ppf((i + 0.5) / 4000.0, 6.0, 9.0) for i in range(4000)]
        self.assertAlmostEqual(sum(draws) / len(draws), 6.0, delta=0.4)

    def test_cholesky_reconstructs_the_matrix(self):
        m = [[1.0, 0.4, 0.2], [0.4, 1.0, 0.3], [0.2, 0.3, 1.0]]
        L = stats.cholesky(m)
        for i in range(3):
            for j in range(3):
                got = sum(L[i][k] * L[j][k] for k in range(3))
                self.assertAlmostEqual(got, m[i][j], places=9)

    def test_cholesky_rejects_impossible_matrix(self):
        with self.assertRaises(ValueError):
            stats.cholesky([[1.0, 0.9, -0.5], [0.9, 1.0, 0.9], [-0.5, 0.9, 1.0]])

    def test_nearest_correlation_repairs_impossible_input(self):
        bad = [[1.0, 0.9, -0.5], [0.9, 1.0, 0.9], [-0.5, 0.9, 1.0]]
        self.assertFalse(stats.is_positive_definite(bad))
        fixed = stats.nearest_correlation(bad)
        self.assertTrue(stats.is_positive_definite(fixed))
        for i in range(3):
            self.assertAlmostEqual(fixed[i][i], 1.0, places=9)

    def test_nearest_correlation_leaves_valid_input_alone(self):
        good = [[1.0, 0.4], [0.4, 1.0]]
        fixed = stats.nearest_correlation(good)
        self.assertAlmostEqual(fixed[0][1], 0.4, places=9)

    def test_copula_reproduces_target_correlation(self):
        import random
        c = stats.GaussianCopula([[1.0, 0.6], [0.6, 1.0]], rng=random.Random(42))
        xs, ys = [], []
        for _ in range(30000):
            a, b = c.sample_normals()
            xs.append(a)
            ys.append(b)
        self.assertAlmostEqual(stats.pearson(xs, ys), 0.6, delta=0.02)

    def test_wilson_interval_brackets_the_point_estimate(self):
        lo, hi = stats.wilson_interval(55, 100)
        self.assertLess(lo, 0.55)
        self.assertGreater(hi, 0.55)
        # more data must narrow the interval
        lo2, hi2 = stats.wilson_interval(550, 1000)
        self.assertLess(hi2 - lo2, hi - lo)


class TestSimulate(unittest.TestCase):

    def test_normal_prob_over_is_analytic(self):
        n = simulate.NormalStat(100.0, 20.0)
        self.assertAlmostEqual(n.prob_over(100.0), 0.5, places=9)
        self.assertAlmostEqual(n.prob_over(120.0), 1 - stats.norm_cdf(1.0), places=9)

    def test_lognormal_preserves_the_requested_mean(self):
        ln = simulate.LognormalStat(70.0, 28.0)
        draws = [ln.ppf((i + 0.5) / 20000.0) for i in range(20000)]
        self.assertAlmostEqual(sum(draws) / len(draws), 70.0, delta=1.5)

    def test_lognormal_is_more_conservative_on_a_high_line(self):
        """Skew matters: a symmetric model overprices the over on a big number."""
        ln = simulate.LognormalStat(68.0, 28.0)
        nm = simulate.NormalStat(68.0, 28.0)
        self.assertLess(ln.prob_over(90.5), nm.prob_over(90.5))

    def test_count_stat_matches_poisson_when_not_overdispersed(self):
        c = simulate.CountStat(4.0, 4.0)
        self.assertAlmostEqual(c.prob_over(3.5), 1 - stats.poisson_cdf(3, 4.0), places=9)

    def test_bernoulli_prob(self):
        b = simulate.BernoulliStat(0.42)
        self.assertAlmostEqual(b.prob_over(0.5), 0.42, places=9)
        self.assertEqual(b.ppf(0.99), 1.0)
        self.assertEqual(b.ppf(0.01), 0.0)

    def test_under_side_is_the_complement(self):
        over = simulate.Leg("x", simulate.NormalStat(100, 20), 110, "over", -110)
        under = simulate.Leg("x", simulate.NormalStat(100, 20), 110, "under", -110)
        self.assertAlmostEqual(over.model_prob() + under.model_prob(), 1.0, places=9)

    def test_blended_prob_sits_between_model_and_market(self):
        leg = simulate.Leg("x", simulate.NormalStat(100, 20), 95, "over", -110,
                           market_prices=[-110, -110], weight_model=0.5)
        model = leg.model_prob()
        mkt = leg.market_prob()
        blended = leg.blended_prob()
        self.assertLessEqual(min(model, mkt) - 1e-9, blended)
        self.assertGreaterEqual(max(model, mkt) + 1e-9, blended)

    def test_independent_simulation_matches_the_product(self):
        legs = [simulate.Leg("a", simulate.NormalStat(100, 20), 100, "over", -110),
                simulate.Leg("b", simulate.NormalStat(50, 10), 50, "over", -110)]
        res = simulate.Simulation(legs, trials=40000, seed=1).run()
        self.assertAlmostEqual(res.joint_prob, 0.25, delta=0.015)
        self.assertAlmostEqual(res.correlation_multiplier, 1.0, delta=0.06)

    def test_positive_correlation_raises_the_joint_probability(self):
        def build(rho):
            legs = [simulate.Leg("a", simulate.NormalStat(100, 20), 100, "over", -110),
                    simulate.Leg("b", simulate.NormalStat(50, 10), 50, "over", -110)]
            return simulate.Simulation(legs, [[1, rho], [rho, 1]],
                                       trials=40000, seed=2).run()
        self.assertGreater(build(0.6).joint_prob, build(0.0).joint_prob)
        self.assertLess(build(-0.6).joint_prob, build(0.0).joint_prob)

    def test_hit_distribution_sums_to_one(self):
        legs = [simulate.Leg("a", simulate.NormalStat(100, 20), 100, "over", -110),
                simulate.Leg("b", simulate.NormalStat(50, 10), 50, "over", -110)]
        res = simulate.Simulation(legs, trials=5000, seed=4).run()
        self.assertAlmostEqual(sum(res.hit_distribution), 1.0, places=9)

    def test_spread_and_win_prob_are_inverses(self):
        for spread in (-7.0, -3.0, 0.0, 2.5, 6.5):
            p = simulate.spread_to_win_prob(spread)
            self.assertAlmostEqual(simulate.win_prob_to_spread(p), spread, places=6)

    def test_simulation_honours_the_model_market_blend(self):
        """The joint probability must use the same number the leg grade shows."""
        leg = simulate.Leg("x", simulate.NormalStat(100, 20), 90, "over", -110,
                           market_prices=[+200, -260], weight_model=0.5)
        blended = leg.blended_prob()
        self.assertLess(blended, leg.model_prob() - 0.1)   # market pulls it down hard
        res = simulate.Simulation([leg], trials=40000, seed=1).run()
        self.assertAlmostEqual(res.leg_probs[0], blended, delta=0.01)

    def test_effective_line_reports_where_the_blend_lands(self):
        leg = simulate.Leg("x", simulate.NormalStat(100, 20), 90, "over", -110,
                           market_prices=[+200, -260], weight_model=0.5)
        res = simulate.Simulation([leg], trials=4000, seed=1).run()
        # market says he is worse than the model, so the real line is higher
        self.assertGreater(res.effective_lines[0], 90)

    def test_bet_level_sign_is_correct_for_opposite_sides(self):
        """QB over + RB under should HELP each other; both overs should fight."""
        def build(rb_side):
            qb = simulate.leg_from_spec({"label": "qb", "stat": "pass_yards",
                                         "dist": "normal", "mean": 270, "sd": 60,
                                         "line": 250, "side": "over"})
            rb = simulate.leg_from_spec({"label": "rb", "stat": "rush_yards",
                                         "dist": "normal", "mean": 70, "sd": 25,
                                         "line": 65, "side": rb_side})
            m = correlation.build_matrix([qb, rb], "nfl",
                                         relationships={(0, 1): "same_team"})
            return simulate.Simulation([qb, rb], m, trials=40000, seed=2).run()
        self.assertGreater(build("under").correlation_multiplier, 1.02)
        self.assertLess(build("over").correlation_multiplier, 0.98)

    def test_realized_bet_correlation_flips_with_the_side(self):
        def rho(rb_side):
            qb = simulate.leg_from_spec({"stat": "pass_yards", "dist": "normal",
                                         "mean": 270, "sd": 60, "line": 250, "side": "over"})
            rb = simulate.leg_from_spec({"stat": "rush_yards", "dist": "normal",
                                         "mean": 70, "sd": 25, "line": 65, "side": rb_side})
            m = correlation.build_matrix([qb, rb], "nfl",
                                         relationships={(0, 1): "same_team"})
            res = simulate.Simulation([qb, rb], m, trials=20000, seed=3).run()
            return res.realized_bet_correlation()[0][1]
        self.assertGreater(rho("under"), 0)
        self.assertLess(rho("over"), 0)

    def test_push_probability_is_simulated_on_whole_number_lines(self):
        leg = simulate.Leg("rec", simulate.CountStat(6.0, 8.0), 6, "over", -110)
        sim = simulate.Simulation([leg], trials=30000, seed=4)
        self.assertGreater(sim.push_probs[0], 0.05)
        res = sim.run()
        self.assertGreater(res.push_rate, 0.05)
        # win + push + loss must account for everything
        self.assertLess(res.leg_probs[0] + res.push_rate, 1.0)

    def test_no_push_on_a_half_point_line(self):
        leg = simulate.Leg("rec", simulate.CountStat(6.0, 8.0), 5.5, "over", -110)
        sim = simulate.Simulation([leg], trials=2000, seed=4)
        self.assertEqual(sim.push_probs[0], 0.0)

    def test_push_reduces_the_parlay_instead_of_killing_it(self):
        """A pushed leg drops out; the ticket pays on the rest."""
        legs = [simulate.Leg("a", simulate.CountStat(6.0, 8.0), 6, "over", -110),
                simulate.Leg("b", simulate.NormalStat(100, 20), 90, "over", -110)]
        sim = simulate.Simulation(legs, trials=30000, seed=5)
        with_push = sim.run(offered_price=260).ev_per_unit
        # same legs on half-point lines cannot push
        legs2 = [simulate.Leg("a", simulate.CountStat(6.0, 8.0), 5.5, "over", -110),
                 simulate.Leg("b", simulate.NormalStat(100, 20), 90, "over", -110)]
        no_push = simulate.Simulation(legs2, trials=30000, seed=5).run(
            offered_price=260).ev_per_unit
        self.assertNotAlmostEqual(with_push, no_push, places=3)

    def test_simulated_ev_matches_the_closed_form_when_no_pushes(self):
        legs = [simulate.Leg("a", simulate.NormalStat(100, 20), 100, "over", -110),
                simulate.Leg("b", simulate.NormalStat(50, 10), 50, "over", -110)]
        res = simulate.Simulation(legs, trials=60000, seed=6).run(offered_price=300)
        closed = odds.expected_value(res.joint_prob, 300)
        self.assertAlmostEqual(res.ev_per_unit, closed, delta=0.02)

    def test_leg_from_spec(self):
        leg = simulate.leg_from_spec({
            "label": "WR yards", "stat": "rec_yards", "dist": "lognormal",
            "mean": 70, "sd": 28, "line": 64.5, "side": "over", "price": -115})
        self.assertEqual(leg.label, "WR yards")
        self.assertEqual(leg.stat, "rec_yards")
        self.assertIsInstance(leg.marginal, simulate.LognormalStat)

    def test_leg_from_spec_rejects_unknown_distribution(self):
        with self.assertRaises(ValueError):
            simulate.leg_from_spec({"dist": "wishful", "mean": 1})


class TestCorrelation(unittest.TestCase):

    def test_prior_lookup_is_symmetric(self):
        a = correlation.prior("nfl", "pass_yards", "rec_yards", "same_team")
        b = correlation.prior("nfl", "rec_yards", "pass_yards", "same_team")
        self.assertEqual(a, b)
        self.assertGreater(a, 0.4)

    def test_unknown_prior_is_zero_not_an_error(self):
        self.assertEqual(correlation.prior("nfl", "nonsense", "gibberish", "same_team"), 0.0)

    def test_qb_and_rb_share_one_football(self):
        self.assertLess(correlation.prior("nfl", "pass_yards", "rush_yards", "same_team"), 0)

    def test_side_flip(self):
        self.assertEqual(correlation.flip_for_sides(0.5, "over", "over"), 0.5)
        self.assertEqual(correlation.flip_for_sides(0.5, "over", "under"), -0.5)
        self.assertEqual(correlation.flip_for_sides(0.5, "under", "under"), 0.5)

    def test_build_matrix_is_valid_and_symmetric(self):
        legs = [simulate.leg_from_spec(
            {"label": l, "stat": s, "side": sd, "dist": "normal",
             "mean": 50, "sd": 10, "line": 50})
            for l, s, sd in (("qb", "pass_yards", "over"),
                             ("wr", "rec_yards", "over"),
                             ("rb", "rush_yards", "under"))]
        m = correlation.build_matrix(legs, "nfl", relationships={
            (0, 1): "same_team", (0, 2): "same_team", (1, 2): "same_team"})
        self.assertTrue(stats.is_positive_definite(m))
        for i in range(3):
            self.assertAlmostEqual(m[i][i], 1.0, places=9)
            for j in range(3):
                self.assertAlmostEqual(m[i][j], m[j][i], places=9)

    def test_build_matrix_is_on_the_stat_scale_not_the_bet_scale(self):
        """The matrix must NOT be pre-flipped for over/under.

        The simulation samples stats and checks them against the lines, so it
        derives the bet relationship itself. Flipping here too would apply the
        sign twice and invert the answer.
        """
        qb = simulate.leg_from_spec({"stat": "pass_yards", "side": "over",
                                     "dist": "normal", "mean": 270, "sd": 60, "line": 250})
        rb_under = simulate.leg_from_spec({"stat": "rush_yards", "side": "under",
                                           "dist": "normal", "mean": 70, "sd": 25, "line": 65})
        rb_over = simulate.leg_from_spec({"stat": "rush_yards", "side": "over",
                                          "dist": "normal", "mean": 70, "sd": 25, "line": 65})
        raw = correlation.prior("nfl", "pass_yards", "rush_yards", "same_team")
        for other in (rb_under, rb_over):
            m = correlation.build_matrix([qb, other], "nfl",
                                         relationships={(0, 1): "same_team"})
            self.assertAlmostEqual(m[0][1], raw, places=9)

    def test_context_scaling(self):
        self.assertEqual(correlation.context_scale(None), 1.0)
        shootout = correlation.context_scale({"total": 54, "base_total": 44})
        rock_fight = correlation.context_scale({"total": 36, "base_total": 44})
        self.assertGreater(shootout, 1.0)
        self.assertLess(rock_fight, 1.0)
        # blowouts decouple, and the scale is clamped
        self.assertLess(correlation.context_scale({"spread": 24}), 1.0)
        self.assertGreaterEqual(correlation.context_scale({"total": 200, "base_total": 20}), 0.6)
        self.assertLessEqual(correlation.context_scale({"total": 200, "base_total": 20}), 1.4)

    def test_overrides_beat_priors(self):
        legs = [simulate.leg_from_spec(
            {"stat": "pass_yards", "side": "over", "dist": "normal", "mean": 1, "sd": 1, "line": 1}),
            simulate.leg_from_spec(
            {"stat": "rec_yards", "side": "over", "dist": "normal", "mean": 1, "sd": 1, "line": 1})]
        m = correlation.build_matrix(legs, "nfl", overrides={(0, 1): -0.3})
        self.assertAlmostEqual(m[0][1], -0.3, places=6)

    def test_describe_matrix_sorts_by_magnitude(self):
        m = [[1.0, 0.1, 0.8], [0.1, 1.0, -0.5], [0.8, -0.5, 1.0]]
        described = correlation.describe_matrix(m, ["a", "b", "c"])
        self.assertEqual(described[0][0], 0.8)
        self.assertEqual(abs(described[-1][0]), 0.1)


class TestMarket(unittest.TestCase):

    def _tracker(self, now=None):
        now = now or time.time()
        t = market.MarketTracker("test")
        t.add("pinnacle", -103, timestamp=now - 3600, limit=20000, opposite=-109,
              ticket_pct=32, handle_pct=61)
        t.add("pinnacle", -119, timestamp=now - 200, limit=40000, opposite=+107,
              ticket_pct=32, handle_pct=61)
        t.add("draftkings", -107, timestamp=now - 3600, opposite=-113, ticket_pct=33)
        t.add("draftkings", -120, timestamp=now - 150, opposite=+100, ticket_pct=33)
        t.add("betmgm", -110, timestamp=now - 3600, opposite=-110)
        t.add("betmgm", -118, timestamp=now - 120, opposite=-102)
        t.add("fanatics", -100, timestamp=now - 90, opposite=-120)
        return t

    def test_book_weights_favour_sharp_books(self):
        self.assertGreater(market.book_weight("pinnacle"), market.book_weight("espnbet"))
        self.assertEqual(market.book_weight("nonexistent book"), 0.30)

    def test_sharp_consensus_lands_between_the_quotes(self):
        t = self._tracker()
        c = t.sharp_consensus()
        self.assertTrue(0.5 < c < 0.6)

    def test_best_available_finds_the_best_price(self):
        t = self._tracker()
        self.assertEqual(t.best_available().book, "fanatics")

    def test_outliers_flag_the_stale_soft_book(self):
        t = self._tracker()
        out = t.outliers(0.01)
        self.assertTrue(any(o["book"] == "fanatics" for o in out))
        for o in out:
            self.assertGreater(o["ev_pct"], 0)

    def test_outliers_never_include_sharp_books(self):
        t = self._tracker()
        for o in t.outliers(0.0):
            self.assertNotIn(o["book"].lower(), market.SHARP_BOOKS)

    def test_steam_detected_across_books(self):
        t = self._tracker()
        sig = t.steam(window_seconds=600, min_books=3, min_cents=8)
        self.assertIsNotNone(sig)
        self.assertEqual(sig.kind, "steam")
        self.assertIn("shortening", sig.detail["direction"])

    def test_reverse_line_movement_when_the_unpopular_side_shortens(self):
        t = self._tracker()
        sig = t.reverse_line_movement()
        self.assertIsNotNone(sig)
        self.assertEqual(sig.detail["sharp_side"], "this side")

    def test_public_flow_is_not_reported_as_rlm(self):
        """Tickets and line moving the same way is normal, not a signal."""
        now = time.time()
        t = market.MarketTracker("public")
        t.add("draftkings", -105, timestamp=now - 3600, ticket_pct=75)
        t.add("draftkings", -125, timestamp=now - 60, ticket_pct=75)
        self.assertIsNone(t.reverse_line_movement())
        flow = t.public_flow()
        self.assertEqual(len(flow), 1)
        self.assertEqual(flow[0].kind, "public_flow")

    def test_rlm_when_the_public_side_drifts(self):
        now = time.time()
        t = market.MarketTracker("fade")
        t.add("pinnacle", -120, timestamp=now - 3600, ticket_pct=78)
        t.add("pinnacle", -104, timestamp=now - 60, ticket_pct=78)
        sig = t.reverse_line_movement()
        self.assertIsNotNone(sig)
        self.assertEqual(sig.detail["sharp_side"], "the other side")

    def test_handle_divergence(self):
        t = self._tracker()
        sigs = t.handle_ticket_divergence()
        self.assertTrue(any("pinnacle" in s.message for s in sigs))

    def test_clv_uses_consensus_not_best_price(self):
        t = self._tracker()
        clv = t.closing_line_value(-104)
        self.assertEqual(clv["closing_price"], t.consensus_price())
        self.assertTrue(clv["beat_close"])
        self.assertGreater(clv["cents"], 0)

    def test_clv_negative_when_you_lose_to_the_close(self):
        t = self._tracker()
        clv = t.closing_line_value(-135)
        self.assertFalse(clv["beat_close"])
        self.assertLess(clv["roi_estimate"], 0)

    def test_signal_strength_is_bounded(self):
        t = self._tracker()
        for sig in t.all_signals():
            self.assertTrue(0.0 <= sig.strength <= 1.0)
            self.assertEqual(len(sig.bar(10)), 10)

    def test_arbitrage_found_and_stakes_balance(self):
        res = market.arbitrage(115, -105, bankroll=1000.0)
        self.assertIsNotNone(res)
        self.assertGreater(res["profit_pct"], 0)
        self.assertAlmostEqual(res["stake_a"] + res["stake_b"], 1000.0, places=6)
        # both sides must return the same amount -- that is what makes it an arb
        a = res["stake_a"] * odds.american_to_decimal(115)
        b = res["stake_b"] * odds.american_to_decimal(-105)
        self.assertAlmostEqual(a, b, places=4)

    def test_no_arbitrage_on_a_normal_market(self):
        self.assertIsNone(market.arbitrage(-110, -110))

    def test_middle(self):
        m = market.middle(-2.5, -110, 3.5, -110)
        self.assertAlmostEqual(m["width"], 6.0, places=9)
        self.assertGreater(m["middle_prob"], 0)


class TestParlay(unittest.TestCase):

    def _leg(self, label, mean, sd, line, side="over", price=-110, market_prices=None,
             stat=None):
        leg = simulate.Leg(label, simulate.NormalStat(mean, sd), line, side, price,
                           market_prices)
        leg.stat = stat
        return leg

    def test_grade_leg_returns_a_band(self):
        g = parlay.grade_leg(self._leg("a", 100, 20, 95), usage_stability=0.9)
        self.assertIn(g.letter, "ABCDF")
        self.assertTrue(0 <= g.score <= 100)
        self.assertEqual(set(g.components), {
            "edge", "line_placement", "driver_stability", "market_agreement",
            "price_efficiency", "correlation_fit"})

    def test_stable_driver_grades_higher(self):
        leg = self._leg("a", 100, 20, 95)
        high = parlay.grade_leg(leg, usage_stability=0.95)
        low = parlay.grade_leg(leg, usage_stability=0.2)
        self.assertGreater(high.score, low.score)
        self.assertTrue(any("Volatile driver" in n for n in low.notes))

    def test_tail_lines_are_penalised(self):
        near = parlay.grade_leg(self._leg("a", 100, 20, 101), usage_stability=0.8)
        far = parlay.grade_leg(self._leg("b", 100, 20, 145), usage_stability=0.8)
        self.assertGreater(near.components["line_placement"],
                           far.components["line_placement"])
        self.assertTrue(any("tail bet" in n for n in far.notes))

    def test_negative_ev_leg_is_flagged(self):
        g = parlay.grade_leg(self._leg("a", 100, 20, 130, price=-110))
        self.assertLess(g.ev_pct, 0)
        self.assertTrue(any("Negative EV" in n for n in g.notes))

    def test_correlated_parlay_beats_the_independent_price(self):
        qb = self._leg("qb", 270, 60, 249.5, stat="pass_yards")
        wr = self._leg("wr", 70, 25, 64.5, stat="rec_yards")
        rep = parlay.analyse_parlay([qb, wr], offered_price=260, sport="nfl",
                                    relationships={(0, 1): "same_team"},
                                    trials=20000, seed=9)
        self.assertGreater(rep.sim.correlation_multiplier, 1.05)
        self.assertGreater(rep.true_prob, rep.sim.independent_prob)

    def test_anticorrelated_parlay_is_punished(self):
        qb = self._leg("qb", 270, 60, 249.5, stat="pass_yards")
        rb = self._leg("rb", 70, 25, 64.5, stat="rush_yards")
        rep = parlay.analyse_parlay([qb, rb], offered_price=260, sport="nfl",
                                    relationships={(0, 1): "same_team"},
                                    trials=20000, seed=9)
        self.assertLess(rep.sim.correlation_multiplier, 1.0)

    def test_terrible_price_is_a_no_bet(self):
        legs = [self._leg("a", 100, 20, 100), self._leg("b", 50, 10, 50)]
        rep = parlay.analyse_parlay(legs, offered_price=150, trials=8000, seed=3)
        self.assertEqual(rep.verdict, "NO BET")
        self.assertLess(rep.ev_pct, 0)

    def test_long_tickets_are_downgraded(self):
        legs = [self._leg("l%d" % i, 100, 20, 90) for i in range(6)]
        rep = parlay.analyse_parlay(legs, offered_price=6000, trials=8000, seed=3)
        self.assertTrue(any("Effective hold" in r for r in rep.reasons))

    def test_verdict_headline_matches_the_tier(self):
        """A downgraded ticket must not be described as 'marginally +EV'."""
        legs = [self._leg("a", 100, 20, 100), self._leg("b", 50, 10, 50)]
        rep = parlay.analyse_parlay(legs, offered_price=150, trials=8000, seed=3)
        self.assertIn("-EV", rep.reasons[0])

    def test_report_renders(self):
        legs = [self._leg("a", 100, 20, 95, stat="pass_yards"),
                self._leg("b", 50, 10, 45, stat="rec_yards")]
        rep = parlay.analyse_parlay(legs, offered_price=300, trials=6000, seed=5)
        text = rep.render()
        for section in ("LEGS", "CORRELATION", "PRICING", "HIT DISTRIBUTION", "VERDICT"):
            self.assertIn(section, text)

    def test_best_subset_drops_the_dead_weight(self):
        good_a = self._leg("good_a", 100, 20, 80, price=-110)
        good_b = self._leg("good_b", 100, 20, 80, price=-110)
        awful = self._leg("awful", 100, 20, 175, price=-110)
        best, all_reports = parlay.best_subset([good_a, good_b, awful], trials=6000)
        self.assertNotIn(awful, best.legs)
        self.assertEqual(len(all_reports), 4)   # three pairs plus the triple

    def test_record_grade_refuses_to_be_impressed_by_a_small_sample(self):
        r = parlay.record_grade(7, 3)
        self.assertFalse(r["proven_winner"])
        self.assertLess(r["ci_low"], 52.38)

    def test_record_grade_recognises_a_real_edge(self):
        r = parlay.record_grade(1200, 1000)
        self.assertTrue(r["proven_winner"])

    def test_record_grade_with_no_bets(self):
        self.assertEqual(parlay.record_grade(0, 0)["n"], 0)


class TestCents(unittest.TestCase):
    """American odds cannot be subtracted across the century boundary."""

    def test_cents_scale_is_monotone(self):
        prices = [-500, -200, -110, -101, 100, 110, 200, 500]
        scaled = [odds.cents_scale(p) for p in prices]
        self.assertEqual(scaled, sorted(scaled))

    def test_plus_and_minus_100_are_the_same_point(self):
        self.assertAlmostEqual(odds.cents_scale(100), odds.cents_scale(-100), places=9)

    def test_ten_cent_lines(self):
        self.assertAlmostEqual(odds.cents_between(100, -110), 10.0, places=9)
        self.assertAlmostEqual(odds.cents_between(-110, -120), 10.0, places=9)
        self.assertAlmostEqual(odds.cents_between(110, 100), 10.0, places=9)

    def test_edge_in_cents_across_the_boundary(self):
        """-110 against a fair +100 is ten cents of juice, not two hundred."""
        self.assertAlmostEqual(odds.edge_in_cents(0.5, -110), -10.0, places=9)
        self.assertAlmostEqual(odds.edge_in_cents(0.5, 120), 20.0, places=9)


class TestKeyNumbers(unittest.TestCase):

    def test_three_is_the_most_common_nfl_margin(self):
        pmf = keynumbers.margin_pmf("nfl")
        top = max(pmf.items(), key=lambda kv: kv[1])[0]
        self.assertEqual(top, 3)
        self.assertGreater(pmf[3], pmf[7])
        self.assertGreater(pmf[7], pmf[11])

    def test_key_numbers_identified(self):
        self.assertTrue(keynumbers.is_key_number(3))
        self.assertTrue(keynumbers.is_key_number(-7))
        self.assertFalse(keynumbers.is_key_number(11))

    def test_key_number_logic_is_nfl_only(self):
        with self.assertRaises(ValueError):
            keynumbers.margin_pmf("nba")

    def test_half_point_off_three_is_worth_more_than_off_eight(self):
        self.assertGreater(keynumbers.half_point_value(-3),
                           keynumbers.half_point_value(-8))
        self.assertGreater(keynumbers.half_point_value(-7),
                           keynumbers.half_point_value(-11))

    def test_half_point_off_three_is_worth_roughly_25_cents(self):
        """The industry rule of thumb, reproduced from the margin table."""
        rows = {r["margin"]: r for r in keynumbers.key_number_report()}
        self.assertTrue(20 <= rows[3]["half_point_cents"] <= 32)

    def test_buying_at_the_breakeven_price_is_a_wash(self):
        res = keynumbers.buy_points(0.48, 0.057, -110, -130)
        at_be = keynumbers.buy_points(0.48, 0.057, -110, res["breakeven_price"])
        self.assertAlmostEqual(at_be["gain"], 0.0, delta=0.002)

    def test_buying_a_worthless_point_is_rejected(self):
        cheap = keynumbers.buy_points(0.50, 0.021, -110, -130)
        self.assertFalse(cheap["worth_it"])

    def test_buying_is_worth_it_when_the_price_is_right(self):
        res = keynumbers.buy_points(0.48, 0.057, -110, -112)
        self.assertTrue(res["worth_it"])


class TestMiddles(unittest.TestCase):

    def test_middle_requires_a_gap(self):
        self.assertIsNone(market.middle(3.5, -110, 2.5, -110))

    def test_breakeven_middle_prob_at_standard_prices(self):
        res = market.middle(-2.5, -110, 3.5, -110)
        self.assertAlmostEqual(res["breakeven_middle_prob"], 0.0476, delta=0.004)

    def test_nfl_middles_are_priced_off_the_margin_distribution(self):
        res = market.middle(-3.5, -110, -2.5, -110, sport="nfl")
        self.assertEqual(res["priced_from"], "nfl margin distribution")
        plain = market.middle(-3.5, -110, -2.5, -110)
        self.assertEqual(plain["priced_from"], "normal approximation")

    def test_a_middle_spanning_three_beats_one_spanning_two(self):
        """The whole point of key numbers, and what the normal approximation
        cannot see."""
        spans_three = market.middle(-3.5, -110, -2.5, -110, sport="nfl")
        spans_two = market.middle(-2.5, -110, -1.5, -110, sport="nfl")
        self.assertGreater(spans_three["middle_prob"], 2 * spans_two["middle_prob"])
        self.assertGreater(spans_three["ev_pct"], spans_two["ev_pct"])
        self.assertEqual(spans_three["key_numbers_spanned"], [3])
        self.assertEqual(spans_two["key_numbers_spanned"], [])

    def test_wide_middle_is_worth_it(self):
        self.assertTrue(market.middle(-2.5, -110, 3.5, -110, sport="nfl")["worth_it"])

    def test_narrow_middle_is_not_free_money(self):
        res = market.middle(-2.5, -110, -1.5, -110, sport="nfl")
        self.assertFalse(res["worth_it"])
        self.assertLess(res["ev_pct"], 0)

    def test_probabilities_account_for_everything(self):
        for sport in (None, "nfl"):
            res = market.middle(-2.5, -110, 3.5, -110, sport=sport)
            total = res["middle_prob"] + res["prob_above"] + res["prob_below"]
            self.assertAlmostEqual(total, 1.0, places=6)


class TestPersona(unittest.TestCase):

    def test_brief_renders_everything(self):
        text = persona.brief()
        for name in ("Steve Fezzik", "Voulgaris", "Billy Walters", "Big Bet Bob",
                     "Mikki Mase"):
            self.assertIn(name, text)
        for section in ("HOUSE RULES", "THE FOUR PILLARS", "BANKROLL", "TEMPERAMENT"):
            self.assertIn(section, text)

    def test_every_doctrine_states_what_not_to_copy(self):
        for d in persona.DOCTRINES:
            self.assertTrue(d.jordan_takes)
            self.assertTrue(d.jordan_leaves, "%s has no cautions" % d.name)

    def test_disclaimer_carries_a_helpline(self):
        self.assertIn("1-800-522-4700", persona.DISCLAIMER)

    def test_default_answer_is_pass(self):
        self.assertIn("PASS", persona.HOUSE_RULES[0])

    def test_bankroll_caps_are_conservative(self):
        self.assertLessEqual(persona.BANKROLL["kelly_multiplier"], 0.25)
        self.assertLessEqual(persona.BANKROLL["single_bet_cap"], 0.02)


class TestCli(unittest.TestCase):

    def _run(self, argv):
        import io
        from contextlib import redirect_stdout
        from jordan import cli
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def test_brief(self):
        code, out = self._run(["brief"])
        self.assertEqual(code, 0)
        self.assertIn("JORDAN", out)

    def test_devig(self):
        code, out = self._run(["devig", "-110", "-110"])
        self.assertEqual(code, 0)
        self.assertIn("50.00%", out)

    def test_ev_no_bet_message(self):
        code, out = self._run(["ev", "--prob", "0.45", "--price", "-110"])
        self.assertEqual(code, 0)
        self.assertIn("No bet", out)

    def test_parlay_hold(self):
        code, out = self._run(["parlay", "-110", "-110", "-110"])
        self.assertEqual(code, 0)
        self.assertIn("Effective hold", out)

    def test_stacks(self):
        code, out = self._run(["stacks", "nba"])
        self.assertEqual(code, 0)
        self.assertIn("CORRELATION PRIORS -- NBA", out)

    def test_stacks_unknown_sport_exits_nonzero(self):
        code, out = self._run(["stacks", "curling"])
        self.assertEqual(code, 1)

    def test_record(self):
        code, out = self._run(["record", "7", "3"])
        self.assertEqual(code, 0)
        self.assertIn("95% interval", out)

    def test_arb_rejects_a_normal_market(self):
        code, out = self._run(["arb", "-110", "-110"])
        self.assertEqual(code, 1)

    def test_sgp_end_to_end_on_the_shipped_example(self):
        here = os.path.dirname(os.path.abspath(__file__))
        ticket = os.path.join(here, os.pardir, "examples", "ticket_nfl_stack.json")
        code, out = self._run(["sgp", ticket, "--trials", "4000", "--seed", "1"])
        self.assertEqual(code, 0)
        self.assertIn("VERDICT", out)
        self.assertIn("1-800-522-4700", out)

    def test_market_end_to_end_on_the_shipped_example(self):
        here = os.path.dirname(os.path.abspath(__file__))
        snaps = os.path.join(here, os.pardir, "examples", "market_nfl_side.json")
        code, out = self._run(["market", snaps])
        self.assertEqual(code, 0)
        self.assertIn("SIGNALS", out)

    def test_no_command_prints_help(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("usage", out.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
