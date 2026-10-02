#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python cad/source/build_cad.py
python textile/build_patterns.py
python harness/build_harness.py
python cad/source/build_cad.py
python embroidery/prepare_logo.py
python embroidery/digitize_logo.py
python docs/derive_closures_and_patch.py
bash tests/run_tests.sh
python tests/validate_release.py
python docs/build_review_pdf.py
