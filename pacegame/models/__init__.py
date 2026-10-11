from .preannounce_entry import (preannounce_entry, symbols, numeric,
                                BASELINE, REPAIRED)
from .extra import (logistic_entry, asymmetric_quality,
                    LOGISTIC_POINT, ASYMMETRIC_POINT)

#: every model the package ships, by name, for the command line
REGISTRY = {
    "preannounce_entry": preannounce_entry,
    "logistic_entry": logistic_entry,
    "asymmetric_quality": asymmetric_quality,
}

DEFAULT_POINTS = {
    "preannounce_entry": BASELINE,
    "logistic_entry": LOGISTIC_POINT,
    "asymmetric_quality": ASYMMETRIC_POINT,
}

__all__ = ["preannounce_entry", "symbols", "numeric", "BASELINE", "REPAIRED",
           "logistic_entry", "asymmetric_quality", "LOGISTIC_POINT",
           "ASYMMETRIC_POINT", "REGISTRY", "DEFAULT_POINTS"]
