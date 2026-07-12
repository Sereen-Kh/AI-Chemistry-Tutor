from pathlib import Path


def test_pgvector_verifier_is_read_only() -> None:
    script = Path(__file__).parents[1] / "scripts" / "verify_pgvector.py"
    source = script.read_text(encoding="utf-8")

    assert "CREATE TEMP TABLE" not in source
    assert "INSERT INTO" not in source
    assert "UPDATE " not in source
    assert "DELETE " not in source
    assert "::vector <=> '" in source
