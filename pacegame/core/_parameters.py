"""Deterministic symbol inventories for constant or expression coefficients."""
from __future__ import annotations

import sympy as sp


def parameter_symbols(*expressions) -> tuple:
    """Constants introduce no parameter; expressions introduce free Symbols.

    Symbol identity (including assumptions) is retained. Game separately
    rejects distinct symbols that cannot be addressed by unique string names.
    """
    symbols = set()
    for expression in expressions:
        symbols.update(sp.sympify(expression).free_symbols)
    if any(not isinstance(symbol, sp.Symbol) for symbol in symbols):
        raise ValueError("parameters must be scalar Symbols")
    return tuple(sorted(symbols, key=sp.default_sort_key))
