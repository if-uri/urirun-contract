# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Driver konformancji vs ŻYWY węzeł — łapie węzeł zgodny lokalnie, a kłamiący na drucie.

Odpala `xlang/peer.py serve-http` jako prawdziwy podproces HTTP i steruje go driverem.
Honest → 0 naruszeń; --lie (int/bool serializowany jako string) → driver łapie naruszenie.
"""
import os
import re
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PEER = os.path.join(ROOT, "xlang", "peer.py")
sys.path.insert(0, os.path.join(ROOT, "adapters"))
import conformance  # noqa: E402


def _spawn_peer(lie: bool):
    args = [sys.executable, PEER, "serve-http"] + (["--lie"] if lie else [])
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    deadline = time.time() + 10
    port = None
    while time.time() < deadline:
        line = proc.stdout.readline()
        m = re.match(r"READY (\d+)", line.strip())
        if m:
            port = int(m.group(1))
            break
        if proc.poll() is not None:
            raise RuntimeError(f"peer padł: {proc.stdout.read()}")
    if port is None:
        proc.kill()
        raise RuntimeError("peer nie ogłosił READY")
    return proc, port


def _drive(port):
    contracts = conformance.load_contracts(conformance._DEFAULT_CONTRACTS)
    return conformance.drive(
        f"http://127.0.0.1:{port}", contracts,
        profile="peer", endpoint="/run", routes=None, timeout=5.0,
    )


def test_honest_node_conforms_on_the_wire():
    proc, port = _spawn_peer(lie=False)
    try:
        assert _drive(port) == 0
    finally:
        proc.kill()


def test_lying_node_is_caught_on_the_wire():
    """conform() przechodzi u węzła lokalnie, ale serializacja kłamie — driver to łapie."""
    proc, port = _spawn_peer(lie=True)
    try:
        violations = _drive(port)
        assert violations > 0, "driver przepuścił węzeł kłamiący na drucie"
    finally:
        proc.kill()


def test_unreachable_node_counts_as_violation():
    contracts = conformance.load_contracts(conformance._DEFAULT_CONTRACTS)
    # port nasłuchu, na którym nic nie żyje — transport pada, to naruszenie
    violations = conformance.drive(
        "http://127.0.0.1:1", contracts,
        profile="peer", endpoint="/run", routes=None, timeout=1.0,
    )
    assert violations == len(contracts)
