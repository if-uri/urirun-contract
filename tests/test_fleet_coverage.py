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


def test_baseline_ratchet_only_flags_new_violations(tmp_path):
    _connector(tmp_path, "urirun-connector-known", '@conn.command("x/command/y")\ndef y(): ...\n')
    _connector(tmp_path, "urirun-connector-new", '@conn.command("z/command/w")\ndef w(): ...\n')
    rep = fc.scan(str(tmp_path))

    new = fc.new_violations(rep, {"urirun-connector-known"})

    assert [r["name"] for r in new] == ["urirun-connector-new"]
