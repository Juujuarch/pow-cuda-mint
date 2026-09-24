from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_no_credentials_in_template():
    text = (ROOT / "miner.py").read_text()
    assert 'PRIVATE_KEY = ""' in text
    assert "0x" + "a" * 64 not in text


def test_required_safety_gates_exist():
    text = (ROOT / "miner.py").read_text()
    for gate in ("verify_solution", "simulate_mint", "broadcast_mint", "refresh_job"):
        assert f"def {gate}" in text
