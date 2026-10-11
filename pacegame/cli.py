"""The command line: five verbs, none of which needs anything but the package.

    pacegame models
    pacegame solve preannounce_entry --repair --set sigma=0.1 --set kappa_d=0.05
    pacegame equilibrium preannounce_entry --repair
    pacegame sweep preannounce_entry --wrt hatvarsigma --from 0.1 --to 0.6 --repair
    pacegame verify preannounce_entry --repair
    pacegame examples --extract .
"""
from __future__ import annotations

import argparse
import os
import sys

from . import __version__, models
from .analyze import equilibrium, sweep, verify
from .solve import solve, BoundsPrecisionError


def _subs(game, point):
    return game.numeric(point)


def _build(a):
    if a.model not in models.REGISTRY:
        raise ValueError(f"unknown model {a.model!r}; "
                         f"expected one of {', '.join(sorted(models.REGISTRY))}")
    factory = models.REGISTRY[a.model]
    kwargs = {}
    if a.model in ("preannounce_entry", "asymmetric_quality") and a.repair:
        kwargs = dict(keep_stock=True, signal_accrues=True, signal_cost=True)
    game = factory(**kwargs)
    point = dict(models.DEFAULT_POINTS[a.model])
    if a.repair and not point.get("kappa_d"):
        # a repaired model needs a positive signalling cost, otherwise the
        # signal is still free and still has no optimum
        point["kappa_d"] = 0.05
    for item in a.set or []:
        if "=" not in item:
            raise ValueError(f"--set expects name=value, got {item!r}")
        k, v = item.split("=", 1)
        k = k.strip()
        if k not in game.parameters():
            raise ValueError(f"--set {k!r} is not a parameter of this model")
        point[k] = float(v)
    return game, point


def _print_point(point):
    print("  parameters: " + ", ".join(f"{k}={v:g}" for k, v in sorted(point.items())))


def cmd_models(a):
    print(f"pacegame {__version__}")
    for name in sorted(models.REGISTRY):
        pt = models.DEFAULT_POINTS[name]
        print(f"  {name:22s} default point: "
              + ", ".join(f"{k}={v:g}" for k, v in sorted(pt.items())))
    return 0


def cmd_solve(a):
    game, point = _build(a)
    print(f"pacegame {__version__}  model {a.model}")
    _print_point(point)
    subs = _subs(game, point)
    valid = True
    for st in game.strategies:
        sol = solve(game, st, subs)
        valid = valid and sol.rankable
        marks = "  ".join(f"{k}: {v}" for k, v in sol.kind.items())
        print(f"  {st.name:4s} pi_x = {sol.payoffs[game.focal]:12.7f}   {marks}")
        if not sol.feasibility.ok or not sol.feasibility.complete:
            for v in sol.feasibility.findings:
                if v.status != "violation" and not (v.required and v.status == "warning"):
                    continue
                print(f"        ! {v.detail}")
    return 0 if valid else 1


def cmd_equilibrium(a):
    game, point = _build(a)
    out = equilibrium(game, point)
    print(f"pacegame {__version__}  model {a.model}")
    _print_point(point)
    print(f"  {out}")
    return 0 if out.complete else 1


def _check_parameter(game, point, name, flag):
    """A parameter that is swept must be one the model actually has.

    Sweeping a name the model does not know produces a table in which nothing
    changes -- a result-shaped answer to a malformed question -- so the name is
    refused here rather than absorbed.
    """
    known = set(game.parameters())
    if name not in known:
        raise ValueError(f"{flag} {name!r} is not a parameter of this model; "
                         f"expected one of {', '.join(sorted(known))}")


def cmd_sweep(a):
    game, point = _build(a)
    _check_parameter(game, point, a.wrt, "--wrt")
    if a.steps < 1:
        raise ValueError(f"--steps must be at least 1 (got {a.steps})")
    values = [a.start + (a.stop - a.start) * i / a.steps for i in range(a.steps + 1)]
    outs = sweep(game, a.wrt, values, point)
    names = [s.name for s in game.strategies]
    print(f"pacegame {__version__}  model {a.model}")
    _print_point(point)
    print(f"  {a.wrt:>10s}" + "".join(f"{n:>14s}" for n in names) + "   best")
    flagged = False
    for v, o in zip(values, outs):
        row = ""
        for n in names:
            sol = o.solutions[n]
            if not sol.rankable:
                row += f"{'unresolved':>14s}"
                flagged = True
            else:
                row += f"{o.payoffs[n]:14.7f}"
        tie = o.ties()
        best = o.best if len(tie) == 1 else "tie"
        print(f"  {v:10.4f}{row}   {best}")
    if flagged:
        print("  note: unresolved/invalid candidates are omitted from ranking; "
              "a finite search cap is not a divergence proof.")
    return 1 if flagged else 0


def cmd_verify(a):
    game, point = _build(a)
    names = [s.name for s in game.strategies]
    claims = [verify.Feasible()]
    if "RL" in names and "RF" in names:
        claims.append(verify.Dominates("RL", "RF"))
    if "DF" in names and "DL" in names:
        claims.append(verify.Dominates("DF", "DL"))
    claims.append(verify.Bounded(names[0]))
    claims.append(verify.Competitive(names[0]))
    for var in ("varsigma", "delta"):
        if var == "delta" and "RL" not in names:
            continue
        claims.append(verify.Interior(var, strategy="RL" if "RL" in names else names[0]))
    wrt = a.over or _first_numeric(point)
    _check_parameter(game, point, wrt, "--over")
    lo, hi = point[wrt] * 0.5, point[wrt] * 1.5
    print(f"pacegame {__version__}  model {a.model}")
    _print_point(point)
    rep = verify.check(game, claims, over={wrt: (lo, hi)}, n=a.points,
                       fixed={k: v for k, v in point.items() if k != wrt})
    print(rep)
    return 2 if any(r.errors for r in rep.results) else (0 if rep.ok and rep.complete else 1)


def _first_numeric(point):
    for k in ("sigma", "phi", "beta", "rho"):
        if k in point:
            return k
    return sorted(point)[0]


def cmd_examples(a):
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "examples")
    dst = os.path.join(a.extract, "examples")
    os.makedirs(dst, exist_ok=True)
    n = 0
    if os.path.isdir(src):
        for f in sorted(os.listdir(src)):
            path = os.path.join(src, f)
            if not os.path.isfile(path) or f.startswith((".", "__")):
                continue
            with open(path, encoding="utf-8") as r, \
                 open(os.path.join(dst, f), "w", encoding="utf-8") as w:
                w.write(r.read())
            n += 1
    print(f"pacegame {__version__}: extracted {n} example file(s) to {dst}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="pacegame",
        description="Continuous-time sequential entry games with signalling.")
    p.add_argument("--version", action="version", version=f"pacegame {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(q):
        q.add_argument("model", choices=sorted(models.REGISTRY))
        q.add_argument("--repair", action="store_true",
                       help="switch on keep_stock, signal_accrues and signal_cost")
        q.add_argument("--set", action="append", metavar="NAME=VALUE",
                       help="override a parameter; repeatable")

    sub.add_parser("models", help="list the built-in models")\
        .set_defaults(func=cmd_models)
    q = sub.add_parser("solve", help="constrained optimum of every strategy")
    common(q); q.set_defaults(func=cmd_solve)
    q = sub.add_parser("equilibrium", help="rank the strategies at one point")
    common(q); q.set_defaults(func=cmd_equilibrium)
    q = sub.add_parser("sweep", help="payoffs as one parameter moves")
    common(q)
    q.add_argument("--wrt", required=True)
    q.add_argument("--from", dest="start", type=float, required=True)
    q.add_argument("--to", dest="stop", type=float, required=True)
    q.add_argument("--steps", type=int, default=8)
    q.set_defaults(func=cmd_sweep)
    q = sub.add_parser("verify", help="check the standard claims over a range")
    common(q)
    q.add_argument("--over", help="parameter to vary; defaults to sigma")
    q.add_argument("--points", type=int, default=3)
    q.set_defaults(func=cmd_verify)
    q = sub.add_parser("examples", help="extract the shipped examples")
    q.add_argument("--extract", default=".")
    q.set_defaults(func=cmd_examples)

    a = p.parse_args(argv)
    try:
        return a.func(a)
    except BoundsPrecisionError as exc:
        print(f"unresolved: {exc}", file=sys.stderr)
        return 1
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
