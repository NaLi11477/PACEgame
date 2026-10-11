"""How new users split between the two platforms.

A share rule maps each player's installed base to the fraction of arriving users
it captures.  The rule is the only place where the network effect enters, so
swapping :class:`Proportional` for :class:`Logit` changes the competitive story
without touching the lifecycle, the payoff functional or the solver.
"""
from __future__ import annotations

from dataclasses import dataclass

import sympy as sp
from ._parameters import parameter_symbols

__all__ = ["ShareRule", "Proportional", "Logit"]


class ShareRule:
    params: tuple = ()

    def shares(self, stocks: dict) -> dict:
        raise NotImplementedError

    def all_params(self) -> tuple:
        """Every symbol the rule reacts to, not only the ones it declares.

        ``params`` is the model's parameter table; a rule can hold further
        symbols elsewhere -- a per-player quality, say -- and a check that asks
        "does the share rule affect the payoff here" must differentiate in
        those too, or it returns a verdict on a subset and reads as a verdict
        on the rule.
        """
        return parameter_symbols(*self.params)

    def validate_players(self, players) -> None:
        """Optional identity check; custom rules may impose their own policy."""

    def is_symmetric_for(self, players) -> bool:
        """Player-aware hook, preserving existing no-argument custom rules."""
        return self.is_symmetric()

    def is_symmetric(self) -> bool:
        """Are the two players interchangeable under this rule?"""
        return True

    def _check(self, out: dict) -> dict:
        total = sp.simplify(sum(out.values()))
        if sp.simplify(total - 1) != 0:
            raise ValueError(f"shares must sum to 1, got {total}")
        return out


@dataclass
class Proportional(ShareRule):
    """Cohen et al. (1996): share is platform value over total value.

    Value is ``theta * (1 + phi * q)``: a baseline quality scaled by a network
    effect acting on the installed base.
    """

    phi: sp.Expr
    quality: dict | None = None      # player -> theta_j; defaults to 1 each

    def __post_init__(self):
        self.phi = sp.sympify(self.phi)
        self.params = parameter_symbols(self.phi)

    def all_params(self) -> tuple:
        return parameter_symbols(self.phi, *(self.quality or {}).values())

    def validate_players(self, players) -> None:
        unknown = set(self.quality or {}) - set(players)
        if unknown:
            names = ", ".join(sorted(map(str, unknown)))
            raise ValueError(f"quality contains unknown player(s): {names}")

    def is_symmetric(self, players=("x", "y")) -> bool:
        self.validate_players(players)
        quality = self.quality or {}
        vals = [sp.sympify(quality.get(player, 1)) for player in players]
        return not vals or all(sp.simplify(v - vals[0]) == 0 for v in vals)

    def is_symmetric_for(self, players) -> bool:
        # Existing subclasses may override the legacy no-argument method.
        if getattr(self.is_symmetric, "__func__", None) is not Proportional.is_symmetric:
            return self.is_symmetric()
        return self.is_symmetric(players)

    def shares(self, stocks: dict) -> dict:
        self.validate_players(stocks)
        q = self.quality or {}
        vals = {j: q.get(j, sp.Integer(1)) * (1 + self.phi * s)
                for j, s in stocks.items()}
        total = sum(vals.values())
        return self._check({j: sp.simplify(v / total) for j, v in vals.items()})


@dataclass
class Logit(ShareRule):
    """Multinomial logit on installed base, with sensitivity ``beta``."""

    beta: sp.Expr

    def __post_init__(self):
        self.beta = sp.sympify(self.beta)
        self.params = parameter_symbols(self.beta)

    def all_params(self) -> tuple:
        return parameter_symbols(self.beta)

    def shares(self, stocks: dict) -> dict:
        ex = {j: sp.exp(self.beta * s) for j, s in stocks.items()}
        total = sum(ex.values())
        return self._check({j: sp.simplify(v / total) for j, v in ex.items()})
