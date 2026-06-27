#!/usr/bin/env python3
# Part of the ifURI solution — cienki shim; logika w urirun_contract.check_single_source
# (sama brama jednego źródła też nie może być zduplikowana). Uruchom też: python -m urirun_contract.check_single_source <root...>
import sys

from urirun_contract.check_single_source import main

if __name__ == "__main__":
    raise SystemExit(main(*(sys.argv[1:] or ["."])))
