PACEgame v0.2.11 implementation validation, 8 October 2026.
R12-01 and R12-02 revision criteria pass. Independent re-audit, author/public-archive completion and current official-template certification remain pending.

FINAL EXECUTION ONLY
validation_source, validation_wheel, validation_core contain the final 493-case suite ledgers and 12 exporters per environment. The full environments pass all 493; the core installation passes 492 and skips only plotting. Every command records imported package path, wheel hash and unchanged member inventory. Final validation follows the release-history label correction and final wheel reinstallation. Earlier draft executions and runtime environments are excluded from this delivered evidence.
old_probes_source/wheel/core contain independently maintained public-interface R7-R12 probes. Round12 fixtures use exact Integer/Rational differences and analytic derivatives, without using production numeric helpers as the oracle. probe_round12_parent.py confirms both defects on frozen v0.2.10 with expected exit 1. verify_round12_fixes.py exits 0 on the new implementation; its acceptance fails on the frozen parent. The original report and complete Round12 evidence are in prior_audit of the complete release.

REPRODUCE OUTSIDE THE CHECKOUT
Create a fresh venv; from the extracted release install:
  python -m pip install --no-index --find-links vendor dist/pacegame-0.2.11-py3-none-any.whl
Change to an empty directory and run:
  python -m pacegame.tests
  python -m pacegame.examples.validate_release validation
  python -m pacegame.examples.validate_audit_021 validation
  python -m pacegame.examples.validate_audit_022 validation
  python -m pacegame.examples.validate_audit_023 validation
  python -m pacegame.examples.validate_audit_024 validation
  python -m pacegame.examples.validate_audit_025 validation
  python -m pacegame.examples.validate_audit_026 validation
  python -m pacegame.examples.validate_audit_027 validation
  python -m pacegame.examples.validate_audit_028 validation
  python -m pacegame.examples.validate_audit_029 validation
  python -m pacegame.examples.validate_audit_0210 validation
  python -m pacegame.examples.validate_audit_0211 validation
Invoke run_public_probes.py by absolute path --out /absolute/new-output; add --source-root /absolute/release for source mode. The final run_revision_validation.py also requires --source-root (for distribution and metadata checks); use --installed for the installed package. Source mode imports exactly that source tree.

DATA AND ARTIFACTS
validation_comparison.json compares 41 numbered groups, excluding only R6-05 installed_versions and installed_matches_snapshot. release baselines, quadrature, finite asymptote and analytic sequential toy are compared to frozen v0.2.10. distribution_integrity.json records an actual fresh sdist rebuild with reused build tooling; final package members agree across source, wheel, sdist and installations. artifact_validation.json covers shared manuscript contents, 232 cells, 17 metadata fields, render text and page bounds. Visual review receipts cover every Word/TeX/report page.
benchmark_v0210.json is historical v0.2.10 timing only; no new benchmark was executed. primary_source_checks.json preserves the dated Round12 guide retrieval limit; it is not a fresh official-template check. Fonts are an OFL derivative with unique family and full current report glyph coverage; the source and derivative hashes and license are recorded.

PORTABLE PAYLOAD CHECK
Run python /absolute/release/evidence/verify_release.py --release-root /absolute/release. The complete SHA256SUMS.txt must cover every payload file, including all distribution and evidence bytes. Final nested delivery checks are summarized in packaging_receipt.json alongside the deliverables.
Execution helpers with local build/manuscript-generation paths are construction evidence; they do not promise that the original scratch environment exists on another machine. Use the portable checker, installed modules and probes for review. Heuristic search arithmetic remains binary64; final retained comparisons do not certify global optima, unsampled domains or Nash games.
