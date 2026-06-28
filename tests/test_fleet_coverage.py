import json

from ci import fleet_coverage as fc


def _connector(root, name, source, contract=False):
    d = root / name
    pkg = d / name.replace("-", "_")
    pkg.mkdir(parents=True)
    (pkg / "core.py").write_text(source)
    if contract:
        (d / "contracts.json").write_text(json.dumps({"contracts": {}}))
    return d


def test_scan_flags_mutating_connector_without_contract(tmp_path):
    _connector(tmp_path, "urirun-connector-email", '@conn.command("message/command/send")\ndef send(): ...\n')
    rep = fc.scan(str(tmp_path))

    assert rep["total"] == 1
    assert rep["violations"][0]["name"] == "urirun-connector-email"
    assert rep["violations"][0]["mutating"] == ["message/command/send"]


def test_scan_accepts_mutating_connector_with_contract(tmp_path):
    _connector(
        tmp_path,
        "urirun-connector-email",
        '@conn.command("message/command/send")\ndef send(): ...\n',
        contract=True,
    )
    rep = fc.scan(str(tmp_path))

    assert rep["violations"] == []
    assert rep["with_contract"] == 1


def test_scan_reads_connector_manifest_inside_package(tmp_path):
    d = _connector(tmp_path, "urirun-connector-ksef", "")
    pkg = d / "urirun_connector_ksef"
    (pkg / "connector.manifest.json").write_text(json.dumps({
        "routes": ["ksef://test/session/online/{ref}/send"]
    }))

    rep = fc.scan(str(tmp_path))

    assert rep["unknown"] == []
    assert rep["violations"][0]["name"] == "urirun-connector-ksef"
    assert rep["violations"][0]["mutating"] == ["session/online/{ref}/send"]


def test_baseline_ratchet_only_flags_new_violations(tmp_path):
    _connector(tmp_path, "urirun-connector-known", '@conn.command("x/command/y")\ndef y(): ...\n')
    _connector(tmp_path, "urirun-connector-new", '@conn.command("z/command/w")\ndef w(): ...\n')
    rep = fc.scan(str(tmp_path))

    new = fc.new_violations(rep, {"urirun-connector-known"})

    assert [r["name"] for r in new] == ["urirun-connector-new"]


def test_baseline_ratchet_only_flags_new_unknown(tmp_path):
    _connector(tmp_path, "urirun-connector-scanner", "")
    _connector(tmp_path, "urirun-connector-empty", "")
    rep = fc.scan(str(tmp_path))

    new = fc.new_unknown(rep, {"urirun-connector-scanner"})

    assert [r["name"] for r in new] == ["urirun-connector-empty"]


def _connector_with_contract(root, name, source, contracts):
    d = root / name
    pkg = d / name.replace("-", "_")
    pkg.mkdir(parents=True)
    (pkg / "core.py").write_text(source)
    (d / "contracts.json").write_text(json.dumps({"contracts": contracts}))
    return d


def test_scan_flags_partial_route_coverage(tmp_path):
    """Connector MA kontrakt, ale trasa mutująca nie ma wpisu → 'partial' (route-level), nie 'violation'."""
    _connector_with_contract(
        tmp_path, "urirun-connector-fs",
        '@conn.command("file/command/delete")\ndef d(): ...\n'
        '@conn.command("file/command/write")\ndef w(): ...\n',
        {"file/command/write": {"effect": "command"}},   # pokrywa tylko jedną z dwóch
    )
    rep = fc.scan(str(tmp_path))
    assert rep["violations"] == []                        # ma kontrakt → nie connector-level brak
    assert rep["partial"][0]["name"] == "urirun-connector-fs"
    assert rep["partial"][0]["uncovered_mutating"] == ["file/command/delete"]


def test_full_route_coverage_is_not_partial(tmp_path):
    _connector_with_contract(
        tmp_path, "urirun-connector-x",
        '@conn.command("a/command/b")\ndef f(): ...\n',
        {"a/command/b": {"effect": "command"}},
    )
    assert fc.scan(str(tmp_path))["partial"] == []


def test_partial_match_tolerates_full_uri_contract_keys(tmp_path):
    """Kontrakt keyed PEŁNYM URI (browser-control/webnode) pasuje do trasy route_key — bez fałszywego braku."""
    _connector_with_contract(
        tmp_path, "urirun-connector-webnode",
        '@conn.command("page/command/navigate")\ndef n(): ...\n',
        {"webnode://page/command/navigate": {"effect": "command"}},
    )
    assert fc.scan(str(tmp_path))["partial"] == []


def test_partial_ratchet_only_flags_new_partials(tmp_path):
    _connector_with_contract(
        tmp_path, "urirun-connector-twin",
        '@conn.command("plan/command/run")\ndef r(): ...\n',
        {"other/query/x": {"effect": "query"}},          # kontrakt nie pokrywa trasy mutującej
    )
    rep = fc.scan(str(tmp_path))
    baseline = {"known_partial": ["urirun-connector-twin"]}
    assert fc.new_partial(rep, fc._baseline_partial_names(baseline)) == []
    assert fc.new_partial(rep, set()) != []               # bez baseline → flagowane
