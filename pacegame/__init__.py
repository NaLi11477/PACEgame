"""PACEgame: continuous-time sequential entry games with signalling."""
from .core import (Game, Strategy, TwoPhase, Logistic, Proportional, Logit,
                   STANDARD_STRATEGIES)
from .solve import solve, solve_symbolic, Solution, BoundsPrecisionError
from . import models

__version__ = "0.2.11"
__all__ = ["Game", "Strategy", "TwoPhase", "Logistic", "Proportional", "Logit",
           "STANDARD_STRATEGIES", "solve", "solve_symbolic", "Solution",
           "models", "__version__", "BoundsPrecisionError"]
