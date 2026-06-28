#!/usr/bin/env bash
# Enforce a minimum line-coverage threshold on Flutter's lcov.info, excluding
# files that carry no meaningful logic (app bootstrap, generated code, and the
# pure colour/const theme). Mirrors the API gate's `--cov-fail-under` so all
# three packages hold the same bar.
set -euo pipefail

MIN="${1:-90}"
LCOV="${2:-coverage/lcov.info}"

if [[ ! -f "$LCOV" ]]; then
  echo "check_coverage: $LCOV not found — run 'flutter test --coverage' first." >&2
  exit 1
fi

# ERE of SF: paths excluded from the metric (non-logic / not meaningfully testable).
EXCLUDE='lib/main[.]dart|lib/core/theme/|[.]g[.]dart|[.]freezed[.]dart'

awk -v exclude="$EXCLUDE" -v min="$MIN" '
  /^SF:/ { path = substr($0, 4); skip = (path ~ exclude) }
  /^LF:/ { if (!skip) lf += substr($0, 4) }
  /^LH:/ { if (!skip) lh += substr($0, 4) }
  END {
    if (lf == 0) { print "check_coverage: no coverage data"; exit 1 }
    pct = (lh / lf) * 100
    printf "Flutter line coverage: %.2f%% (%d/%d lines, excluding bootstrap/generated/theme)\n", pct, lh, lf
    if (pct + 1e-9 < min) {
      printf "FAIL: below %.0f%% threshold\n", min
      exit 1
    }
    printf "PASS: meets %.0f%% threshold\n", min
  }
' "$LCOV"
