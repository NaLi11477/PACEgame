"""Tests for pacegame.

Written against the properties the package claims rather than against its
current numbers, so a solver that stops working fails a test here rather than
quietly changing a figure.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest

import sympy as sp

import pacegame as pg
from pacegame.analyze import (critical_value, derivative, equilibrium,
                              sign_map, sweep, threshold, verify)
import pacegame.core
from pacegame.core import Logit, Logistic, Proportional, TwoPhase
from pacegame.cli import main as cli_main
from pacegame.solve import INTERIOR, LOWER, UNBOUNDED, UPPER, check_point, solve

PT = {"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3}
REP = dict(PT, kappa_d=0.05)


def published():
    return pg.models.preannounce_entry()


def repaired():
    return pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                       signal_cost=True)


def subs(game, point):
    names = {}
    for obj in (game.lifecycle, game.share_rule):
        for p in getattr(obj, "params", ()):
            names[str(p)] = p
    for extra in (game.signal_cost, game.timing_cost):
        for s in sp.sympify(extra).free_symbols:
            names[str(s)] = s
    return {names[k]: sp.Float(v) for k, v in point.items() if k in names}


def strat(name):
    return next(s for s in pg.STANDARD_STRATEGIES if s.name == name)


class TestPrimitives(unittest.TestCase):
    def test_proportional_shares_sum_to_one(self):
        phi, a, b = sp.symbols("phi a b", positive=True)
        out = Proportional(phi=phi).shares({"x": a, "y": b})
        self.assertEqual(sp.simplify(sum(out.values())), 1)

    def test_logit_shares_sum_to_one(self):
        beta, a, b = sp.symbols("beta a b", positive=True)
        out = Logit(beta=beta).shares({"x": a, "y": b})
        self.assertEqual(sp.simplify(sum(out.values())), 1)

    def test_a_share_rule_that_does_not_sum_to_one_is_refused(self):
        class Broken(Proportional):
            def shares(self, stocks):
                return self._check({j: sp.Rational(1, 3) for j in stocks})
        with self.assertRaises(ValueError):
            Broken(phi=sp.Symbol("phi")).shares({"x": 0, "y": 0})

    def test_pioneer_keeps_its_stock_and_follower_may_not(self):
        t = sp.Symbol("t")
        s, ge = sp.Rational(1, 10), sp.Rational(3, 10)
        keep_val = TwoPhase(sigma=s, growth_end=ge, keep_stock=True).accumulate(
            t, entry=sp.Rational(1, 10), rivals_entry=sp.Integer(0),
            share=sp.Rational(1, 2), stock=sp.Integer(1), is_pioneer=False)
        drop_val = TwoPhase(sigma=s, growth_end=ge, keep_stock=False).accumulate(
            t, entry=sp.Rational(1, 10), rivals_entry=sp.Integer(0),
            share=sp.Rational(1, 2), stock=sp.Integer(1), is_pioneer=False)
        self.assertGreater(float(keep_val), float(drop_val))

    def test_a_second_lifecycle_satisfies_the_same_interface(self):
        t = sp.Symbol("t")
        life = Logistic(ceiling=sp.Integer(1), rate=sp.Integer(8),
                        midpoint=sp.Rational(1, 2))
        val = life.accumulate(t, entry=sp.Rational(1, 5),
                              rivals_entry=sp.Integer(0),
                              share=sp.Rational(1, 2), stock=sp.Integer(0),
                              is_pioneer=False)
        self.assertGreater(float(sp.N(val)), 0)


class TestPayoffs(unittest.TestCase):
    def test_every_strategy_has_a_payoff_for_both_players(self):
        g = published()
        for s in pg.STANDARD_STRATEGIES:
            p = g.payoffs(s)
            self.assertEqual(set(p), {"x", "y"})

    def test_symmetric_strategies_mirror_each_other(self):
        """DF seen by x is DL seen by y: the same game from the other side."""
        g = published()
        self.assertEqual(sp.simplify(g.payoffs(strat("DF"))["x"]
                                     - g.payoffs(strat("DL"))["y"]), 0)

    def test_payoff_at_simultaneous_entry_is_the_symmetric_split(self):
        g = published()
        p = g.payoffs(strat("DF"))["x"].subs({g.entry: 0})
        sigma, ge = g.lifecycle.sigma, g.lifecycle.growth_end
        self.assertEqual(sp.simplify(p - sigma * ge * (2 - ge) / 16), 0)


class TestPublishedSpecification(unittest.TestCase):
    """What the model does as published, which is the reason this package exists."""

    def test_the_follower_never_waits(self):
        g = published()
        for name in ("DF", "DL", "RF", "RL"):
            sol = solve(g, strat(name), subs(g, PT))
            self.assertEqual(sol.kind[g.entry], LOWER,
                             f"{name}: entry should sit on its lower bound")

    def test_a_costless_signal_is_unresolved_at_a_finite_cap(self):
        g = published()
        for name in ("RF", "RL"):
            sol = solve(g, strat(name), subs(g, PT))
            self.assertEqual(sol.kind[g.signal], "search limit")
            self.assertTrue(sol.unresolved)
            self.assertFalse(sol.unbounded)

    def test_the_reported_stationary_point_is_outside_the_feasible_set(self):
        """The published closed form for the follower's entry time, checked."""
        g = published()
        st = strat("DL")
        roots = pg.solve_symbolic(g, st)
        self.assertIsNotNone(roots)
        rep = check_point(g.payoffs(st)["x"], roots, g.bounds(st), subs(g, PT),
                          upper_bound=g.demand_ceiling(st))
        self.assertFalse(rep.ok)
        reasons = " ".join(v.detail for v in rep.violations())
        self.assertIn("exceeds its upper bound", reasons)
        self.assertIn("MINIMUM", reasons)


class TestRepairedSpecification(unittest.TestCase):
    def test_the_late_entrant_now_waits(self):
        g = repaired()
        sol = solve(g, strat("RL"), subs(g, REP))
        self.assertIn(sol.kind[g.entry], (INTERIOR, UPPER))
        self.assertGreater(float(sol.point[g.entry]), 0.0)

    def test_a_costly_signal_has_an_interior_level(self):
        g = repaired()
        sol = solve(g, strat("RL"), subs(g, REP))
        self.assertEqual(sol.kind[g.signal], INTERIOR)
        self.assertFalse(sol.unbounded)

    def test_signalling_and_following_is_the_equilibrium(self):
        g = repaired()
        self.assertEqual(equilibrium(g, REP).best, "RL")

    def test_every_optimum_is_feasible(self):
        g = repaired()
        for s in pg.STANDARD_STRATEGIES:
            sol = solve(g, s, subs(g, REP))
            self.assertTrue(sol.feasibility.ok, f"{s}: {sol.feasibility}")


class TestFeasibility(unittest.TestCase):
    def test_a_payoff_above_the_demand_ceiling_is_flagged(self):
        g = published()
        st = strat("DL")
        rep = check_point(g.payoffs(st)["x"] * 1000, {g.entry: sp.Float(0.0)},
                          g.bounds(st), subs(g, PT),
                          upper_bound=g.demand_ceiling(st),
                          kinds={g.entry: "lower corner"})
        self.assertTrue(any("ceiling" in v.detail for v in rep.violations()))

    def test_a_clean_point_passes_every_check(self):
        g = repaired()
        sol = solve(g, strat("RL"), subs(g, REP))
        self.assertTrue(sol.feasibility.ok)
        self.assertGreater(len(sol.feasibility.findings), 3)


class TestVerification(unittest.TestCase):
    def test_a_true_claim_holds_and_a_false_one_reports_where(self):
        # A resolved model supplies a genuine verdict and counterexample.
        # Unresolved-parent skips are covered separately in test_audit_021.
        g = repaired()
        rep = verify.check(g, [verify.Dominates("RL", "DF"),
                               verify.Interior("varsigma", strategy="RL")],
                           over={"sigma": (0.05, 0.4), "phi": (0.3, 0.9)}, n=2,
                           fixed={"hatvarsigma": 0.3, "kappa_d": 0.05})
        by = {r.claim: r for r in rep.results}
        interior = by["varsigma* is interior under RL"]
        self.assertTrue(by["pi_RL > pi_DF"].holds)
        self.assertFalse(interior.holds)
        self.assertTrue(interior.counterexamples)

    def test_the_report_renders_as_markdown(self):
        g = repaired()
        rep = verify.check(g, [verify.Bounded("RL")],
                           over={"sigma": (0.05, 0.2)}, n=2,
                           fixed={"phi": 0.85, "hatvarsigma": 0.3, "kappa_d": 0.05})
        md = rep.to_markdown()
        self.assertIn("| claim |", md)
        self.assertIn("RL", md)

    def test_a_claim_that_raises_is_recorded_not_propagated(self):
        class Boom(verify.Claim):
            label = "boom"

            def evaluate(self, game, point, cache):
                raise RuntimeError("kaboom")
        rep = verify.check(published(), [Boom()], over={"sigma": (0.1, 0.2)}, n=2,
                           fixed={"phi": 0.85, "hatvarsigma": 0.3})
        self.assertEqual(rep.results[0].errors, 2)
        self.assertFalse(rep.ok)


class TestEquilibrium(unittest.TestCase):
    def test_ties_are_reported_as_ties(self):
        out = equilibrium(published(), PT)
        self.assertGreater(len(out.ties()), 1)

    def test_sweep_returns_one_outcome_per_value(self):
        outs = sweep(repaired(), "sigma", [0.1, 0.2], REP)
        self.assertEqual(len(outs), 2)

    def test_threshold_returns_none_when_no_crossing_exists(self):
        self.assertIsNone(threshold(repaired(), "sigma", 0.05, 0.4, REP,
                                    winner="RL", loser="DF"))

    def test_threshold_finds_a_crossing_when_one_exists(self):
        """Once deploying early is expensive enough, following beats leading."""
        g = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                        signal_cost=True, timing_cost=True)
        fixed = dict(REP, kappa_t=0.0)
        cut = threshold(g, "kappa_t", 0.0, 0.08, fixed, winner="DL", loser="DF")
        self.assertIsNotNone(cut)
        # Half the crossing lies in the exact lower-entry tie plateau for this
        # model. The old strict assertion passed only through float rounding.
        # Preserve a strict crossing test using the nonzero branch below it.
        plateau_point = dict(fixed, kappa_t=cut * 0.5)
        plateau = equilibrium(g, plateau_point)
        from pacegame.core.numeric import exact_numeric
        retained = []
        for label in ("DF", "DL"):
            solution = plateau.solutions[label]
            self.assertEqual(sp.Rational(solution.point[g.entry]), 0)
            at = g.numeric(plateau_point)
            at.update(solution.point)
            retained.append(exact_numeric(g.payoffs(solution.strategy)[g.focal], at))
        self.assertEqual(retained[0], retained[1])
        below = equilibrium(g, dict(fixed, kappa_t=cut * 0.9))
        above = equilibrium(g, dict(fixed, kappa_t=cut * 1.5))
        self.assertGreater(below.payoffs["DF"], below.payoffs["DL"])
        self.assertGreater(above.payoffs["DL"], above.payoffs["DF"])

    def test_an_endpoint_tie_is_not_reported_as_a_crossing(self):
        g = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                        signal_cost=True, timing_cost=True)
        fixed = dict(REP, kappa_t=0.0)
        self.assertEqual(equilibrium(g, fixed).payoffs["DF"],
                         equilibrium(g, fixed).payoffs["DL"])
        cut = threshold(g, "kappa_t", 0.0, 0.08, fixed, winner="DL", loser="DF")
        self.assertGreater(cut, 0.0)


class TestOtherModels(unittest.TestCase):
    """The framework must not be a single-model abstraction."""

    def test_a_model_without_a_signal_admits_only_silent_strategies(self):
        g = pg.models.logistic_entry()
        self.assertEqual({s.name for s in g.strategies}, {"DF", "DL"})
        out = equilibrium(g, pg.models.LOGISTIC_POINT)
        self.assertEqual(set(out.payoffs), {"DF", "DL"})

    def test_a_different_lifecycle_and_share_rule_give_an_interior_optimum(self):
        g = pg.models.logistic_entry()
        sol = solve(g, strat("DF"), subs(g, pg.models.LOGISTIC_POINT))
        self.assertEqual(sol.kind[g.entry], INTERIOR)
        self.assertTrue(sol.feasibility.ok, str(sol.feasibility))

    def test_asymmetric_quality_changes_payoffs_but_not_the_equilibrium(self):
        """The motivating study assumes equal quality 'without loss of
        generality'; that is a claim, and this is the test of it."""
        point = {k: v for k, v in pg.models.ASYMMETRIC_POINT.items() if k != "omega"}
        best, levels = set(), []
        for omega in (0.6, 1.0, 1.6):
            g = pg.models.asymmetric_quality(omega=omega)
            out = equilibrium(g, point)
            best.add(out.best)
            levels.append(out.payoffs["DF"])
        self.assertEqual(best, {"RL"}, "the equilibrium strategy should not move")
        self.assertNotEqual(len(set(round(v, 9) for v in levels)), 1,
                            "but the payoff levels should")


class TestReadinessLag(unittest.TestCase):
    """Without a lag a rival enters at once and no first-mover advantage exists."""

    def _game(self):
        return pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                           signal_cost=True, entry_floor=True)

    def test_a_zero_lag_leaves_leading_and_following_identical(self):
        out = equilibrium(self._game(), dict(REP, **{"lambda": 0.0}))
        self.assertAlmostEqual(out.payoffs["DF"], out.payoffs["DL"], places=9)

    def test_a_positive_lag_creates_a_first_mover_advantage(self):
        out = equilibrium(self._game(), dict(REP, **{"lambda": 0.1}))
        self.assertGreater(out.payoffs["DF"], out.payoffs["DL"])

    def test_the_follower_cannot_enter_before_the_lag(self):
        g = self._game()
        sol = solve(g, strat("DL"), g.numeric(dict(REP, **{"lambda": 0.1})))
        self.assertGreaterEqual(float(sol.point[g.entry]), 0.1 - 1e-9)


class TestParameters(unittest.TestCase):
    def test_every_primitive_contributes_to_the_parameter_table(self):
        g = pg.models.preannounce_entry(signal_cost=True, timing_cost=True,
                                        entry_floor=True)
        self.assertEqual(set(g.parameters()),
                         {"sigma", "phi", "hatvarsigma", "kappa_d", "kappa_t",
                          "lambda"})

    def test_a_missing_parameter_is_named_rather_than_failing_later(self):
        g = pg.models.preannounce_entry(entry_floor=True)
        with self.assertRaises(KeyError) as ctx:
            g.numeric({"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3})
        self.assertIn("lambda", str(ctx.exception))

    def test_unknown_names_are_ignored_rather_than_refused(self):
        g = pg.models.preannounce_entry()
        out = g.numeric({"sigma": 0.1, "phi": 0.85, "hatvarsigma": 0.3,
                         "not_a_parameter": 7})
        self.assertEqual(len(out), 3)


class TestDecisionStatics(unittest.TestCase):
    def test_a_decision_variable_can_be_differentiated_like_a_payoff(self):
        g = repaired()
        r = derivative(g, "RL", "hatvarsigma", REP, quantity="delta")
        self.assertIn("delta*", r.target)
        self.assertGreater(r.slope, 0)

    def test_a_payoff_gap_can_be_differentiated(self):
        g = repaired()
        r = derivative(g, ("RL", "RF"), "hatvarsigma", REP)
        self.assertIn("RL-RF", r.target)

    def test_a_quantity_that_is_not_a_decision_is_refused_by_name(self):
        g = repaired()
        with self.assertRaises(KeyError):
            derivative(g, "DF", "sigma", REP, quantity="delta")


class TestStatics(unittest.TestCase):
    def test_a_uniform_sign_is_reported_as_uniform(self):
        g = repaired()
        m = sign_map(g, "DF", "sigma", over={"phi": (0.3, 0.95)}, fixed=REP, n=3)
        self.assertTrue(m.uniform)
        self.assertEqual(m.signs - {"0"}, {"+"})

    def test_a_missing_parameter_is_refused_by_name(self):
        g = repaired()
        with self.assertRaises(KeyError):
            sign_map(g, "DF", "nosuch", over={"phi": (0.3, 0.9)}, fixed=REP, n=2)

    def test_no_critical_value_is_reported_when_the_sign_never_turns(self):
        g = repaired()
        self.assertIsNone(critical_value(g, "DF", "sigma", "phi",
                                         0.1, 0.95, REP))


class TestCommandLine(unittest.TestCase):
    def _run(self, argv):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli_main(argv)
        return code, buf.getvalue()

    def test_models_lists_every_registered_model(self):
        code, out = self._run(["models"])
        self.assertEqual(code, 0)
        for name in pg.models.REGISTRY:
            self.assertIn(name, out)

    def test_solve_reports_the_unresolved_signal_of_the_baseline_model(self):
        code, out = self._run(["solve", "preannounce_entry"])
        self.assertEqual(code, 1)
        self.assertIn("search limit", out)

    def test_repair_switches_on_a_positive_signal_cost(self):
        code, out = self._run(["equilibrium", "preannounce_entry", "--repair"])
        self.assertEqual(code, 0)
        self.assertIn("kappa_d=0.05", out)
        self.assertNotIn("unbounded", out)

    def test_an_unknown_swept_parameter_is_refused_by_name(self):
        """Sweeping a name the model lacks would print a table where nothing
        changes; it is refused instead."""
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = self._run(["sweep", "preannounce_entry", "--wrt", "nope",
                                 "--from", "0.1", "--to", "0.3", "--steps", "2"])
        self.assertEqual(code, 2)
        self.assertIn("not a parameter", err.getvalue())

    def test_a_degenerate_step_count_is_refused(self):
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = self._run(["sweep", "preannounce_entry", "--wrt", "sigma",
                                 "--from", "0.1", "--to", "0.3", "--steps", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--steps", err.getvalue())

    def test_a_malformed_override_is_refused_not_a_traceback(self):
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, _ = self._run(["solve", "preannounce_entry", "--set", "oops"])
        self.assertEqual(code, 2)
        self.assertIn("name=value", err.getvalue())

    def test_examples_extraction_writes_the_script(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            code, out = self._run(["examples", "--extract", tmp])
            self.assertEqual(code, 0)
            self.assertTrue(os.path.isfile(
                os.path.join(tmp, "examples", "audit_preannouncement.py")))


class TestPlotting(unittest.TestCase):
    def test_importing_the_package_does_not_pull_in_matplotlib(self):
        """A reviewer checking the solver should not need a plotting stack."""
        import subprocess
        code = ("import sys; import pacegame; "
                "sys.exit(1 if 'matplotlib' in sys.modules else 0)")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(
            os.path.abspath(pg.__file__)))
        r = subprocess.run([sys.executable, "-c", code], env=env)
        self.assertEqual(r.returncode, 0)

    def test_the_plot_helpers_explain_themselves_without_matplotlib(self):
        from unittest import mock
        from pacegame import plot
        with mock.patch.dict(sys.modules, {"matplotlib": None}):
            with self.assertRaises(ImportError) as ctx:
                plot._plt()
        self.assertIn("matplotlib", str(ctx.exception))

    def test_a_sweep_renders_when_matplotlib_is_present(self):
        import tempfile
        from pacegame import plot
        if not plot.available():
            self.skipTest("matplotlib not installed")
        g = repaired()
        vals = [0.1, 0.2, 0.3]
        outs = sweep(g, "hatvarsigma", vals, REP)
        with tempfile.TemporaryDirectory() as tmp:
            p = plot.payoff_sweep(vals, outs, "hatvarsigma",
                                  os.path.join(tmp, "f.png"))
            self.assertTrue(os.path.getsize(p) > 0)


class TestShippedFiles(unittest.TestCase):
    """The examples live in two places so that `examples --extract` can work
    from an installed wheel while a source checkout can run them in place.
    They must not drift."""

    def test_every_shipped_example_extracts_byte_for_byte(self):
        """`examples --extract` must write exactly what the package carries,
        and a source checkout's root copy must match both. The extracted copy
        exists everywhere, so this runs from a wheel as well as a checkout."""
        import tempfile
        inside = os.path.join(os.path.dirname(os.path.abspath(pg.__file__)),
                              "examples")
        names = sorted(f for f in os.listdir(inside) if f.endswith(".py"))
        self.assertTrue(names, "no examples are shipped")
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cli_main(["examples", "--extract", tmp])
            for name in names:
                with open(os.path.join(inside, name), encoding="utf-8") as a, \
                     open(os.path.join(tmp, "examples", name), encoding="utf-8") as b:
                    self.assertEqual(a.read(), b.read(), name)
        root = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(pg.__file__)))), "examples")
        if os.path.isdir(root):
            for name in names:
                with open(os.path.join(inside, name), encoding="utf-8") as a, \
                     open(os.path.join(root, name), encoding="utf-8") as b:
                    self.assertEqual(a.read(), b.read(), name)

    def test_the_tests_are_importable_from_an_installed_package(self):
        """A reviewer who pip-installs should be able to run the suite."""
        import importlib
        mod = importlib.import_module("pacegame.tests.test_pacegame")
        self.assertTrue(hasattr(mod, "TestPackage"))


class TestAuditRegressions(unittest.TestCase):
    """The four defects the v0.1.1 artifact audit found, pinned so they stay fixed."""

    def test_every_shipped_example_parses_on_the_declared_minimum_python(self):
        """`requires-python = ">=3.10"` is a promise about every shipped file.

        A PEP 701 f-string (a quote reused inside the braces) compiles here but
        is a SyntaxError on 3.10 and 3.11, and no test that only reads the file
        as text will notice.
        """
        import re
        inside = os.path.join(os.path.dirname(os.path.abspath(pg.__file__)))
        offenders = []
        for root, _, files in os.walk(inside):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8") as fh:
                    for n, line in enumerate(fh, 1):
                        for m in re.finditer(r"f([\"'])", line):
                            q, depth = m.group(1), 0
                            for ch in line[m.end():]:
                                if ch == "{":
                                    depth += 1
                                elif ch == "}":
                                    depth -= 1
                                elif ch == q:
                                    if depth > 0:
                                        offenders.append(f"{path}:{n}")
                                    break
        self.assertEqual(offenders, [], "3.12-only f-string syntax")

    def test_a_cost_may_make_the_net_payoff_negative_without_a_violation(self):
        """The sign test belongs to the demand integral, not to the net payoff.

        A timing or signalling cost can legitimately take a player below zero;
        flagging that as impossible is a false alarm, and `logistic_entry` ships
        with a timing cost switched on.
        """
        g = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                        signal_cost=True, timing_cost=True)
        pt = dict(REP, kappa_t=0.5)
        sol = solve(g, strat("DL"), g.numeric(pt))
        self.assertLess(sol.payoffs["x"], 0.0)
        self.assertTrue(sol.feasibility.ok, str(sol.feasibility))

    def test_a_ceiling_that_moves_with_the_payoff_is_declared_uninformative(self):
        """Once the signal accrues to the stock, the ceiling contains the
        decision variable and the magnitude check can never bite. Say so."""
        g = repaired()
        st = strat("RL")
        self.assertTrue(g.ceiling_is_endogenous(st))
        sol = solve(g, st, subs(g, REP))
        notes = " ".join(f.detail for f in sol.feasibility.findings)
        self.assertIn("cannot fail", notes)
        self.assertFalse(pg.models.preannounce_entry().ceiling_is_endogenous(st))

    def test_a_lifecycle_without_a_capacity_says_the_check_did_not_run(self):
        g = pg.models.logistic_entry()
        self.assertIsNotNone(g.demand_ceiling(strat("DF")))
        sol = solve(g, strat("DF"), g.numeric(pg.models.LOGISTIC_POINT))
        self.assertIn("payoff magnitude", [f.check for f in sol.feasibility.findings])

    def test_an_inapplicable_claim_is_not_counted_as_a_failure(self):
        """A claim skipped at every point did not apply; turning that into a
        non-zero exit code is a false alarm in a CI script."""
        class Skips(verify.Claim):
            label = "never applies"

            def evaluate(self, game, point, cache):
                return None, "not applicable"
        rep = verify.check(repaired(), [Skips()], over={"sigma": (0.1, 0.2)},
                           n=2, fixed={"phi": 0.85, "hatvarsigma": 0.3,
                                       "kappa_d": 0.05})
        self.assertTrue(rep.ok)
        self.assertEqual(rep.inapplicable, ["never applies"])

    def test_the_before_and_after_claim_lists_are_identical(self):
        """The worked example compares the published and repaired models on the
        same six claims. Dropping one between the runs would hide the claim the
        repairs do not fix, which is the error the package exists to catch."""
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(pg.__file__)),
                            "examples", "audit_preannouncement.py")
        spec = importlib.util.spec_from_file_location("_audit_ex", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        labels = [c.label for c in mod.claims()]
        self.assertEqual(len(labels), 6)
        self.assertIn("varsigma* is interior under RL", labels)
        self.assertIn("pi_DF > pi_DL", labels)

    def test_the_solver_records_the_method_it_was_asked_for(self):
        g = published()
        self.assertEqual(solve(g, strat("DL"), subs(g, PT),
                               method="symbolic").method, "symbolic")


class TestV012Regressions(unittest.TestCase):
    """What the response to the v0.1.1 audit changed, pinned."""

    def test_the_share_rule_actually_bites_in_the_logistic_model(self):
        """`logistic_entry` exists to show the primitives are replaceable. It
        was not: the stock came off a TwoPhase-only attribute, so both players
        held zero, the logit returned one half whatever beta was, and the share
        rule was inert."""
        g = pg.models.logistic_entry()
        sol = solve(g, strat("DF"), g.numeric(pg.models.LOGISTIC_POINT))
        note = next(f for f in sol.feasibility.findings
                    if f.check == "competition")
        self.assertEqual(note.status, "ok", note.detail)
        a = equilibrium(g, dict(pg.models.LOGISTIC_POINT, beta=0.5))
        b = equilibrium(g, dict(pg.models.LOGISTIC_POINT, beta=3.0))
        self.assertNotAlmostEqual(a.payoffs["DF"], b.payoffs["DF"], places=9)

    def test_an_inactive_share_rule_is_reported(self):
        """At the repaired model's own optimum the follower waits out the whole
        growth phase, captures nothing, and phi leaves the payoff."""
        g = repaired()
        sol = solve(g, strat("RL"), subs(g, REP))
        note = next(f for f in sol.feasibility.findings
                    if f.check == "competition")
        self.assertEqual(note.status, "warning")
        self.assertIn("share rule is inactive", note.detail)

    def test_a_divergent_strategy_is_not_crowned_and_not_ruled_on(self):
        out = equilibrium(published(), PT)
        self.assertEqual(set(out.excluded), {"RF", "RL"})
        self.assertNotIn(out.best, out.excluded)
        rep = verify.check(published(), [verify.Dominates("RL", "DF")],
                           over={"sigma": (0.05, 0.4)}, n=2,
                           fixed={"phi": 0.85, "hatvarsigma": 0.3})
        self.assertEqual(rep.results[0].passed + rep.results[0].failed, 0)
        self.assertTrue(rep.ok)

    def test_the_ranking_reports_that_it_is_not_a_nash_equilibrium(self):
        """The caveat is unconditional; the number is not.

        0.1.2 asserted a positive gap on the shipped repaired model. 0.1.4
        withholds the gap there, because only the focal platform can announce
        and the rival could not earn the focal payoff from that position, so
        the difference would be between unlike quantities. The claim being
        tested -- that the ranking is announced as a best response rather than
        an equilibrium -- is unchanged; the gap is asserted where the two
        players really are interchangeable.
        """
        out = equilibrium(repaired(), REP)
        self.assertEqual(out.best, "RL")
        self.assertIsNone(out.role_conflict())
        self.assertIn("not Nash", str(out))
        both = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                           signal_cost=True, rival_signals=True)
        self.assertIsNone(equilibrium(both, REP).role_conflict())

    def test_a_credibility_ceiling_bounds_the_signal_without_a_cost(self):
        """A quadratic cost regularises the divergence; it does not remove it.
        delta* is exactly inverse in kappa_d without a ceiling and pinned with
        one."""
        loose = repaired()
        tight = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                            signal_cost=True, signal_ceiling=True)
        ds, ps = [], []
        for kd in (0.05, 0.01):
            a = solve(loose, strat("RL"), subs(loose, dict(REP, kappa_d=kd)))
            b = solve(tight, strat("RL"), subs(tight, dict(REP, kappa_d=kd)))
            ds.append(float(a.point[loose.signal]))
            ps.append(float(b.point[tight.signal]))
        self.assertAlmostEqual(ds[1] / ds[0], 5.0, places=4)   # inverse in kappa_d
        self.assertAlmostEqual(ps[0], ps[1], places=9)         # pinned at the ceiling

    def test_the_rival_can_be_given_the_announcement_channel(self):
        g = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                        signal_cost=True, rival_signals=True)
        st = strat("RL")
        self.assertNotEqual(sp.simplify(g.stocks(st)[g.rival]
                                        - repaired().stocks(st)[g.rival]), 0)

    def test_a_large_but_genuine_optimum_is_not_called_unbounded(self):
        """The old test was `value >= 0.5 * cap`, which would call a real
        optimum at 6e5 divergent. Divergence is now evidenced by the probe."""
        g = repaired()
        sol = solve(g, strat("RL"), subs(g, dict(REP, kappa_d=1e-5)))
        self.assertGreater(float(sol.point[g.signal]), 5e3)
        self.assertEqual(sol.kind[g.signal], INTERIOR)
        self.assertFalse(sol.unbounded)

    def test_sign_claims_are_covered_at_last(self):
        """verify.Sign was the one advertised claim type with no test."""
        g = repaired()
        rep = verify.check(g, [verify.Sign("d pi_x / d sigma", ">", strategy="DF"),
                               verify.Sign("d pi_x / d sigma", "<", strategy="DF")],
                           over={"sigma": (0.05, 0.4)}, n=3,
                           fixed={"phi": 0.85, "hatvarsigma": 0.3,
                                  "kappa_d": 0.05})
        self.assertTrue(rep.results[0].holds)
        self.assertFalse(rep.results[1].holds)


class TestV013Regressions(unittest.TestCase):
    """What the response to the v0.1.2 audit changed, pinned."""

    def test_the_demand_path_is_integrated_once_per_solve(self):
        """solve() asked for net payoffs and then for gross ones, and the net
        call computes the gross ones internally, so the integral ran three
        times. Guard the count rather than the clock."""
        g = repaired()
        calls = []
        real = type(g)._gross_payoffs
        type(g)._gross_payoffs = lambda self, s: (calls.append(1), real(self, s))[1]
        try:
            solve(g, strat("RL"), subs(g, REP))
        finally:
            type(g)._gross_payoffs = real
        self.assertEqual(len(calls), 1, f"integrated {len(calls)} times")

    def test_the_competition_check_sees_every_share_rule_symbol(self):
        g = pg.models.asymmetric_quality(omega=None)
        names = {str(s) for s in g.share_rule.all_params()}
        self.assertEqual(names, {"phi", "omega"})

    def test_an_inactive_share_rule_can_be_asserted_over_a_grid(self):
        """Feasible reports violations only, so the competition warning never
        reached the verification layer."""
        rep = verify.check(repaired(), [verify.Competitive("RL")],
                           over={"sigma": (0.05, 0.4)}, n=2,
                           fixed={"phi": 0.85, "hatvarsigma": 0.3,
                                  "kappa_d": 0.05})
        self.assertFalse(rep.results[0].holds)
        self.assertTrue(rep.results[0].counterexamples)

    def test_role_conflict_is_withheld_when_the_players_are_not_alike(self):
        point = {k: v for k, v in pg.models.ASYMMETRIC_POINT.items()
                 if k != "omega"}
        same = pg.models.asymmetric_quality(omega=1.0)
        diff = pg.models.asymmetric_quality(omega=2.0)
        # the share-rule dimension, read on a strategy with no signal so that
        # the channel does not decide the answer for it
        self.assertTrue(same.players_alike(strat("DF")))
        self.assertFalse(diff.players_alike(strat("DF")))
        # and it still governs the outcome-level answer
        self.assertIsNone(equilibrium(diff, point).role_conflict())

    def test_a_divergent_strategy_is_not_reported_as_tied(self):
        out = equilibrium(published(), PT)
        self.assertEqual(set(out.ties()) & set(out.unbounded), set())

    def test_the_logistic_stock_and_demand_level_share_an_origin(self):
        life = Logistic(ceiling=sp.Integer(1), rate=sp.Integer(8),
                        midpoint=sp.Rational(1, 2))
        t = sp.Symbol("t", nonnegative=True)
        seg = life.segments(t, entry=sp.Integer(0), rivals_entry=sp.Rational(1, 5),
                            share=sp.Rational(1, 2), stock=sp.Integer(0),
                            is_pioneer=True)[0]
        at_zero = sp.simplify(seg.expr.subs(t, 0))
        self.assertEqual(at_zero, 0)
        self.assertEqual(sp.simplify(life.stock_at(sp.Integer(0))), 0)

    def test_a_lifecycle_from_the_previous_release_still_works(self):
        """stock_at arrived in 0.1.2 with no default, which broke every
        user-written lifecycle in a patch release."""
        import warnings

        class Legacy(pg.core.Lifecycle):
            sigma = sp.Rational(1, 10)

            def segments(self, t, entry, rivals_entry, share, stock, is_pioneer):
                return []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = Legacy().stock_at(sp.Rational(1, 2))
        self.assertEqual(sp.simplify(value - sp.Rational(1, 20)), 0)
        self.assertTrue(caught)


class TestV014Regressions(unittest.TestCase):
    """Three of these were introduced by the v0.1.3 fixes."""

    def test_a_subclass_that_overrides_payoffs_is_honoured(self):
        """0.1.3 removed a triple integration by assembling the net payoff in
        the solver, which made it ignore the override silently."""
        base = repaired()

        class Taxed(pg.Game):
            def payoffs(self, strategy):
                return {j: v - sp.Rational(1, 1000)
                        for j, v in super().payoffs(strategy).items()}
        g = Taxed(**{f.name: getattr(base, f.name)
                     for f in base.__dataclass_fields__.values()
                     if f.name != "_memo"})
        sol = solve(g, strat("DF"), g.numeric(REP))
        self.assertAlmostEqual(sol.payoffs["x"], 0.0031875 - 0.001, places=9)

    def test_the_payoffs_are_built_once_per_strategy(self):
        g = repaired()
        calls = []
        real = type(g)._gross_payoffs
        type(g)._gross_payoffs = lambda self, s: (calls.append(1), real(self, s))[1]
        try:
            solve(g, strat("RL"), subs(g, REP))
        finally:
            type(g)._gross_payoffs = real
        self.assertEqual(len(calls), 1)

    def test_a_bounded_ceiling_is_not_called_uninformative(self):
        """It is only uninformative when it moves with a variable the model
        leaves unbounded above. Under Logistic the stock is the adopted
        population, which the market's capacity bounds."""
        g = pg.models.logistic_entry()
        self.assertFalse(g.ceiling_is_endogenous(strat("DF")))
        self.assertTrue(repaired().ceiling_is_endogenous(strat("RL")))

    def test_a_bounded_ceiling_still_bites(self):
        g = pg.models.logistic_entry()
        st = strat("DF")
        sol = solve(g, st, g.numeric(pg.models.LOGISTIC_POINT))
        at = dict(g.numeric(pg.models.LOGISTIC_POINT)); at.update(sol.point)
        rep = check_point(g.payoffs(st)["x"] * 1000, sol.point, g.bounds(st),
                          g.numeric(pg.models.LOGISTIC_POINT),
                          upper_bound=g.demand_ceiling(st, at),
                          kinds=dict(sol.kind))
        self.assertTrue(any("ceiling" in v.detail for v in rep.violations()))

    def test_symmetry_asks_about_the_signalling_channel_too(self):
        """The shipped model's asymmetry is not in the share rule: only the
        focal platform can announce."""
        alone = repaired()
        both = pg.models.preannounce_entry(keep_stock=True, signal_accrues=True,
                                           signal_cost=True, rival_signals=True)
        self.assertFalse(alone.players_alike(strat("RL")))
        self.assertTrue(alone.players_alike(strat("DF")))
        self.assertFalse(both.players_alike(strat("RL")))
        self.assertIsNone(equilibrium(alone, REP).role_conflict())
        self.assertIsNone(equilibrium(both, REP).role_conflict())

    def test_withholding_the_gap_does_not_withhold_the_caveat(self):
        self.assertIn("not Nash", str(equilibrium(repaired(), REP)))

    def test_an_all_divergent_outcome_says_there_is_no_ranking(self):
        g = published()
        g.strategies = tuple(s for s in pg.STANDARD_STRATEGIES if s.signals)
        out = equilibrium(g, PT)
        self.assertEqual(out.rankable, [])
        self.assertIn("no ranking", str(out))
        self.assertNotIn("tie()", str(out))


class TestV015Regressions(unittest.TestCase):
    """The nan had shipped since 0.1.3 and through two audits."""

    def test_every_shipped_model_reports_a_finite_payoff(self):
        for name, factory in pg.models.REGISTRY.items():
            g = factory()
            point = pg.models.DEFAULT_POINTS[name]
            for s in g.strategies:
                sol = solve(g, s, g.numeric(point))
                for who, value in sol.payoffs.items():
                    self.assertTrue(value == value and abs(value) != float("inf"),
                                    f"{name}/{s}: pi_{who} = {value}")

    def test_the_logistic_payoff_matches_its_exact_value(self):
        """0.1.3 wrote this model's payoff as one fraction that overflows a
        float while its quotient is ordinary. The assertion is against the
        symbolic value, not against the previous run."""
        g = pg.models.logistic_entry()
        st = strat("DF")
        sol = solve(g, st, g.numeric(pg.models.LOGISTIC_POINT))
        at = dict(g.numeric(pg.models.LOGISTIC_POINT)); at.update(sol.point)
        exact = float(sp.N(g.payoffs(st)["x"].subs(at)))
        self.assertAlmostEqual(sol.payoffs["x"], exact, places=9)
        self.assertGreater(sol.payoffs["x"], 0.0)

    def test_the_logit_sensitivity_moves_the_payoff(self):
        """The 0.1.3 version of this was satisfied by two NaNs."""
        g = pg.models.logistic_entry()
        a = equilibrium(g, dict(pg.models.LOGISTIC_POINT, beta=0.5)).payoffs["DF"]
        b = equilibrium(g, dict(pg.models.LOGISTIC_POINT, beta=3.0)).payoffs["DF"]
        for v in (a, b):
            self.assertTrue(v == v, "payoff is NaN")
            self.assertGreater(v, 0.0)
        self.assertGreater(abs(a - b), 1e-6)

    def test_a_payoff_that_is_not_a_number_is_a_violation(self):
        g = repaired()
        rep = check_point(g.payoffs(strat("RL"))["x"], {}, {}, subs(g, REP),
                          realised={"x": float("nan")})
        self.assertFalse(rep.ok)
        self.assertTrue(any(f.check == "payoff finite"
                            for f in rep.violations()))

    def test_the_evaluation_route_is_reported_when_it_is_not_the_direct_one(self):
        """0.1.6 moved this line from the "evaluation" finding to "evaluation
        coverage", which carries the route alongside the failure count. The
        property asserted -- that needing a slower route is visible -- is the
        same one."""
        g = pg.models.logistic_entry()
        sol = solve(g, strat("DF"), g.numeric(pg.models.LOGISTIC_POINT))
        notes = [f for f in sol.feasibility.findings
                 if f.check == "evaluation coverage"]
        self.assertTrue(notes)
        self.assertTrue(any("cancelled" in n.detail or "exact" in n.detail
                            for n in notes), [n.detail for n in notes])

    def test_mutating_a_game_in_place_does_not_return_stale_payoffs(self):
        g = repaired()
        before = solve(g, strat("RL"), subs(g, REP)).payoffs["x"]
        g.signal_accrues = False
        after = solve(g, strat("RL"), g.numeric(REP)).payoffs["x"]
        fresh = solve(pg.models.preannounce_entry(keep_stock=True,
                      signal_accrues=False, signal_cost=True),
                      strat("RL"), g.numeric(REP)).payoffs["x"]
        self.assertNotAlmostEqual(before, after, places=6)
        self.assertAlmostEqual(after, fresh, places=9)

    def test_replace_does_not_carry_the_previous_models_payoffs(self):
        import dataclasses
        g = repaired()
        solve(g, strat("RL"), subs(g, REP))
        derived = dataclasses.replace(g, signal_accrues=False)
        fresh = pg.models.preannounce_entry(keep_stock=True, signal_accrues=False,
                                            signal_cost=True)
        self.assertAlmostEqual(
            solve(derived, strat("RL"), derived.numeric(REP)).payoffs["x"],
            solve(fresh, strat("RL"), fresh.numeric(REP)).payoffs["x"], places=9)

    def test_the_memo_is_not_a_constructor_parameter(self):
        import dataclasses
        self.assertNotIn("_memo", [f.name for f in dataclasses.fields(pg.Game)
                                   if f.init])

    def test_competitive_refuses_a_divergent_strategy(self):
        rep = verify.check(published(), [verify.Competitive("RF")],
                           over={"sigma": (0.05, 0.4)}, n=2,
                           fixed={"phi": 0.85, "hatvarsigma": 0.3})
        self.assertEqual(rep.results[0].passed + rep.results[0].failed, 0)
        self.assertTrue(rep.ok)

    def test_the_two_evaluation_routes_are_actually_compared(self):
        """The violation branch referenced a name the module had not imported,
        so it would have raised NameError the first time it mattered. Nothing
        in the suite reached it, and pyflakes did."""
        import importlib
        eng = importlib.import_module("pacegame.solve.engine")
        g = repaired()
        real = eng._Evaluator.__call__
        eng._Evaluator.__call__ = lambda self, *a: 42.0
        try:
            sol = eng.solve(g, strat("RL"), subs(g, REP))
        finally:
            eng._Evaluator.__call__ = real
        self.assertFalse(sol.feasibility.ok)
        self.assertTrue(any(f.check == "evaluation"
                            for f in sol.feasibility.violations()))

    def test_available_says_no_when_matplotlib_cannot_be_imported(self):
        from unittest import mock
        from pacegame import plot
        with mock.patch.dict(sys.modules, {"matplotlib": None}):
            self.assertFalse(plot.available())


class TestV016Regressions(unittest.TestCase):

    def test_evaluation_escalates_at_the_point_that_needs_it(self):
        """0.1.5 picked a route from two probe points and never revisited it,
        so a form finite at the probes and overflowing at the optimum was
        simply skipped."""
        import importlib
        eng = importlib.import_module("pacegame.solve.engine")
        x = sp.Symbol("x")
        expr = sp.exp(sp.exp(x)) / (1 + sp.exp(sp.exp(x)))
        ev = eng._Evaluator(expr, [x])
        self.assertAlmostEqual(ev(1.0), 0.938096832585, places=9)
        self.assertEqual(ev.route_name, "direct")
        self.assertIsNotNone(ev(7.0))
        self.assertEqual(ev.route_name, "exact")
        self.assertEqual(ev.failures, 0)

    def test_a_search_over_part_of_its_domain_is_a_violation(self):
        """0.1.6's version of this demonstrated the hazard with a raw function
        handed straight to the optimiser, which bypasses the evaluator and so
        showed nothing about whether the check ever fires on the real path.
        It fires here through an expression that no route can evaluate over
        part of the box."""
        import importlib
        eng = importlib.import_module("pacegame.solve.engine")
        x = sp.Symbol("x", nonnegative=True)
        expr = sp.sqrt(5 - x)                    # complex above 5, no route helps
        ev = eng._Evaluator(expr, [x])
        best_x, _ = eng._max_1d(ev, 0.0, 10.0)
        self.assertLess(best_x, 5.0)             # the optimum is over a subset
        self.assertGreater(ev.failure_rate, 0.02)
        self.assertGreater(ev.rescues, 0)         # exact retries rescue valid points

        # and the end of the sentence this test's name makes: a solve over the
        # same hole reports a violation. 0.1.7 asserted only on the counters
        # and called itself "is_a_violation".
        g = repaired()
        real = type(g).payoffs
        hole = sp.sqrt(sp.Rational(1, 10) - g.entry)

        def holed(self, strategy):
            return {k: v + hole for k, v in real(self, strategy).items()}
        type(g).payoffs = holed
        try:
            sol = solve(g, strat("RL"), g.numeric(REP))
        finally:
            type(g).payoffs = real
        self.assertFalse(sol.feasibility.ok)
        self.assertTrue(any(f.check == "evaluation coverage"
                            for f in sol.feasibility.violations()),
                        [str(f) for f in sol.feasibility.findings])

    def test_rescues_and_failures_are_reported_apart(self):
        """0.1.6 counted only failures, and its own escalation turned the
        overflow case -- the one the check was written for -- into a rescue,
        so the counter stayed at zero everywhere."""
        import importlib
        eng = importlib.import_module("pacegame.solve.engine")
        x = sp.Symbol("x")
        overflow = eng._Evaluator(sp.exp(sp.exp(x)) / (1 + sp.exp(sp.exp(x))), [x])
        self.assertIsNotNone(overflow(7.0))
        self.assertEqual((overflow.rescues, overflow.failures), (1, 0))
        undefined = eng._Evaluator(sp.sqrt(x - 5), [x])
        self.assertIsNone(undefined(1.0))
        self.assertEqual((undefined.rescues, undefined.failures), (0, 1))

    def test_escalation_does_not_stick(self):
        """0.1.6 kept the rescuing route for every later point, on a comment
        rather than a measurement; one bad point early in a grid moved the
        whole search onto SymPy.

        0.1.8 does not bring the cheap route back on the very next call, which
        is what this test asserted at 0.1.7: a failing route is stood down for
        a fixed number of calls and then retried. The property is the same one
        -- the cheap route comes back -- measured over that window instead of
        immediately.
        """
        import importlib
        eng = importlib.import_module("pacegame.solve.engine")
        x = sp.Symbol("x")
        ev = eng._Evaluator(sp.exp(sp.exp(x)) / (1 + sp.exp(sp.exp(x))), [x])
        ev(0.5)
        self.assertEqual(ev.rescues, 0)
        ev(7.0)                                   # forces a rescue
        for _ in range(eng._RETRY_AFTER + 1):
            ev(0.5)
        # the good points after the window used the compiled form again
        self.assertLessEqual(ev.rescues, eng._RETRY_AFTER + 1)
        before = ev.rescues
        ev(0.5)
        self.assertEqual(ev.rescues, before)      # the cheap route came back

    def test_a_player_evaluated_once_still_reports_its_route(self):
        """Suppressing the percentage must not suppress the fact: the
        non-optimising player is the one whose payoff needed rescuing in the
        logistic model."""
        g = pg.models.logistic_entry()
        sol = solve(g, strat("DF"), g.numeric(pg.models.LOGISTIC_POINT))
        notes = [f for f in sol.feasibility.findings
                 if f.check == "evaluation coverage"]
        self.assertEqual(len(notes), 2)
        joined = " ".join(n.detail for n in notes)
        self.assertIn("too few for a rate", joined)
        self.assertIn("cancelled", joined)
        self.assertNotIn("(0.0%)", notes[0].detail)

    def test_evaluation_coverage_fails_when_too_much_cannot_be_evaluated(self):
        g = repaired()
        # a payoff that is genuinely undefined over part of the box, rather
        # than a counter set by hand: 0.1.6 reached this check by forging its
        # input, which established nothing about whether anything reaches it
        real = type(g).payoffs
        entry = g.entry

        def holed(self, strategy):
            out = real(self, strategy)
            return {k: v + sp.sqrt(sp.Rational(1, 10) - entry)
                    for k, v in out.items()}
        type(g).payoffs = holed
        try:
            sol = solve(g, strat("RL"), g.numeric(REP))
        finally:
            type(g).payoffs = real
        notes = [f for f in sol.feasibility.findings
                 if f.check == "evaluation coverage"]
        # "warning" was accepted here until 0.1.8, so a downgrade of the check
        # would have kept this green under a name that says it fails
        self.assertTrue(any(n.status == "violation" for n in notes),
                        [n.detail for n in notes])
        self.assertFalse(sol.feasibility.ok)

    def test_both_players_payoffs_are_cross_checked(self):
        g = repaired()
        sol = solve(g, strat("RL"), subs(g, REP))
        self.assertEqual(len(sol.payoffs), 2)
        for who, value in sol.payoffs.items():
            exact = float(sp.N(sp.sympify(g.payoffs(strat("RL"))[who]).subs(
                {**subs(g, REP), **sol.point})))
            self.assertAlmostEqual(value, exact, places=6, msg=who)

    def test_the_fingerprint_walks_containers(self):
        """0.1.5 skipped container attributes and made one exception for the
        one the built-in model uses."""
        import dataclasses

        @dataclasses.dataclass
        class Weighted(Proportional):
            tilt: tuple = (1, 1)

            def shares(self, stocks):
                base = super().shares(stocks)
                keys = list(base)
                w = dict(zip(keys, self.tilt))
                total = sum(base[k] * w[k] for k in keys)
                return {k: base[k] * w[k] / total for k in keys}

        base = repaired()
        g = dataclasses.replace(base, share_rule=Weighted(
            phi=sp.Symbol("phi", positive=True), tilt=(1, 1)))
        first = solve(g, strat("DF"), g.numeric(REP)).payoffs["x"]
        g.share_rule.tilt = (1, 5)
        second = solve(g, strat("DF"), g.numeric(REP)).payoffs["x"]
        g.invalidate()
        third = solve(g, strat("DF"), g.numeric(REP)).payoffs["x"]
        self.assertNotAlmostEqual(first, second, places=6)
        self.assertAlmostEqual(second, third, places=12)

    def test_the_benchmark_script_refuses_to_certify_a_busy_machine(self):
        """The timing protocol is a script because prose about measuring
        carefully had been added twice and did not work."""
        import importlib.util
        path = os.path.join(os.path.dirname(os.path.abspath(pg.__file__)),
                            "examples", "benchmark.py")
        spec = importlib.util.spec_from_file_location("_bench", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertFalse(mod.wait_for_quiet(limit=-1.0, patience=0))
        self.assertTrue(mod.wait_for_quiet(limit=1e9, patience=0))
        # the threshold must actually reach the test; 0.1.7 rewrote the busy
        # check and left `limit` accepted and ignored for one revision
        self.assertTrue(mod.busy(limit=-1.0)[0])
        self.assertFalse(mod.busy(limit=1e9)[0])
        # 0.1.7 pools the spread across rounds, so n is repeats x rounds; the
        # property asserted -- that the reported n matches what was run -- is
        # unchanged
        result = mod.measure([sys.executable, "-c", "pass"], repeats=3,
                             rounds=2, gap=0)
        self.assertEqual(result["n"], 6)
        self.assertEqual(result["rounds"], 2)
        self.assertLessEqual(result["low"], result["median"])
        self.assertLessEqual(result["median"], result["high"])

    def test_the_benchmark_script_ships_in_both_copies(self):
        inside = os.path.join(os.path.dirname(os.path.abspath(pg.__file__)),
                              "examples", "benchmark.py")
        self.assertTrue(os.path.exists(inside))


class TestPackage(unittest.TestCase):
    def test_version_is_exposed(self):
        self.assertRegex(pg.__version__, r"^\d+\.\d+\.\d+$")
        self.assertEqual(pg.__version__, "0.2.11")

    def test_every_registered_model_has_a_default_point(self):
        self.assertEqual(set(pg.models.REGISTRY), set(pg.models.DEFAULT_POINTS))

    def test_four_standard_strategies_cover_the_two_by_two(self):
        combos = {(s.signals, s.leads) for s in pg.STANDARD_STRATEGIES}
        self.assertEqual(combos, {(True, True), (True, False),
                                  (False, True), (False, False)})


if __name__ == "__main__":
    unittest.main()
