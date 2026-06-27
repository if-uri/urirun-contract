#!/usr/bin/env bash
# Part of the ifURI solution — przygotowanie wydania w 3 ekosystemach (PyPI · npm · Go module).
#
# Buduje i WERYFIKUJE artefakty; NIE publikuje (upload wymaga tokenów). Na końcu wypisuje
# dokładne komendy uploadu do ręcznego uruchomienia z Twoimi poświadczeniami.
#
#   bash scripts/release.sh          # build + weryfikacja + instrukcje uploadu
#   bash scripts/release.sh --check  # tylko weryfikacja (bez budowania)
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PY="${PY:-python}"

VERSION=$("$PY" - <<'EOF'
import tomllib
print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])
EOF
)
echo "▶ urirun-contract v$VERSION — przygotowanie wydania"

# ── 1. Python / PyPI ─────────────────────────────────────────────────────────
echo "── [1/3] Python (PyPI) ──"
rm -rf dist build ./*.egg-info
"$PY" -m build >/dev/null
"$PY" -m twine check dist/*"$VERSION"*
echo "  ✓ sdist+wheel zbudowane, twine check PASSED"

# ── 2. JS / npm ──────────────────────────────────────────────────────────────
echo "── [2/3] JS (npm) ──"
if command -v npm >/dev/null; then
  ( cd sdk/js && npm pack --dry-run >/dev/null && echo "  ✓ npm pack (sdk/js) OK" )
else
  echo "  ⚠ brak npm — pomijam weryfikację paczki JS"
fi

# ── 3. Go module ─────────────────────────────────────────────────────────────
echo "── [3/3] Go module ──"
if command -v go >/dev/null; then
  ( cd sdk/go && go build ./... && go vet ./... && echo "  ✓ go build+vet OK" )
else
  echo "  ⚠ brak go — pomijam weryfikację modułu Go"
fi

# ── komendy uploadu (ręcznie, z tokenami) ────────────────────────────────────
cat <<EOF

═══ GOTOWE DO PUBLIKACJI — uruchom ręcznie z poświadczeniami ═══

  # PyPI (token: ~/.pypirc lub TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-...)
  $PY -m twine upload dist/*$VERSION*

  # npm (npm login lub NODE_AUTH_TOKEN)
  ( cd sdk/js && npm publish --access public )

  # Go module — publikacja = tag VCS w podkatalogu modułu:
  git tag sdk/go/v$VERSION && git push origin sdk/go/v$VERSION
  #   konsumenci: go get github.com/if-uri/urirun-contract/sdk/go/contract@v$VERSION

Pamiętaj: zbumpnij wersję w pyproject.toml ORAZ sdk/js/package.json przed kolejnym wydaniem.
EOF
