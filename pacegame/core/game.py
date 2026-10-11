"""The game: who signals, who moves first, and what each one earns.

A :class:`Game` binds a lifecycle and a share rule to a strategy profile and
produces symbolic payoffs together with the decision structure the solver needs
(which player chooses what, and in what order).

A *strategy* here is a pair of binary choices for the focal player:
signal or stay silent, and lead or follow.  The four combinations are the RF,
RL, DF and DL of the motivating model, but nothing in this module is specific to
them: :class:`Strategy` is just a named pair of flags, and a user can define
their own set.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass

import sympy as sp
from .numeric import exact_numeric, finite_real, retained_sign
from ._parameters import parameter_symbols

__all__ = ["Strategy", "Roles", "Game", "STANDARD_STRATEGIES"]


@dataclass(frozen=True)
class Strategy:
    name: str
    signals: bool           # does the focal player preannounce?
    leads: bool             # does the focal player deploy first?

    def __str__(self):
        return self.name


STANDARD_STRATEGIES = (
    Strategy("RF", signals=True, leads=True),
    Strategy("RL", signals=True, leads=False),
    Strategy("DF", signals=False, leads=True),
    Strategy("DL", signals=False, leads=False),
)


@dataclass(frozen=True)
class Roles:
    pioneer: str
    follower: str


@dataclass
class Game:
    """A two-player continuous-time entry game.

    Parameters
    ----------
    lifecycle, share_rule
        The two primitives.
    entry, signal
        Symbols for the follower's deployment time and the signal level.
    focal, rival
        Player names; the focal player is the one whose strategy is chosen.
    signal_accrues
        If True the signal builds a stock over the wait (``delta * entry``);
        if False it is a one-off addition (``delta``), which is the supplied baseline
        specification of the motivating model.
    signal_cost, timing_cost
        Coefficients of the quadratic signalling cost and of the cost of
        deploying into an immature market.  Both default to zero, which
        reproduces the supplied baseline model exactly.
    rival_signals
        Whether the rival also announces.  The supplied baseline specification gives
        the announcement channel to the focal player alone, so the default is
        False and the asymmetry is a declared modelling choice rather than an
        accident of the code.  When True the rival matches the focal player's
        announcement level -- a symmetric-announcement benchmark, not a second
        decision variable -- which is the cheapest way to ask whether a result
        is driven by one player having a channel the other lacks.
    signal_ceiling
        Largest announcement level the model regards as credible.  Defaults to
        infinity, which is the supplied baseline specification and is why a costless
        signal has no optimum there.  Setting it to a finite expression bounds
        the signal from inside the model, rather than relying on a cost
        coefficient to make the optimum finite.
    """

    lifecycle: object
    share_rule: object
    entry: sp.Symbol
    signal: sp.Symbol
    focal: str = "x"
    rival: str = "y"
    signal_accrues: bool = False
    signal_cost: sp.Expr = sp.Integer(0)
    timing_cost: sp.Expr = sp.Integer(0)
    rival_signals: bool = False
    signal_ceiling: sp.Expr = sp.oo
    #: earliest the follower can deploy. A rival that can always enter at once
    #: denies the pioneer any monopoly window, so a first-mover advantage needs
    #: either a readiness lag like this one or a cost of entering early.
    entry_floor: sp.Expr = sp.Integer(0)
    time: sp.Symbol = field(default_factory=lambda: sp.Symbol("t", nonnegative=True))
    #: which strategies this game admits; a model with no signalling channel
    #: should not be scored on strategies that use one
    strategies: tuple = STANDARD_STRATEGIES
    #: per-strategy memo for the symbolic payoffs. The integrals are the
    #: expensive part of a solve and do not depend on the parameter point, so
    #: they are computed once. It lives here rather than in the solver because
    #: a solver that assembles the payoff itself silently ignores a subclass
    #: that overrides :meth:`payoffs`, and Game is an extension point.
    _memo: dict = field(default_factory=dict, init=False, repr=False,
                        compare=False)

    def __post_init__(self):
        self.validate_contract()

    def _validate_players(self):
        # Recheck at public boundaries because primitives and names are mutable.
        if self.focal == self.rival:
            raise ValueError("two-player Game requires distinct player identities")
        hook = getattr(self.share_rule, "validate_players", None)
        if hook is not None:
            hook((self.focal, self.rival))

    def validate_contract(self) -> dict:
        """Check mutable identities and independent scalar symbol inventories.

        Primitive coefficients are external constant parameters. Reusing the
        integration variable or a decision Symbol as a coefficient binds that
        parameter before numerical substitution and is outside this contract.
        """
        self._validate_players()
        structural = (self.entry, self.signal, self.time)
        if any(not isinstance(v, sp.Symbol) for v in structural):
            raise ValueError("entry, signal and time must be scalar Symbols")
        if len(set(structural)) != 3:
            raise ValueError("entry, signal and time must be distinct structural Symbols")
        names = {str(v) for v in structural}
        if len(names) != 3:
            raise ValueError("structural Symbols must have distinct names")
        inventory = self._parameter_inventory()
        for name, symbol in inventory.items():
            if symbol in structural or name in names:
                raise ValueError(
                    f"parameter {name!r} must be independent of entry, signal and time")
        return inventory

    def invalidate(self) -> None:
        """Drop the payoff memo. Rarely needed: the key carries a fingerprint
        of everything the payoffs depend on, so a changed model misses."""
        self._memo.clear()

    def _fingerprint(self) -> tuple:
        """What the payoffs depend on, in a form that changes when they do.

        Keying the memo on the strategy name alone is enough only while the
        game is immutable, and it is a mutable dataclass: setting a field in
        place, or deriving a variant with ``dataclasses.replace``, which copies
        the memo, would otherwise return the previous model's payoffs -- a
        well-defined number answering a different question.
        """
        self.validate_contract()
        # SymPy objects are hashable, so the fingerprint is built from them
        # directly.  Serialising with srepr is the obvious way to write this
        # and costs more than the memo saves: it walks every expression tree
        # and builds a string on each lookup, which more than doubled the
        # runtime of a solve.
        def tok(v):
            # sympify is the expensive call here and most values arrive as
            # SymPy objects or plain scalars, which are already hashable.
            # Containers are walked rather than skipped: 0.1.5 excluded them
            # and carved out one exception for the attribute the built-in model
            # happens to use, which left every other container-valued primitive
            # invisible to the key -- a weights tuple changed in place went on
            # returning the previous model's payoffs.
            if isinstance(v, (sp.Basic, bool, int, float, str, type(None))):
                return (type(v), v)
            if isinstance(v, dict):
                # Display strings are not identities: 1 and "1", or symbols
                # with the same name but different assumptions, are distinct
                # keys. A set of recursively encoded pairs also ignores order.
                return (type(v), frozenset((tok(k), tok(x))
                                          for k, x in v.items()))
            if isinstance(v, (tuple, list, set, frozenset)):
                items = tuple(tok(x) for x in v)
                return (type(v),
                        frozenset(items)
                        if isinstance(v, (set, frozenset)) else items)
            try:
                return (type(v), sp.sympify(v))
            except Exception:
                return (type(v), repr(v))

        def state(obj):
            data = dict(getattr(obj, "__dict__", {}))
            names = {f.name for f in fields(obj)} if is_dataclass(obj) else set()
            for cls in type(obj).__mro__:
                slots = cls.__dict__.get("__slots__", ())
                names.update((slots,) if isinstance(slots, str) else slots)
            for name in names:
                if not name.startswith("_") and hasattr(obj, name):
                    data[name] = getattr(obj, name)
            return (type(obj),
                    tuple(sorted(((k, tok(v))
                                  for k, v in data.items()
                                  if not k.startswith("_") and not callable(v)),
                                 key=lambda kv: kv[0])))
        return (state(self.lifecycle), state(self.share_rule),
                self.signal_accrues, self.rival_signals,
                self.focal, self.rival, self.entry, self.signal,
                tok(self.signal_cost), tok(self.timing_cost),
                tok(self.entry_floor), tok(self.signal_ceiling), self.time)

    def players_alike(self, strategy: Strategy) -> bool:
        """Are the two players interchangeable under this strategy?

        Not the same question as whether the share rule treats them alike.  A
        game in which only the focal player can announce is asymmetric in the
        one dimension that decides the outcome, however even-handed the share
        rule is, and a gap computed as though the rival could step into the
        focal position would be a difference between unlike things.
        """
        self.validate_contract()
        hook = getattr(self.share_rule, "is_symmetric_for", None)
        symmetric = (hook((self.focal, self.rival)) if hook is not None
                     else self.share_rule.is_symmetric())
        if not symmetric:
            return False
        if getattr(strategy, "signals", False):
            return False
        return True

    def admits(self, strategy: Strategy) -> bool:
        return strategy in self.strategies

    # ---------------------------------------------------------------- pieces
    def roles(self, strategy: Strategy) -> Roles:
        self.validate_contract()
        return (Roles(self.focal, self.rival) if strategy.leads
                else Roles(self.rival, self.focal))

    def _signal_stock(self, strategy: Strategy) -> sp.Expr:
        if not strategy.signals:
            return sp.Integer(0)
        return self.signal * self.entry if self.signal_accrues else self.signal

    def stocks(self, strategy: Strategy) -> dict:
        """Installed base held by each player when the duopoly stage opens."""
        r = self.roles(strategy)
        sig = self._signal_stock(strategy)
        out = {r.pioneer: self.lifecycle.stock_at(self.entry),
               r.follower: sp.Integer(0)}
        out[self.focal] = out[self.focal] + sig
        if self.rival_signals:
            out[self.rival] = out[self.rival] + sig
        return out

    def shares(self, strategy: Strategy) -> dict:
        return self.share_rule.shares(self.stocks(strategy))

    def gross_payoffs(self, strategy: Strategy) -> dict:
        key = ("gross_payoffs", strategy,
               self._fingerprint())
        if key not in self._memo:
            self._memo[key] = self._gross_payoffs(strategy)
        return dict(self._memo[key])

    def _gross_payoffs(self, strategy: Strategy) -> dict:
        """Undiscounted integral of demand over the horizon, per player."""
        return self._gross_with_shares(strategy, self.shares(strategy))

    def _gross_with_shares(self, strategy: Strategy, sh: dict) -> dict:
        r, st = self.roles(strategy), self.stocks(strategy)
        out = {}
        for player in (r.pioneer, r.follower):
            is_pioneer = player == r.pioneer
            out[player] = sp.simplify(
                sp.Rational(1, 4) * self.lifecycle.accumulate(
                    self.time,
                    entry=sp.Integer(0) if is_pioneer else self.entry,
                    rivals_entry=self.entry if is_pioneer else sp.Integer(0),
                    share=sh[player],
                    stock=st[player],
                    is_pioneer=is_pioneer,
                )
            )
        return out

    def share_sensitivity(self, strategy: Strategy, parameter: sp.Symbol) -> sp.Expr:
        """Local focal-payoff response through the share rule alone.

        Stocks, lifecycle and cost paths are held fixed. The chain rule uses
        independent stock and share placeholders before substituting the model
        expressions. A custom payoff/shares implementation must override this
        hook to declare its channel; otherwise the diagnostic is unavailable.
        This is a partial response at fixed decisions, not an equilibrium total
        derivative or a test of strategic interaction.
        """
        for name in ("payoffs", "_payoffs", "gross_payoffs", "_gross_payoffs",
                     "_gross_with_shares", "shares"):
            method = getattr(self, name)
            if getattr(method, "__func__", None) is not getattr(Game, name):
                raise ValueError("custom payoff/share path requires a share_sensitivity hook")
        key = ("share_sensitivity", strategy, parameter, self._fingerprint())
        if key not in self._memo:
            stocks = self.stocks(strategy)
            z = {j: sp.Dummy("stock_" + j, nonnegative=True) for j in stocks}
            q = {j: sp.Dummy("share_" + j, nonnegative=True) for j in stocks}
            rule = self.share_rule.shares(z)
            template = self._gross_with_shares(strategy, q)[self.focal]
            actual_shares = self.shares(strategy)
            stock_sub = {z[j]: stocks[j] for j in stocks}
            share_sub = {q[j]: actual_shares[j] for j in q}
            response = sum(sp.diff(template, q[j]).subs(share_sub)
                           * sp.diff(rule[j], parameter).subs(stock_sub)
                           for j in q)
            # Keep the chain-rule expression factored. Expanding/cancelling a
            # substituted logit rule can dominate a solve without improving
            # its numerical verdict; evaluation occurs after point substitution.
            self._memo[key] = response
        return self._memo[key]

    def costs(self, strategy: Strategy) -> dict:
        key = ("costs", strategy,
               self._fingerprint())
        if key not in self._memo:
            self._memo[key] = self._costs(strategy)
        return dict(self._memo[key])

    def _costs(self, strategy: Strategy) -> dict:
        r = self.roles(strategy)
        out = {}
        for player in (r.pioneer, r.follower):
            own_entry = sp.Integer(0) if player == r.pioneer else self.entry
            T = sp.sympify(getattr(self.lifecycle, "horizon", 1))
            c = self.timing_cost * (1 - own_entry / T)
            if player == self.focal and strategy.signals:
                c = c + self.signal_cost * self.signal**2 / 2
            out[player] = sp.simplify(c)
        return out

    def payoffs(self, strategy: Strategy) -> dict:
        key = ("payoffs", strategy,
               self._fingerprint())
        if key not in self._memo:
            self._memo[key] = self._payoffs(strategy)
        return dict(self._memo[key])

    def _payoffs(self, strategy: Strategy) -> dict:
        g, c = self.gross_payoffs(strategy), self.costs(strategy)
        return {j: sp.simplify(g[j] - c[j]) for j in g}

    # ------------------------------------------------------- decision order
    def decision_order(self, strategy: Strategy) -> list:
        """Who optimises what, outermost move first.

        The follower always chooses its own deployment time.  A signalling
        player chooses the signal level; when it is also the pioneer the signal
        is committed before the follower responds, which makes the pair a
        Stackelberg problem rather than a joint one.
        """
        r = self.roles(strategy)
        if not strategy.signals:
            return [(r.follower, [self.entry])]
        if strategy.leads:                      # signal first, rival responds
            return [(self.focal, [self.signal]), (r.follower, [self.entry])]
        return [(self.focal, [self.signal, self.entry])]   # joint

    def bounds(self, strategy: Strategy) -> dict:
        """Feasible set declared by the model."""
        self.validate_contract()
        ge = getattr(self.lifecycle, "growth_end",
                     getattr(self.lifecycle, "horizon", sp.Integer(1)))
        b = {self.entry: (self.entry_floor, ge)}
        if strategy.signals:
            b[self.signal] = (sp.Integer(0), self.signal_ceiling)
        return b

    # ---------------------------------------------------------- parameters
    def parameters(self) -> dict:
        """Every free symbol the model takes, by name.

        Collected in one place because four callers used to build this map
        separately and a primitive added in one of them went missing in the
        others.
        """
        return self.validate_contract()

    def _parameter_inventory(self) -> dict:
        """Collect coefficients without recursing into contract validation."""
        expressions = [getattr(self.lifecycle, "horizon", 1)]
        for obj in (self.lifecycle, self.share_rule):
            hook = getattr(obj, "all_params", None)
            expressions.extend(hook() if hook is not None
                               else getattr(obj, "params", ()))
        for extra in (self.signal_cost, self.timing_cost, self.entry_floor,
                      self.signal_ceiling):
            if extra is sp.oo:
                continue
            expressions.append(extra)
        for rule in (self.share_rule,):
            for val in (getattr(rule, "quality", None) or {}).values():
                expressions.append(val)
        out = {}
        for sym in parameter_symbols(*expressions):
            name = str(sym)
            if name in out and out[name] != sym:
                raise ValueError(f"ambiguous parameter name: {name}; distinct Symbols need distinct names")
            out[name] = sym
        return out

    def numeric(self, point: dict) -> dict:
        """Map a ``{name: value}`` dictionary onto the model's symbols.

        Names the model does not use are ignored; names it needs but the point
        omits are reported, because a missing parameter otherwise surfaces much
        later as an expression that will not evaluate.
        """
        names = self.parameters()
        missing = sorted(set(names) - set(point))
        if missing:
            raise KeyError(
                f"missing parameter(s): {', '.join(missing)}; "
                f"this model takes {', '.join(sorted(names))}")
        out = {}
        for name, sym in names.items():
            try:
                value = sp.sympify(point[name])
                finite_real(value)
            except (ValueError, TypeError, ArithmeticError):
                raise ValueError(f"{name} must be a finite real number") from None
            out[sym] = value
        self.validate(out)
        return out

    def validate(self, params: dict) -> None:
        """Reject non-finite values and invalid declared domains before search.

        Custom primitives may override this method for extra restrictions.
        Unknown names in numeric() remain ignored for compatibility with
        dictionaries holding inactive switches; CLI and sweep names are strict.
        """
        import math
        def number(expr, label, *, positive=False, nonnegative=False):
            try:
                value = finite_real(expr, params)
                sign = retained_sign(value)
            except (ValueError, TypeError, ArithmeticError):
                raise ValueError(f"{label} must be a finite real number with a decidable sign") from None
            if positive and sign <= 0:
                raise ValueError(f"{label} must be positive")
            if nonnegative and sign < 0:
                raise ValueError(f"{label} must be nonnegative")
            try:
                converted = float(sp.N(value, 80))
            except (TypeError, ValueError, OverflowError):
                raise ValueError(f"{label} is outside the supported binary64 range") from None
            if not math.isfinite(converted) or (converted == 0 and sign != 0):
                raise ValueError(f"{label} is outside the supported binary64 range")
            return value
        for name, sym in self.parameters().items():
            if sym not in params:
                raise KeyError(f"missing parameter: {name}")
            number(params[sym], name, positive=sym.is_positive is True,
                   nonnegative=sym.is_nonnegative is True)
        T = number(getattr(self.lifecycle, "horizon", 1), "horizon", positive=True)
        ge = number(getattr(self.lifecycle, "growth_end", T), "growth_end")
        floor = number(self.entry_floor, "entry_floor")
        if any(retained_sign(x) < 0 for x in (floor, ge - floor, T - ge)):
            raise ValueError("require 0 <= entry_floor <= growth_end <= horizon")
        for name in ("signal_cost", "timing_cost"):
            number(getattr(self, name), name, nonnegative=True)
        if self.signal_ceiling != sp.oo:
            number(self.signal_ceiling, "signal_ceiling", nonnegative=True)
        quality = getattr(self.share_rule, "quality", None) or {}
        for name, value in quality.items():
            number(value, f"quality[{name}]", positive=True)
        # Coefficient expressions must satisfy the same domains as bare symbols.
        from .share import Proportional, Logit
        from .lifecycle import TwoPhase, Logistic
        if isinstance(self.share_rule, Proportional):
            number(self.share_rule.phi, "phi coefficient", nonnegative=True)
        if isinstance(self.share_rule, Logit):
            number(self.share_rule.beta, "beta coefficient", nonnegative=True)
        if isinstance(self.lifecycle, TwoPhase):
            number(self.lifecycle.sigma, "sigma coefficient", positive=True)
        if isinstance(self.lifecycle, Logistic):
            for name in ("ceiling", "rate"):
                number(getattr(self.lifecycle, name), name, positive=True)

    def demand_ceiling(self, strategy: Strategy, at: dict | None = None):
        """Largest payoff the model's own demand can produce, for a sanity check.

        ``capacity()`` bounds cumulative endogenous demand over the horizon,
        excluding any externally created carried stock. A constant carried
        stock contributes at most stock times horizon. Costs are nonnegative
        on the declared time domain, so this gross ceiling also bounds net
        payoff. It is a loose diagnostic, not a conservation constraint.
        """
        self.validate_contract()
        cap = self.lifecycle.capacity()
        if cap is None:
            return None
        carried = sp.Integer(0)
        if getattr(self.lifecycle, "keep_stock", False):
            stocks = list(self.stocks(strategy).values())
            carried = sp.Max(*stocks) if len(stocks) > 1 else stocks[0]
        T = sp.sympify(getattr(self.lifecycle, "horizon", 1))
        # Simplify the retained symbolic ceiling before substituting numeric
        # parameters. Simplification after substitution can invoke enormous
        # exact-integer GCDs for otherwise ordinary Logistic carried stocks.
        ceiling = sp.simplify((exact_numeric(carried) * exact_numeric(T)
                               + exact_numeric(cap)) / 4)
        return exact_numeric(ceiling, at) if at else ceiling

    def ceiling_is_endogenous(self, strategy: Strategy) -> bool:
        """Does the demand ceiling depend on a decision variable?

        When a signal accrues to the installed base, the stock a player carries
        into the duopoly stage contains the signal level, so the ceiling rises
        with the very payoff it is supposed to bound and the magnitude check
        can never fail.  Callers are told rather than left to assume the check
        bit on something.
        """
        if not getattr(self.lifecycle, "keep_stock", False):
            return False
        bounds = self.bounds(strategy)
        loose = {v for v, (_, hi) in bounds.items() if hi is sp.oo}
        # A ceiling that moves with a decision variable still bites as long as
        # that variable is itself bounded: the ceiling is then bounded too, and
        # a payoff can still exceed it. Only a variable the model leaves open
        # above lets the ceiling outrun whatever it is meant to bound.
        return any(sp.sympify(s).free_symbols & loose
                   for s in self.stocks(strategy).values())
