# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Brama additive-only: zmiana kontraktu trasy przy TEJ SAMEJ wersji musi być wstecznie
kompatybilna. Zmiana łamiąca wymaga bumpa wersji (v1→v2).

Wariancja — sedno poprawności:
  • ``out`` jest KOWARIANTNE (obietnica producenta). Wolno: DODAĆ pole, wzmocnić ``?T``→``T``.
    Nie wolno: usunąć pole, osłabić ``T``→``?T``, zmienić typ/const.
  • ``inp`` jest KONTRAWARIANTNE (obowiązek wołającego). Wolno: dodać pole OPCJONALNE,
    zluzować ``T``→``?T``, usunąć wymóg. Nie wolno: dodać pole WYMAGANE, zacieśnić ``?T``→``T``.
  • ``effect`` zmiana, ``reversible`` true→false, usunięcie klasy błędu, usunięcie trasy → łamiące.
    Dodanie trasy / klasy błędu, ``reversible`` false→true → additive.

Głębokie zmiany struktury (oneOf, enum, zagnieżdżenia poza add/remove/opcjonalność/typ) są
klasyfikowane KONSERWATYWNIE: różne ≠ identyczne → łamiące (fałszywe „łamiące" jest bezpieczniejsze
niż fałszywe „additive" — wymusza świadomy bump wersji).
"""
from __future__ import annotations

from typing import Any, NamedTuple


class Change(NamedTuple):
    route: str
    where: str          # "inp" | "out" | "errors" | "effect" | "reversible" | "route"
    field: str
    kind: str           # "additive" | "breaking"
    detail: str


def _optional(tok: Any) -> bool:
    return isinstance(tok, str) and tok.startswith("?")


def _base(tok: Any) -> Any:
    """Token bez znacznika opcjonalności (``?``); dict/list zwracane bez zmian."""
    return tok[1:] if _optional(tok) else tok


def _changes_in_schema(route: str, where: str, prefix: str,
                       old: dict, new: dict, *, covariant: bool) -> list[Change]:
    """Porównaj dwa schematy-obiekty pole po polu wg wariancji (covariant = ``out``)."""
    out: list[Change] = []
    for key in old:
        path = f"{prefix}{key}"
        if key not in new:
            # usunięcie pola: out → łamiące (zniknęła obietnica); inp → additive (luzujemy wymóg)
            out.append(Change(route, where, path,
                              "breaking" if covariant else "additive",
                              "pole usunięte"))
            continue
        out += _changes_in_field(route, where, path, old[key], new[key], covariant=covariant)
    for key in new:
        if key in old:
            continue
        path = f"{prefix}{key}"
        if covariant:
            # nowe pole wyjścia: konsument ignoruje nadmiar → additive
            out.append(Change(route, where, path, "additive", "nowe pole wyjścia"))
        else:
            # nowe pole wejścia: wymagane → łamiące (stary wołający go nie wysyła), opcjonalne → additive
            req = not _optional(new[key])
            out.append(Change(route, where, path,
                              "breaking" if req else "additive",
                              "nowe wymagane pole wejścia" if req else "nowe opcjonalne pole wejścia"))
    return out


def _changes_in_field(route: str, where: str, path: str,
                      old: Any, new: Any, *, covariant: bool) -> list[Change]:
    if old == new:
        return []
    # zagnieżdżony obiekt po obu stronach → rekurencja
    if isinstance(_base(old), dict) and isinstance(_base(new), dict):
        return _changes_in_schema(route, where, f"{path}.", _base(old), _base(new), covariant=covariant)
    # opcjonalność: ?T vs T (ta sama baza)
    oo, no = _optional(old), _optional(new)
    if _base(old) == _base(new) and oo != no:
        if covariant:
            # out: ?T→T wzmocnienie (additive); T→?T osłabienie (breaking)
            kind = "additive" if (oo and not no) else "breaking"
        else:
            # inp: T→?T zluzowanie (additive); ?T→T zacieśnienie (breaking)
            kind = "additive" if (no and not oo) else "breaking"
        return [Change(route, where, path, kind,
                       f"opcjonalność {old!r}→{new!r}")]
    # wszystko inne (typ, const, enum, oneOf, kształt) — konserwatywnie łamiące
    return [Change(route, where, path, "breaking", f"zmiana kształtu {old!r}→{new!r}")]


def compare_route(route: str, old: dict, new: dict) -> list[Change]:
    """Wszystkie zmiany kontraktu jednej trasy (additive i breaking)."""
    ch: list[Change] = []
    if old.get("effect", "query") != new.get("effect", "query"):
        ch.append(Change(route, "effect", "effect", "breaking",
                         f"{old.get('effect')!r}→{new.get('effect')!r}"))
    o_rev, n_rev = bool(old.get("reversible")), bool(new.get("reversible"))
    if o_rev != n_rev:
        ch.append(Change(route, "reversible", "reversible",
                        "breaking" if o_rev and not n_rev else "additive",
                        f"{o_rev}→{n_rev}"))
    ch += _changes_in_schema(route, "inp", "", old.get("inp", {}), new.get("inp", {}), covariant=False)
    ch += _changes_in_schema(route, "out", "", old.get("out", {}), new.get("out", {}), covariant=True)
    old_err, new_err = set(old.get("errors", [])), set(new.get("errors", []))
    for cls in old_err - new_err:
        ch.append(Change(route, "errors", cls, "breaking", "usunięta klasa błędu"))
    for cls in new_err - old_err:
        ch.append(Change(route, "errors", cls, "additive", "nowa klasa błędu"))
    return ch


def incompatibilities(old_doc: dict, new_doc: dict) -> list[Change]:
    """Zmiany ŁAMIĄCE bez bumpa wersji (+ usunięte trasy). Pusta lista = zgodne additive-only.

    Trasa, której wersja wzrosła (np. v1→v2), jest pomijana — nowy major może zmieniać dowolnie.
    """
    old_c = old_doc.get("contracts", {})
    new_c = new_doc.get("contracts", {})
    bad: list[Change] = []
    for route, oc in old_c.items():
        if route not in new_c:
            bad.append(Change(route, "route", route, "breaking", "trasa usunięta"))
            continue
        nc = new_c[route]
        if oc.get("version", "v1") != nc.get("version", "v1"):
            continue  # świadomy bump wersji — major, dozwolone
        bad += [c for c in compare_route(route, oc, nc) if c.kind == "breaking"]
    return bad
