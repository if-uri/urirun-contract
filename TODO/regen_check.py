#!/usr/bin/env python3
# Part of the ifURI solution — brama anty-dryfu generacji.
"""Przegeneruj src/handlers_generated.py z contracts.json do bufora i porównaj z tym, co
w repo. Różnica = albo ktoś ręcznie zedytował generowany plik, albo zmienił kontrakt i
zapomniał przegenerować. To jest egzekucja reguły 'kształtu nie pisze się ręcznie'."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "gen"))
import emit_handlers as eh

committed = os.path.join(ROOT, "src", "handlers_generated.py")
fresh = eh.emit(os.path.join(ROOT, "contracts.json"))
have = open(committed).read() if os.path.exists(committed) else ""
if have != fresh:
    print("DRYF: src/handlers_generated.py != generacja z contracts.json", file=sys.stderr)
    print("  uruchom `make gen` i scommituj (albo cofnij ręczną edycję generowanego pliku)", file=sys.stderr)
    sys.exit(1)
print("OK: wygenerowany kod zgodny z kontraktem (brak ręcznego dryfu)")
