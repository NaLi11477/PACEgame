"""Figures, for papers that need them.

Matplotlib is imported lazily and is not a runtime dependency: everything in the
package works without it, and only these functions fail if it is absent.  That
matters for a reviewer installing the package in a clean environment, who should
not have to pull a plotting stack to check that the solver is right.
"""
from __future__ import annotations

__all__ = ["payoff_sweep", "sign_heatmap", "decision_map", "available"]

_ERR = ("matplotlib is needed for pacegame.plot but is not installed; "
        "install it with `pip install matplotlib`, or use the numeric API")


def available() -> bool:
    """Is matplotlib installed *and* importable?"""
    try:
        import matplotlib
        return bool(matplotlib.__version__)
    except Exception:
        # find_spec would be tidier and is wrong: it reports a module that is
        # present but cannot be imported as available, and the figure scripts
        # guard on this before calling into the plot helpers.
        return False


def _plt():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError(_ERR) from exc
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
    return plt


_STYLES = [("-", "o"), ("--", "s"), (":", "^"), ("-.", "d"), ("-", "v")]


def payoff_sweep(values, outcomes, wrt: str, path: str,
                 title: str | None = None, ylabel: str = "payoff"):
    """Payoff of every strategy against one parameter.

    Unresolved or invalid candidates at a point are dropped rather than
    drawn at whatever the search cap happened to be, since plotting a cap as if
    it were an optimum is exactly the error the package exists to catch.
    """
    plt = _plt()
    names = sorted(outcomes[0].payoffs)
    fig, ax = plt.subplots(figsize=(4.6, 3.0), dpi=300)
    dropped = []
    for i, name in enumerate(names):
        xs, ys = [], []
        for v, o in zip(values, outcomes):
            if not o.solutions[name].rankable:
                dropped.append(name)
                continue
            xs.append(v)
            ys.append(o.payoffs[name])
        if not xs:
            continue
        ls, mk = _STYLES[i % len(_STYLES)]
        ax.plot(xs, ys, ls, marker=mk, ms=3, lw=1, color="black",
                markerfacecolor="white" if i % 2 else "black", label=name)
    ax.set_xlabel(wrt)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=9)
    ax.legend(frameon=False, ncol=len(names), fontsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    if dropped:
        ax.text(0.02, 0.95, f"omitted where unresolved/invalid: {', '.join(sorted(set(dropped)))}",
                transform=ax.transAxes, fontsize=6, va="top", color="0.35")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def sign_heatmap(sign_maps, path: str, title: str | None = None):
    """Sign of a response across a grid, one row per map."""
    plt = _plt()
    rows = list(sign_maps)
    width = max(len(m.responses) for m in rows)
    fig, ax = plt.subplots(figsize=(0.35 * width + 2.2, 0.5 * len(rows) + 1.2),
                           dpi=300)
    tone = {"+": 0.2, "-": 0.8, "0": 0.55}
    for r, m in enumerate(rows):
        for c, resp in enumerate(m.responses):
            ax.add_patch(plt.Rectangle((c, r), 1, 1, facecolor=str(tone[resp.sign]),
                                       edgecolor="white", linewidth=0.6))
            ax.text(c + 0.5, r + 0.5, resp.sign, ha="center", va="center",
                    fontsize=7, color="white" if resp.sign != "0" else "black")
    ax.set_xlim(0, width)
    ax.set_ylim(0, len(rows))
    ax.set_yticks([r + 0.5 for r in range(len(rows))])
    ax.set_yticklabels([f"d {m.target} / d {m.wrt}" for m in rows], fontsize=7)
    ax.set_xticks([])
    ax.invert_yaxis()
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    if title:
        ax.set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def decision_map(values, solutions, wrt: str, variable: str, path: str,
                 title: str | None = None, label: str | None = None):
    """A decision variable against a parameter, with corners marked.

    ``solutions`` is either a list, or a mapping of label to list when several
    strategies are drawn together.
    """
    plt = _plt()
    fig, ax = plt.subplots(figsize=(4.6, 3.0), dpi=300)
    series = solutions if isinstance(solutions, dict) else {label or "": solutions}
    for i, (name, sols) in enumerate(series.items()):
        xs, ys, kinds = [], [], []
        for v, sol in zip(values, sols):
            if not sol.rankable:
                continue
            for sym, val in sol.point.items():
                if str(sym) == variable:
                    xs.append(v)
                    ys.append(float(val))
                    kinds.append(sol.kind.get(sym, "interior"))
        if not xs:
            continue
        ls, mk = _STYLES[i % len(_STYLES)]
        ax.plot(xs, ys, ls, lw=1, color="black", label=name or None)
        for x, y, k in zip(xs, ys, kinds):
            ax.plot([x], [y], marker=mk if k == "interior" else "s", ms=4,
                    color="black",
                    markerfacecolor="black" if k == "interior" else "white")
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=7)
    ax.set_xlabel(wrt)
    ax.set_ylabel(f"{variable}*")
    ax.text(0.02, 0.02, "filled: interior    open: on a bound",
            transform=ax.transAxes, fontsize=6, va="bottom", color="0.35")
    if title:
        ax.set_title(title, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path
