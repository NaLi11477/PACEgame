"""Market-lifecycle demand trajectories.

A lifecycle turns a market-growth story into a piecewise demand path for one
player, given when that player entered and what share of new users it wins.
Everything downstream integrates that path, so replacing the lifecycle is how a
user moves from one demand story to another without touching the solver.

The built-in :class:`TwoPhase` is the two-stage growth of Bayus (1997): users
arrive at a constant rate during a rapid-growth phase and stop arriving once the
market matures.  :class:`Logistic` is provided as a second instance so that the
interface is exercised by more than one implementation.
"""
from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from ._parameters import parameter_symbols

__all__ = ["Segment", "Lifecycle", "TwoPhase", "Logistic"]


@dataclass(frozen=True)
class Segment:
    """Demand on a half-open interval of the horizon."""

    lo: sp.Expr
    hi: sp.Expr
    expr: sp.Expr

    def integrate(self, t: sp.Symbol) -> sp.Expr:
        return sp.integrate(self.expr, (t, self.lo, self.hi))


class Lifecycle:
    """Base class. Subclasses implement :meth:`segments` and :meth:`capacity`."""

    #: symbols the lifecycle introduces, for the model's parameter table
    params: tuple = ()

    def all_params(self) -> tuple:
        return parameter_symbols(*self.params)
    #: classes already told that they do not implement stock_at; one solve
    #: builds the payoffs many times and the warning is about the class
    _warned: set = set()

    def segments(self, t, entry, rivals_entry, share, stock, is_pioneer):
        raise NotImplementedError

    def capacity(self):
        """Upper bound on cumulative endogenous demand over the horizon.

        Units are demand times time, excluding externally created stock.
        Built-in paths have nonnegative demand and shares in [0, 1]. Custom
        lifecycles must establish this envelope under their own restrictions.

        Returns None when the lifecycle cannot say, in which case the payoff
        magnitude check is reported as unavailable rather than silently skipped:
        a check that quietly does not run is worse than one that says so.
        """
        return None

    def stock_at(self, time):
        """Installed base a player entering at 0 holds by ``time``.

        The game needs this to say what a pioneer carries into the duopoly
        stage.  Reading it off a lifecycle attribute instead ties the game to
        one demand story: a lifecycle with no arrival-rate symbol then hands
        every player a base of zero, the share rule returns one half whatever
        its parameters are, and the competitive channel is silently dead.

        The default reproduces what the game used to do on its own, so a
        lifecycle written against 0.1.1 keeps working; it warns, because a
        lifecycle with no ``sigma`` gets a base of zero from it and that is the
        failure this method exists to remove.
        """
        import warnings
        if type(self) in Lifecycle._warned:
            return (getattr(self, "sigma", None) or sp.Integer(0)) * time
        Lifecycle._warned.add(type(self))
        rate = getattr(self, "sigma", None)
        if rate is None:
            warnings.warn(
                f"{type(self).__name__} does not implement stock_at(); falling "
                f"back to a base of zero, which makes the share rule inactive. "
                f"Implement stock_at() to say what a player entering at 0 holds "
                f"by a given time.", RuntimeWarning, stacklevel=2)
            return sp.Integer(0)
        warnings.warn(
            f"{type(self).__name__} does not implement stock_at(); using "
            f"sigma * time. Implement it explicitly.",
            DeprecationWarning, stacklevel=2)
        return rate * time

    def demand_of(self, t, **kw) -> sp.Expr:
        """The trajectory as a single Piecewise, for plotting or inspection."""
        segs = self.segments(t, **kw)
        pieces = [(s.expr, sp.And(t >= s.lo, t < s.hi)) for s in segs]
        return sp.Piecewise(*pieces, (sp.Integer(0), True))

    def accumulate(self, t, **kw) -> sp.Expr:
        """int_0^T D(t) dt, summed over the segments.

        The share and the carried stock are constants in ``t`` but can be
        involved functions of the decision variables.  Left in place they are
        folded into the integrand -- a logit share and a logistic path combine
        into one rational expression in ``exp(-rho t)`` -- and SymPy then fails
        on an integral that is elementary once the constants are held aside.
        They are therefore integrated as opaque symbols and put back after, so
        that what goes under the integral sign is only the demand path.
        """
        held = {}
        for name in ("share", "stock"):
            value = kw.get(name)
            if value is None or sp.sympify(value).is_number:
                continue
            token = sp.Dummy(name)
            held[token] = value
            kw[name] = token
        total = sp.together(sum(s.integrate(t) for s in self.segments(t, **kw)))
        return total.subs(held)


@dataclass
class TwoPhase(Lifecycle):
    """Rapid growth at rate ``sigma`` until ``growth_end``, then a flat market.

    ``keep_stock`` decides whether a player that enters late carries the
    installed base it holds at entry into its own demand level.  The supplied baseline
    specification of the motivating model sets this to False for followers,
    which turns out to remove any reason to enter late at all; see
    ``docs/model.md``.
    """

    sigma: sp.Expr
    growth_end: sp.Expr
    horizon: sp.Expr = sp.Integer(1)
    keep_stock: bool = True

    def __post_init__(self):
        self.params = parameter_symbols(self.sigma, self.growth_end, self.horizon)

    def all_params(self) -> tuple:
        return parameter_symbols(self.sigma, self.growth_end, self.horizon)

    def capacity(self):
        g, T = self.growth_end, self.horizon
        return self.sigma * (g * T - g**2 / 2)

    def stock_at(self, time):
        # the declared bounds keep entry inside the growth phase, so a Min
        # against growth_end here would only add a Heaviside to every closed
        # form and defeat solve_symbolic
        return self.sigma * time

    def segments(self, t, entry, rivals_entry, share, stock, is_pioneer):
        s, ge, T = self.sigma, self.growth_end, self.horizon
        if is_pioneer:
            duopoly_start = rivals_entry
            held = s * duopoly_start
            return [
                Segment(sp.Integer(0), duopoly_start, s * t),
                Segment(duopoly_start, ge, held + s * share * (t - duopoly_start)),
                Segment(ge, T, held + s * share * (ge - duopoly_start)),
            ]
        held = stock if self.keep_stock else sp.Integer(0)
        return [
            Segment(entry, ge, held + s * share * (t - entry)),
            Segment(ge, T, held + s * share * (ge - entry)),
        ]


@dataclass
class Logistic(Lifecycle):
    """S-shaped adoption; the market's own clock is independent of entry.

    Included so that the lifecycle interface is not a single-implementation
    abstraction: the solver never sees anything but :class:`Segment` objects.
    """

    ceiling: sp.Expr
    rate: sp.Expr
    midpoint: sp.Expr
    horizon: sp.Expr = sp.Integer(1)
    keep_stock: bool = True

    def __post_init__(self):
        self.params = parameter_symbols(self.ceiling, self.rate, self.midpoint, self.horizon)

    def all_params(self) -> tuple:
        return parameter_symbols(self.ceiling, self.rate, self.midpoint, self.horizon)

    def capacity(self):
        return self.ceiling * self.horizon

    def stock_at(self, time):
        return self._adopted(time) - self._adopted(sp.Integer(0))

    def _adopted(self, t):
        return self.ceiling / (1 + sp.exp(-self.rate * (t - self.midpoint)))

    def segments(self, t, entry, rivals_entry, share, stock, is_pioneer):
        T = self.horizon
        # measured from the same origin as stock_at, so that what a player
        # carries into the share rule and what enters its demand level are the
        # same quantity; using the raw curve here left them differing by the
        # mass the market already held at time zero
        base = self._adopted(sp.Integer(0))
        if is_pioneer:
            start = rivals_entry
            return [
                Segment(sp.Integer(0), start, self._adopted(t) - base),
                Segment(start, T, self._adopted(start) - base
                        + share * (self._adopted(t) - self._adopted(start))),
            ]
        held = stock if self.keep_stock else sp.Integer(0)
        return [Segment(entry, T,
                        held + share * (self._adopted(t) - self._adopted(entry)))]
