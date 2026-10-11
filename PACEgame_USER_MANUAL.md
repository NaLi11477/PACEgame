# PACEgame User Manual

**Version 0.2.11** · A Python toolkit for inspecting continuous-time entry and signalling models

**Manual updated:** 11 October 2026

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation](#3-installation)
4. [Functional Modules](#4-functional-modules)
5. [API Reference](#5-api-reference)
6. [Operation Guide](#6-operation-guide)
7. [Command-Line Interface](#7-command-line-interface)
8. [Validation and Accuracy](#8-validation-and-accuracy)
9. [Troubleshooting](#9-troubleshooting)
10. [Support and Version Information](#10-support-and-version-information)
11. [Appendix](#11-appendix)

---

## 1. Introduction

### 1.1 Overview

PACEgame helps researchers, reviewers and instructors inspect stylized two-player entry-timing and preannouncement models. It connects symbolic demand and payoff expressions to numerical candidate searches, local diagnostics, comparative statics and sampled claim reports.

A typical analysis asks:

- Which conditional strategy produces the highest admissible candidate payoff at a specified parameter point?
- Does the selected decision lie inside its domain, on a boundary, or at a fixed value?
- Does a numerical result satisfy the required feasibility and local diagnostic checks?
- How do candidate payoffs or decisions change when a parameter changes?
- Which stated comparisons hold, fail or remain unresolved on a requested sample grid?

The software distinguishes a completed numerical comparison from missing evidence. A search that reaches a finite computational limit is reported as unresolved. It is not evidence that payoff diverges.

**Scope:** PACEgame performs finite heuristic searches and necessary local checks. Candidate rankings are not Nash or subgame-perfect equilibrium certificates. A successful grid check is evidence at sampled points, not a proof over a continuous parameter region. The supplied models use synthetic, uncalibrated inputs.

### 1.2 Key Features

- **Composable models:** two demand lifecycles, two share rules and three built-in model factories.
- **Symbolic payoffs:** demand integrals, gross payoffs and costs built with SymPy.
- **Sequential searches:** the declared decision order determines continuation choices.
- **Explicit result states:** interior, lower corner, upper corner, fixed and search limit.
- **Required diagnostics:** bounds, payoff admission and agreement, and supported necessary derivative and curvature checks.
- **Retained comparisons:** final payoff differences retain parameter and candidate values before numerical conversion.
- **Comparative statics:** payoff and decision responses, parameter sweeps and detected sign crossings.
- **Sampled claims:** separate counts for passes, failures, skips and computation errors.
- **Review materials:** packaged examples and tests, JSON validation exporters, optional figures and offline core dependency wheels.

### 1.3 Technical Architecture

| Layer                       | Technology or implementation                                       |
| --------------------------- | ------------------------------------------------------------------ |
| Language                    | Python ≥3.10                                                       |
| Symbolic and numerical core | SymPy ≥1.12 and its mpmath dependency                              |
| Model input                 | Python objects and parameter dictionaries; CLI parameter overrides |
| Figures                     | Optional Matplotlib ≥3.5, using the Agg backend                    |
| Interfaces                  | `pacegame` console command, `python -m pacegame.cli`, Python API   |
| Packaging                   | `pyproject.toml`, Hatchling, pure-Python wheel                     |
| Tests                       | `unittest`; 493 test methods in the supplied release               |
| Continuous integration      | GitHub Actions; Ubuntu, macOS and Windows × Python 3.10–3.13       |
| License                     | MIT                                                                |

No GPU, model API key or external inference service is required. After dependencies are installed, the numerical workflow runs locally.

### 1.4 Two Ways to Run an Analysis

| Interface    | Intended use                                                 | Example                                                   |
| ------------ | ------------------------------------------------------------ | --------------------------------------------------------- |
| Command line | Quick checks of built-in models                              | `python -m pacegame.cli solve preannounce_entry --repair` |
| Python API   | Custom variants, claims, bounds, parameter grids and exports | `from pacegame.analyze import rank_strategies`            |

The CLI exposes a selected set of operations. Use Python for custom claims, signal ceilings, readiness lags and detailed diagnostic access.

## 2. System Requirements

| Item              | Requirement                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------ |
| Python            | 3.10 or later; hosted CI verified 3.10–3.13                                                |
| Operating system  | Linux, macOS or Windows                                                                    |
| Core dependencies | SymPy ≥1.12; mpmath installed through SymPy                                                |
| Optional figures  | Matplotlib ≥3.5 and its dependencies                                                       |
| GPU               | Not required                                                                               |
| Network           | Needed for online installation; not needed for the supplied offline core installation      |
| Memory and disk   | No measured minimum is specified; symbolic complexity and grid size determine resource use |

The supplied historical Linux audit records use CPython 3.12.14, SymPy 1.14.0 and mpmath 1.3.0. The recorded optional plotting environment uses Matplotlib 3.10.8 and NumPy 2.3.5.

`requirements-core.txt` records core pins. `requirements-reproduce.txt` records principal reproduction dependencies; `requirements-reproduce-lock.txt` records the optional environment. Version pins do not guarantee bitwise identity across hardware.

## 3. Installation

### 3.1 Prepare an Environment

Open a terminal in the extracted `PACEgame-main` directory, where `pyproject.toml`, `dist/` and `vendor/` are located.

Create an environment:

```bash
python -m venv .venv
```

Activate it on Linux or macOS:

```bash
source .venv/bin/activate
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of `python` in subsequent commands. Activation is a convenience, not a requirement.

### 3.2 Offline Core Installation from the Supplied Package

From the extracted software root:

```bash
python -m pip install --no-index --find-links vendor dist/pacegame-0.2.11-py3-none-any.whl
```

The supplied `vendor/` directory contains SymPy 1.14.0 and mpmath 1.3.0 wheels. It does not contain the complete plotting stack. This wheel-based installation does not need a source build or online build dependencies.

### 3.3 Installation from Source with Internet Access

For the public tagged release:

```bash
git clone --branch V0.2.11 --depth 1 https://github.com/NaLi11477/PACEgame.git
cd PACEgame
python -m pip install .
```

For an already extracted archive, run `python -m pip install .` from its root. Build tools and runtime dependencies may be downloaded.

**PyPI:** publication is not relied on in this manual. Use the supplied wheel or source installation; do not assume `pip install pacegame==0.2.11` is available merely because it appears in release notes.

### 3.4 Optional Plotting Installation

From the software root, with internet access:

```bash
python -m pip install ".[figures]"
```

Alternatively, install the plotting extra from the local wheel:

```bash
python -m pip install "dist/pacegame-0.2.11-py3-none-any.whl[figures]"
```

### 3.5 Verify the Installation

```bash
python -c "import pacegame; print(pacegame.__version__)"
python -m pacegame.cli --version
python -m pacegame.cli models
python -m pacegame.cli solve preannounce_entry --repair
```

Expected version: `0.2.11`. The last command should report approximately:

```text
RF   pi_x = 0.0031875   delta: lower corner   varsigma: lower corner
RL   pi_x = 0.0275625   delta: interior      varsigma: upper corner
DF   pi_x = 0.0031875   varsigma: lower corner
DL   pi_x = 0.0031875   varsigma: lower corner
```

This is the stock-cost variant. It is different from the no-argument baseline model.

### 3.6 Using Examples after Wheel Installation

Examples also ship inside the installed package:

```bash
python -m pacegame.cli examples --extract pacegame_demo
python -m pacegame.examples.validate_release validation
```

The extraction command writes files into `pacegame_demo/examples/`. Choose a new destination: existing example files with the same names are overwritten. Module execution works without extracting examples or remaining in the source directory.

## 4. Functional Modules

| Module                    | Purpose                                                                            |
| ------------------------- | ---------------------------------------------------------------------------------- |
| `pacegame.core.lifecycle` | Demand segments, installed stock and capacity envelopes                            |
| `pacegame.core.share`     | Proportional and logit allocation rules                                            |
| `pacegame.core.game`      | Players, strategies, symbolic payoffs, costs, bounds and move order                |
| `pacegame.models`         | Built-in factories and default parameter points                                    |
| `pacegame.solve`          | Numerical candidates, symbolic stationary-point helper and feasibility diagnostics |
| `pacegame.analyze`        | Candidate rankings, sweeps, crossings and comparative statics                      |
| `pacegame.analyze.verify` | Claim definitions, sample grids and reports                                        |
| `pacegame.plot`           | Optional payoff, decision and sign figures                                         |
| `pacegame.cli`            | Command-line interface                                                             |
| `pacegame.examples`       | Demonstrations and validation exporters                                            |
| `pacegame.tests`          | Shipped regression suite                                                           |

### 4.1 Demand and Share Primitives

**`TwoPhase`** represents constant arrivals followed by maturity. **`Logistic`** measures adoption from a common time-zero origin. Their `capacity()` values are diagnostic cumulative-demand envelopes, not customer-conservation constraints.

**`Proportional`** allocates arriving users using installed stock, network effects and optional player quality. **`Logit`** uses exponential weights. Quality keys must name actual players; missing quality values default to one.

### 4.2 Strategies and Decision Ownership

The built-in focal player is `x`; the rival is `y`. The pioneer enters at time zero. `varsigma` is follower entry time and `delta` is the focal signal.

| Label | Focal role | Signal | Decision structure                                         |
| ----- | ---------- | ------ | ---------------------------------------------------------- |
| RF    | Pioneer    | Yes    | Focal signal first; rival follower chooses entry afterward |
| RL    | Follower   | Yes    | Focal player jointly chooses signal and follower entry     |
| DF    | Pioneer    | No     | Rival follower chooses entry                               |
| DL    | Follower   | No     | Focal follower chooses entry                               |

These are conditional role scenarios. Ranking them does not solve a simultaneous role-selection game. `rival_signals=True` mechanically matches the focal signal; it does not create an independently chosen rival signal or its signalling cost.

### 4.3 Built-in Models


| Factory / CLI key | Demand and shares | Strategies | Default characteristics |
|---|---|---|---|
| `preannounce_entry` | TwoPhase + Proportional | RF, RL, DF, DL | Baseline switches off stock retention, signal accrual and signal cost |
| `asymmetric_quality` | TwoPhase + Proportional | RF, RL, DF, DL | Stock retention, accrual and signal cost enabled; rival quality `omega` can vary |
| `logistic_entry` | Logistic + Logit | DF, DL | No signalling; timing cost enabled by default |

### 4.4 Candidate Search and Diagnostics

The numerical solver follows the declared move order backward. It uses grids and local refinement, includes model corners and returns a numerical candidate. It can miss narrow peaks or separated maxima.

Required diagnostics inspect domain membership, finite-real payoffs, final-point payoff agreement and supported necessary optimality conditions. Joint curvature checks cover supported interior groups and at most two critical feasible boundary directions. Earlier-stage reduced objectives and fixed coordinates have different diagnostic scope.

`solve_symbolic()` returns stationary expressions when available. It does not certify feasibility or maximality. The accepted `solve(method=...)` values do not turn the numerical workflow into a global proof.

### 4.5 Claims and Reports

| Claim | Question tested |
|---|---|
| `Feasible()` | Are requested strategy candidates resolved and complete under required checks? |
| `Dominates("RL", "RF")` | Is the focal candidate payoff under RL strictly greater than RF? |
| `Interior("delta", strategy="RL")` | Is the named decision interior in a valid resolved candidate? |
| `Bounded("RL")` | Does the resolved candidate pass the supplied magnitude-bound check? |
| `Competitive("RL")` | Is explicit share-channel sensitivity locally nonzero? |
| `Sign("d pi_x / d sigma", ">", strategy="RL")` | Is the sampled constrained payoff response positive? |

`Competitive` holds decisions, installed stocks, lifecycle and costs fixed while isolating the share channel. A cost-only response cannot establish it. Zero local sensitivity does not establish absence of competition globally.

## 5. API Reference

The signatures below cover common public operations in version 0.2.11. Imports are explicit so scripts do not depend on undocumented top-level re-exports.

### 5.1 Models

```python
from pacegame import models

models.preannounce_entry(
    keep_stock=False, signal_accrues=False, signal_cost=False,
    timing_cost=False, entry_floor=False, rival_signals=False,
    signal_ceiling=False)
models.asymmetric_quality(omega=None, **repairs)
models.logistic_entry(timing_cost=True)
```

For `preannounce_entry`, switches are booleans. Enabling `signal_ceiling` selects the built-in bound `sigma × horizon`; passing a number to this switch does not set an arbitrary ceiling. Enabling `entry_floor` activates the parameter named `lambda`. Use a custom `Game` for other bound expressions.

### 5.2 Model Inspection and Single-strategy Search

```python
from pacegame import solve, solve_symbolic

game.parameters()                  # name -> parameter symbol
game.numeric(point)                # string-keyed input -> symbol-keyed mapping
game.payoffs(strategy)             # player -> symbolic net payoff
game.gross_payoffs(strategy)       # player -> symbolic gross payoff
game.bounds(strategy)             # decision -> interval
game.decision_order(strategy)      # declared stages
game.invalidate()                  # invalidate memoized model expressions

solve(game, strategy, params, method="numeric", signal_cap=1_000_000.0)
solve_symbolic(game, strategy)
```

Pass an admitted `Strategy` object to `solve`, with `params=game.numeric(point)`. `method` accepts `numeric`, `auto` or `symbolic`. `signal_cap` is a positive finite computational budget for an open signal domain, not an economic bound.

`game.numeric()` ignores inactive names for compatibility with model-switch dictionaries. Check spelling explicitly in custom scripts; CLI overrides and sweep/grid axes reject unknown names.

### 5.3 Rankings and Crossings

```python
from pacegame.analyze import rank_strategies, sweep, threshold

rank_strategies(game, point, strategies=None)
sweep(game, name, values, fixed, strategies=None)
threshold(game, name, lo, hi, fixed, winner, loser,
          scan=12, iters=50, tol=1e-12)
```

`strategies` is an iterable of admitted `Strategy` objects. `winner` and `loser` are strategy-name strings. `equilibrium()` remains a compatibility alias for `rank_strategies()`.

A threshold is a detected strict payoff crossing. `None` means no strict crossing was detected at the chosen scan resolution. A sampled zero plateau between opposite signs yields a representative point, not a unique transition boundary.

### 5.4 Comparative Statics

```python
from pacegame.analyze import derivative, sign_map, critical_value

derivative(game, strategy, wrt, point, quantity="payoff", step=1e-4)
sign_map(game, strategy, wrt, over, fixed, n=5, quantity="payoff")
critical_value(game, strategy, wrt, along, lo, hi, fixed,
               scan=12, iters=40, tol=1e-12, quantity="payoff")
```

`strategy` is a name or a pair such as `("RL", "RF")` for a payoff gap. Gap requests require `quantity="payoff"`. Other supported quantities include `pi_x`, `pi_y`, `varsigma` and `delta` when the decision exists in that strategy.

`derivative()` re-solves perturbed points. It uses a feasible one-sided stencil if a central perturbation leaves the parameter domain. Inspect `Response.stencil` and check step-size sensitivity near regime changes.

### 5.5 Verification

```python
from pacegame.analyze import verify

verify.Sign(expr, relation, strategy="RL", step=1e-4, flat=1e-10)
verify.Dominates(winner, loser, strict=True)
verify.Interior(variable, strategy="RL")
verify.Feasible(strategies=())
verify.Bounded(strategy="RL")
verify.Competitive(strategy="RL")
verify.grid(over, n=3)
verify.check(game, claims, over, n=3, fixed=None, max_counterexamples=3)
```

`Sign` supports strict relations `">"` and `"<"` and accepts payoff derivative expressions of the form `d pi_<player> / d <parameter>`. Use `derivative()` for decision responses. With `k` varied axes and `n` values per axis, a Cartesian verification grid contains `n**k` points.

### 5.6 Optional Plotting

```python
from pacegame import plot

plot.available()
plot.payoff_sweep(values, outcomes, wrt, path, title=None, ylabel="payoff")
plot.sign_heatmap(sign_maps, path, title=None)
plot.decision_map(values, solutions, wrt, variable, path, title=None, label=None)
```

Create the output directory first. Payoff plotting omits unresolved or invalid candidates rather than treating their search-cap values as maxima.

## 6. Operation Guide

### 6.1 Rank the Stock-cost Variant

Save this as `quickstart.py` and run `python quickstart.py`:

```python
from pacegame import models
from pacegame.analyze import rank_strategies

game = models.preannounce_entry(
    keep_stock=True, signal_accrues=True, signal_cost=True)
point = dict(sigma=0.1, phi=0.85, hatvarsigma=0.3, kappa_d=0.05)
out = rank_strategies(game, point)
print(out)
print("best:", out.best, "complete:", out.complete)
print("excluded:", out.excluded, "ties:", out.ties())

sol = out.solutions["RL"]
print("decisions:", {str(k): float(v) for k, v in sol.point.items()})
print("states:", {str(k): v for k, v in sol.kind.items()})
print("retained focal payoff:", sol.payoff_value(game.focal))
for finding in sol.feasibility.findings:
    print(finding.status, finding.detail)
```

At this point, RL is the highest ranked candidate: `delta ≈ 1.05`, `varsigma = 0.3`, net payoff `0.0275625`. The entry decision is at its upper boundary; this does not make it invalid. Read both the required checks and the explicit search-assurance limitations.

### 6.2 Compare Assumptions

```python
from pacegame import models
from pacegame.analyze import rank_strategies

point = dict(sigma=0.1, phi=0.85, hatvarsigma=0.3, kappa_d=0.05)
base_options = dict(keep_stock=True, signal_accrues=True, signal_cost=True)
variants = {
    "stock-cost": models.preannounce_entry(**base_options),
    "bounded-signal": models.preannounce_entry(**base_options, signal_ceiling=True),
    "readiness-lag": models.preannounce_entry(**base_options, entry_floor=True),
}
for name, game in variants.items():
    params = dict(point)
    if name == "readiness-lag":
        params["lambda"] = 0.1
    result = rank_strategies(game, params)
    print(name, result)
```

Expected illustrative focal payoffs:

| Variant | RL signal | RL entry | RL payoff | DF payoff | DL payoff |
|---|---:|---:|---:|---:|---:|
| Stock-cost | 1.05 | 0.3 | 0.0275625 | 0.0031875 | 0.0031875 |
| Bounded-signal | 0.1 | 0.3 | 0.005 | 0.0031875 | 0.0031875 |
| Readiness-lag | 1.05 | 0.3 | 0.0275625 | 0.00438346403 | 0.00199153597 |

The signal ceiling is a chosen model assumption, not a credibility certificate. These payoffs are stylized model quantities, not measured welfare or adoption.

### 6.3 Inspect the Baseline

```bash
python -m pacegame.cli solve preannounce_entry
```

The costless baseline can leave signalling strategies at `search limit`. At the illustrative point, silent strategies each yield `0.0031875`. Independent symbolic analysis in the supplied validation evidence gives a finite signal-limit payoff of `0.006375` at entry zero. Reaching a search cap therefore does not establish infinite payoff.

`--repair` changes assumptions by enabling stock retention, signal accrual and signal cost. It does not repair an installation or guarantee that arbitrary models become resolved.

### 6.4 Sweep a Parameter and Save a Table

This block continues the setup in Section 6.1:

```python
import csv
from pathlib import Path
from pacegame.analyze import sweep

values = [0.1, 0.2, 0.3, 0.4]
outcomes = sweep(game, "hatvarsigma", values, point)
Path("results").mkdir(exist_ok=True)
with open("results/payoffs.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["hatvarsigma", "strategy", "payoff", "rankable", "complete"])
    for value, outcome in zip(values, outcomes):
        for name, sol in outcome.solutions.items():
            payoff = str(sol.payoff_value(game.focal)) if sol.rankable else ""
            writer.writerow([value, name, payoff, sol.rankable, outcome.complete])
```


This is a user-script CSV export, not a CLI `--csv` option. Empty payoff cells preserve unresolved status. Do not substitute zero for missing results.

### 6.5 Test Claims and Export a Markdown Report

Continue with the stock-cost `game` and `point` from Section 6.1:

```python
from pathlib import Path
from pacegame.analyze import verify

claims = [
    verify.Feasible(),
    verify.Dominates("RL", "RF"),
    verify.Dominates("DF", "DL"),
    verify.Interior("varsigma", strategy="RL"),
    verify.Interior("delta", strategy="RL"),
]
report = verify.check(
    game, claims,
    over={"sigma": (0.05, 0.4), "phi": (0.3, 0.95)}, n=3,
    fixed={"hatvarsigma": 0.3, "kappa_d": 0.05})
print(report)
Path("results").mkdir(exist_ok=True)
Path("results/claims.md").write_text(report.to_markdown(), encoding="utf-8")
print("all requested evidence passed:", report.ok and report.complete)
```

Failures of strict DF–DL dominance and entry interiority are expected for this example. A counterexample is a scientific result, not necessarily a software fault. `report.complete` can be true even when a claim fails: completeness measures accounting, not success.

### 6.6 Calculate a Payoff Response

Continue with the setup in Section 6.1:

```python
from pacegame.analyze import derivative

for step in (1e-3, 1e-4, 1e-5):
    response = derivative(game, "RL", "sigma", point, step=step)
    print(step, response.slope, response.sign, response.stencil)
```

For this RL corner example, the reported response to `sigma` is zero at these steps. A stable sign across steps is a local numerical check. It is not a proof across all parameters. Requests involving an unresolved candidate can raise an error; retain that status rather than reporting a sign.

### 6.7 Generate Figures

After installing plotting dependencies:

```bash
python -m pacegame.examples.make_figures figures
```

This produces `fig1_published.png`, `fig2_repaired.png`, `fig3_timing.png` and `fig4_signs.png`. The historical filename `fig1_published.png` refers to the supplied baseline; it does not establish published-study replication.

For a custom plot, continue Section 6.4:

```python
from pacegame import plot
plot.payoff_sweep(values, outcomes, "hatvarsigma", "results/payoff_sweep.png")
```

### 6.8 Extend a Model

A custom lifecycle implements `segments`, `stock_at`, `capacity` and a parameter inventory. A custom share rule implements `shares` and declares parameters, typically through `all_params`. `Game` subclasses can override payoffs and bounds.

Preserve these contracts:

- Entry, signal and time are distinct scalar SymPy symbols, separate from external primitive parameters.
- Focal and rival player identities are distinct.
- Bounds become independent numerical intervals after parameter substitution. Decision-dependent domains are unsupported.
- Parameters and evaluated coefficients satisfy finite-real, sign and numerical-range requirements.
- Custom share/payoff paths provide a `share_sensitivity` hook if share-channel diagnostics are required.
- Custom hidden or opaque state needs an explicit representation and cache invalidation after mutation. Automatic cache inspection covers supported public acyclic state, not arbitrary objects.

Consult `docs/model.md` and the audit notes before relying on diagnostics for a new economic specification.

## 7. Command-Line Interface

Use `pacegame` or the interpreter-explicit form `python -m pacegame.cli`.

### 7.1 Commands

| Command | Purpose |
|---|---|
| `--version` | Print version |
| `models` | List built-in models and their default points |
| `solve MODEL` | Print each strategy's candidate payoff and decision states |
| `equilibrium MODEL` | Print conditional candidate rankings; not Nash-certified |
| `sweep MODEL` | Evaluate a one-parameter sequence |
| `verify MODEL` | Run the built-in claim bundle |
| `examples --extract DIR` | Extract examples into `DIR/examples/` |

```bash
python -m pacegame.cli --help
python -m pacegame.cli solve --help
python -m pacegame.cli equilibrium preannounce_entry --repair
python -m pacegame.cli solve asymmetric_quality --set omega=1.5
python -m pacegame.cli solve logistic_entry
python -m pacegame.cli sweep preannounce_entry --repair --wrt hatvarsigma --from 0.1 --to 0.4 --steps 3
python -m pacegame.cli verify preannounce_entry --repair --over sigma --points 3
```

### 7.2 Options and Their Meaning

| Option | Applies to | Meaning |
|---|---|---|
| `--repair` | Model commands | Enables stock retention, accrual and signal cost for preannouncement/asymmetric factories; sets default `kappa_d=0.05` when needed |
| `--set NAME=VALUE` | Model commands | Repeatable numeric parameter override; unknown active parameter names reject |
| `--wrt NAME` | `sweep` | Parameter varied |
| `--from A --to B` | `sweep` | Inclusive endpoints |
| `--steps N` | `sweep` | Number of intervals; evaluates `N+1` points; default 8 |
| `--over NAME` | `verify` | Parameter varied around its current value |
| `--points N` | `verify` | Number of sample values; default 3 |
| `--extract DIR` | `examples` | Parent of the generated `examples/` directory |

The CLI verification range is **0.5 to 1.5 times the current parameter value**. Select an axis explicitly for reproducibility. For arbitrary ranges, multiple axes or a custom claim bundle, use `verify.check()`.

There are no CLI `--out`, `--json`, `--csv`, `--signal-ceiling` or `--entry-floor` options in this version. Redirect console text or use the Python API and example exporters:

```bash
python -m pacegame.cli equilibrium preannounce_entry --repair > ranking.txt
```

### 7.3 Exit Codes

| Code | Meaning |
|---|---|
| 0 | Complete valid operation; for verification, all requested claims passed |
| 1 | Counterexample, unresolved/invalid output, incomplete checks or bounds precision limitation |
| 2 | Malformed input or verification computation errors |

Read the output and exit code together. The baseline or a deliberately false claim may correctly produce code 1. The CLI claim bundle includes tests that need not hold for the selected model.

## 8. Validation and Accuracy

### 8.1 Evidence Included in the Release

| Evidence | Recorded scope |
|---|---|
| Historical source audit | 493 tests passed |
| Historical full installed-wheel audit | 493 tests passed |
| Historical offline core audit | 492 passed; one optional plotting test skipped |
| Validation exporters | Twelve exporters; 41 numbered audit acceptance groups |
| Independent quadrature | 18 model–strategy combinations, both players; recorded maximum net-payoff difference approximately 2.6×10⁻¹⁷ |
| Analytic sequential control | `d=0.5`, `e=0.25`, leader payoff `0.125`; recorded numerical decisions within 10⁻⁶ |
| Hosted CI | All 12 jobs in run 38129504530 passed on 11 October 2026 |

The hosted run covers Ubuntu, macOS and Windows with Python 3.10–3.13. Its workflow builds and installs the wheel, tests outside the checkout, runs validation exporters and generates figures. Historical Linux audit records and current hosted CI are separate evidence sources.

### 8.2 Run the Tests and Validation

```bash
python -m pacegame.tests
python -m pacegame.examples.validate_release validation
python -m pacegame.examples.validate_audit_0211 validation
```

For all retained audit exporters, run this Python script:

```python
import subprocess
import sys

for suffix in ("021", "022", "023", "024", "025", "026",
               "027", "028", "029", "0210", "0211"):
    subprocess.run(
        [sys.executable, "-m", f"pacegame.examples.validate_audit_{suffix}",
         "validation"], check=True)
```

Together with `validate_release`, these are the twelve exporters. Output includes `release_validation.json` and `audit_0211_acceptance.json`. Use a dedicated output directory because reruns can overwrite prior results. Preserve the software version, input point, output and environment when reporting findings.

### 8.3 Numerical Interpretation

- **Local checks are necessary conditions.** Passing them does not prove a global maximum.
- **Binary64 search remains heuristic.** Retaining final values protects specified comparisons; it does not eliminate rounding throughout the search domain.
- **Bounds precision is explicit.** Unsupported endpoint conversion raises `BoundsPrecisionError` rather than silently converting a nonzero interval into a fixed point.
- **Finite differences require stability checks.** Kinks and branch changes can alter slopes.
- **Share activity is local.** Zero sensitivity at a corner does not establish global absence of competition.
- **No empirical calibration is supplied.** Customer conservation, adoption forecasts and welfare interpretations are not implied by the illustrative payoffs.

### 8.4 Release Consistency Notes

Inspection of the supplied `PACEgame-main.zip` found that the Python source files represented in the wheel match the corresponding source files. The illustrative stock-cost CLI solve also reproduced the reported payoffs.

The archive's `SHA256SUMS.txt` lists 311 entries, but its recorded hashes do not match the supplied `CHANGELOG.md`, `README.md` and `pyproject.toml`. The wheel's embedded README retains older publication-status text, while the source README reports GitHub publication and a DOI. These documentation/manifest discrepancies should be resolved when preparing a new distribution. They do not establish a numerical error, but the manifest must not be represented as fully current.

The supplied software metadata names Na Li only. Section 10 lists both manuscript authors using the supplied author information; it does not claim that Jinghan Su is already recorded in the wheel or archival metadata.

## 9. Troubleshooting

### 9.1 `pacegame` Is Not Recognized

Use `python -m pacegame.cli --version`. Confirm installation with the same interpreter through `python -m pip show pacegame`. Check that the virtual environment is active or use its Python executable directly.

### 9.2 `ModuleNotFoundError: No module named 'sympy'`

Install the supplied wheel and dependencies using the offline command in Section 3.2. Running from a source directory alone does not install dependencies.

### 9.3 Offline Installation Cannot Find a Wheel

Run the command from the extracted software root. Verify that both `dist/pacegame-0.2.11-py3-none-any.whl` and `vendor/` are present. An extracted source distribution can differ from the complete review archive; it need not contain the offline wheelhouse.


### 9.4 A Strategy Reaches `search limit`

The solver exhausted a finite probe budget on an open domain. Do not quote the cap as an optimal signal or call the payoff infinite. Check the model analytically or introduce a substantively justified cost/bound. A larger `signal_cap` changes search effort, not the mathematical claim.

### 9.5 A Result Has No Best Strategy or Is Incomplete

Inspect `Outcome.excluded`, each `Solution.rankable`, and `Solution.feasibility.findings`. `Outcome.best is None` means no valid resolved candidate can be ranked. A best candidate can exist while `Outcome.complete` is false because other strategies are excluded.

### 9.6 `Report.ok` Is True but the Report Is Incomplete

No counterexample or computation error was recorded, but some evidence may have been skipped. Require both `report.ok` and `report.complete` before describing the full requested grid as passing. Inspect per-claim `passed`, `failed`, `skipped`, `errors` and `reasons`.

### 9.7 `BoundsPrecisionError`

Large offsets and narrow intervals can become inaccurate or collapse when converted to binary64. Translate or rescale the complete model consistently, including bounds, objectives and diagnostics. Increasing a tolerance without a modelling justification can hide infeasibility.

### 9.8 `--set` Rejects a Parameter

The name may be misspelled or inactive in the chosen model. `hatvarsigma` is the preannouncement growth-end parameter; `varsigma` is a decision, not that parameter. `kappa_d` becomes active when signal cost is enabled. Inspect `game.parameters()` for the actual model.

### 9.9 `Competitive` Fails at the RL Corner

At some stock-cost example corners, the explicit share channel is locally inactive. A failed activity claim does not by itself invalidate the payoff. Check the decision location and diagnostic details.

### 9.10 Figures Are Not Generated

Install the optional figures dependencies and check `pacegame.plot.available()`. The bundled figure script returns code 1 if Matplotlib is unavailable. Core numerical operations do not require plotting.

### 9.11 Symbolic Stationary Points Look Implausible

A stationary point may be outside the domain, a minimum or unavailable. Use numerical candidates and required diagnostics to inspect the constrained problem. Neither symbolic roots nor the accepted `method="symbolic"` option provide a global certificate.

### 9.12 Results Differ across Parameter Steps or Machines

Record Python and dependency versions, vary finite-difference steps and inspect changes in candidate states. Finite scans, precision and regime changes can affect results. Do not infer bitwise reproducibility from version pins alone.

## 10. Support and Version Information

### 10.1 Contact

- **Support email for questions:** 11477@zzrvtc.edu.cn
- **Issue tracker:** https://github.com/NaLi11477/PACEgame/issues
- **Repository:** https://github.com/NaLi11477/PACEgame
- **Versioned release:** https://github.com/NaLi11477/PACEgame/releases/tag/V0.2.11
- **Documentation:** https://github.com/NaLi11477/PACEgame#readme

For a useful bug report, include the software/Python/dependency versions, operating system, exact model switches and parameter values, a minimal command or script, the full traceback or diagnostic output, and expected versus observed behavior.

### 10.2 Version

| Field | Value |
|---|---|
| Software version | 0.2.11 |
| GitHub release tag | `V0.2.11` |
| GitHub release publication | 11 October 2026 |
| Development status in package metadata | Beta |
| License | MIT |
| Manual basis | Supplied `PACEgame-main.zip`, source interfaces and verified GitHub release/CI records |

### 10.3 Authors and Affiliations

The following are the supplied manuscript author details, in author order:

| Author | Affiliation | Email | ORCID |
|---|---|---|---|
| Na Li — corresponding author | Henan Engineering Research Center of Rail Transit Operation Safety and Transport Efficiency Technology and Application | 11477@zzrvtc.edu.cn | https://orcid.org/0009-0005-7164-2742 |
| Jinghan Su | School of Management, Capital Normal University | sujinghan2026@126.com | https://orcid.org/0009-0002-9051-1877 |

### 10.4 Citation and Archive

The repository reports the archival DOI **10.5281/zenodo.23295744**:

- DOI: https://doi.org/10.5281/zenodo.23295744
- Record: https://zenodo.org/records/23295744
- Repository-reported archive title: *NaLi11477/PACEgame: pacegame v0.2.11*

When citing the software, use the creator list and citation export from the archival record and include version 0.2.11. The archive contents and creator metadata were not independently retrieved during this manual preparation; manuscript authorship should not be assumed to equal the archive's creator list. No SoftwareX publication DOI is asserted here.

### 10.5 Testing Reference

```bash
python -m pacegame.tests
```

Verified hosted CI record: https://github.com/NaLi11477/PACEgame/actions/runs/38129504530

## 11. Appendix

### A. Public API Map

| Import location | Public names |
|---|---|
| `pacegame` | `Game`, `Strategy`, `TwoPhase`, `Logistic`, `Proportional`, `Logit`, `STANDARD_STRATEGIES`, `solve`, `solve_symbolic`, `Solution`, `BoundsPrecisionError`, `models`, `__version__` |
| `pacegame.core` | Also exposes `Lifecycle`, `Segment`, `ShareRule`, `Roles` |
| `pacegame.models` | `preannounce_entry`, `asymmetric_quality`, `logistic_entry`, `symbols`, `numeric`, `BASELINE`, `REPAIRED`, `LOGISTIC_POINT`, `ASYMMETRIC_POINT`, `REGISTRY`, `DEFAULT_POINTS` |
| `pacegame.analyze` | `Outcome`, `rank_strategies`, `equilibrium`, `sweep`, `threshold`, `Response`, `SignMap`, `derivative`, `sign_map`, `critical_value`, `POSITIVE`, `NEGATIVE`, `FLAT`, `verify` |
| `pacegame.analyze.verify` | Common claim/report interfaces: `Claim`, `Sign`, `Dominates`, `Interior`, `Feasible`, `Bounded`, `Competitive`, `Result`, `Report`, `grid`, `check` |
| `pacegame.plot` | `available`, `payoff_sweep`, `sign_heatmap`, `decision_map` |

Use `game.numeric(point)` for the actual model rather than assuming the preannouncement-specific `models.numeric()` helper applies to every factory.

### B. Output Field Glossary

| Field | Meaning |
|---|---|
| `Solution.point` | Decision-symbol-to-value mapping |
| `Solution.kind` | Decision-symbol-to-classification mapping |
| `Solution.payoffs` | Display/compatibility float payoffs for each player |
| `Solution.payoff_value(player)` | Finite-real retained payoff for comparison |
| `Solution.unresolved` | Search-limit or explicit unbounded state |
| `Solution.rankable` | Resolved, finite candidate with successful complete required checks |
| `Solution.feasibility.ok` | No recorded violations |
| `Solution.feasibility.complete` | Necessary required checks have verdicts |
| `Outcome.best` | Highest ranked valid candidate label, or `None` |
| `Outcome.complete` | Requested ranking has no excluded candidates and a valid best label |
| `Outcome.excluded` | Invalid/unresolved labels omitted from ranking |
| `Outcome.ties()` | Valid candidate labels within the default absolute tie tolerance 1e-9 |
| `Report.ok` | No failed claims or computation errors |
| `Report.complete` | Every claim accounted for at every point, without skips/errors |
| `Result.holds` | Positive pass count with no failures, skips or errors |
| `Result.rate` | Pass fraction among passes plus failures; skips/errors are outside this denominator |
| `Response.slope` | Finite-difference response |
| `Response.stencil` | Central, forward or backward difference |

A `fixed` decision has a singleton domain. It has no feasible one-sided movement and is not an interior optimum. A `search limit` is a computational status rather than an economic corner.

### C. Parameter Guide

| Name | Model | Meaning |
|---|---|---|
| `sigma` | Preannouncement / asymmetric | Arrival-rate parameter |
| `phi` | Preannouncement / asymmetric | Network-effect parameter in proportional shares |
| `hatvarsigma` | Preannouncement / asymmetric | End of growth phase; not follower entry decision |
| `kappa_d` | Signal-cost variants | Quadratic signalling-cost coefficient |
| `kappa_t` | Timing-cost variants / logistic | Timing-cost coefficient |
| `lambda` | Preannouncement with `entry_floor=True` | Earliest permitted follower entry |
| `omega` | Asymmetric, when not fixed in factory | Rival quality relative to focal quality one |
| `kappa` | Logistic | Adoption ceiling |
| `rho` | Logistic | Adoption rate |
| `tau` | Logistic | Adoption midpoint |
| `beta` | Logistic | Logit share sensitivity |

For built-in models, the horizon is one. General custom models require `0 ≤ entry_floor ≤ growth_end ≤ horizon` and a positive horizon; the Logistic domain uses its horizon as the effective growth end. Active parameters must meet their symbol/domain constraints and finite-real/range checks. Zero cost coefficients are allowed.

### D. Repository Layout

| Path | Contents |
|---|---|
| `pacegame/core/` | Lifecycle, share, model and numeric primitives |
| `pacegame/models/` | Built-in model factories |
| `pacegame/solve/` | Search engine, domains and feasibility checks |
| `pacegame/analyze/` | Rankings, crossings, statics and verification |
| `pacegame/cli.py` | CLI commands |
| `pacegame/plot.py` | Optional plotting helpers |
| `pacegame/examples/` | Examples included in the wheel |
| `pacegame/tests/` | Regression modules included in the wheel |
| `examples/` | Source-tree example scripts |
| `docs/` | Model description and historical audit notes |
| `evidence/` | Recorded validation, tests and reproduction evidence |
| `dist/` | Version 0.2.11 wheel and source distribution |
| `vendor/` | Offline core dependency wheels |
| `.github/workflows/tests.yml` | Hosted CI matrix |
| `pyproject.toml` | Packaging, version and dependency metadata |
| `SHA256SUMS.txt` | Supplied file hashes; see consistency notes in Section 8.4 |
| `LICENSE` | MIT license |

---

*PACEgame 0.2.11 · MIT License · User manual updated 11 October 2026*
