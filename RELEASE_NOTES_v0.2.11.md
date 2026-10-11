# PACEgame v0.2.11

Cross-platform CI repaired and release artifacts rebuilt to stay self-consistent with the source.

## Changes

- **Fixed the hosted cross-platform CI.** The `os × python-version` matrix (ubuntu / macOS / Windows × 3.10–3.13, 12 cells) now passes. Previously red cells were:
  - **All Windows jobs** — the benchmark isolation test asserted load-average thresholds where `os.getloadavg()` is unavailable (POSIX-only); it now skips those assertions instead of failing.
  - **All Python 3.10 jobs** — `unittest.mock` could not resolve string patch targets shadowed by same-named functions. Tests now patch the resolved module objects via `importlib.import_module` + `patch.object`.
- **Rebuilt release artifacts.** Wheel and sdist were rebuilt from the fixed source, so the published packages contain the corrected tests.
- **Regenerated `SHA256SUMS.txt`** (311 entries) to match the new source, tests and distribution files (also adds the previously unlisted `.gitignore` / `AUTHORS.md`).
- Recorded the repair in `CHANGELOG.md` (entry **R12-03**).

## Verification

- All 12 CI cells are green.
- `evidence/verify_release.py` confirms: 311 payload files, 61 package members, `source == wheel == sdist`, examples mirrored, and a complete SHA-256 manifest.

## Installation

```bash
pip install pacegame==0.2.11
# or directly from the wheel
pip install pacegame-0.2.11-py3-none-any.whl
```

## Checksums

`SHA256SUMS.txt` in the repository root lists the SHA-256 of every released file. Highlights:

```
b20e1997aa1b411ad4787ce1c3d351664971b0d715758568baf5c451e6e91899  dist/pacegame-0.2.11-py3-none-any.whl
34e2cff863f3771a9957e304506bc3f09071f6c394901f08f7abb6f4f7d3ac5e  dist/pacegame-0.2.11.tar.gz
```

## Cite this software

This release is archived and citable:

- **DOI:** [10.5281/zenodo.23295744](https://doi.org/10.5281/zenodo.23295744)
- **Record:** <https://zenodo.org/records/23295744>
- **Title:** NaLi11477/PACEgame: pacegame v0.2.11
- **Published:** 2026-10-11 (Zenodo, open access, MIT license)
- **Source:** <https://github.com/NaLi11477/PACEgame> (tag `V0.2.11`)
