from scripts.government_pv_generation_inventory_audit import audit_status, build_rows


def test_complete_government_pv_generation_inventory_is_not_claimed():
    rows = build_rows()
    status = audit_status(rows)
    assert status["obtained"] is False
    assert "not acquired" in status["decision"]
    assert not any(row["complete_government_inventory"] for row in rows)


def test_audit_records_official_candidates_and_required_fields():
    rows = build_rows()
    candidates = {row["candidate"] for row in rows}
    assert "National Data regional annual database" in candidates
    assert "2024 renewable power monitoring result" in candidates
    assert "China Statistical Yearbook 2025 Table 9-19" in candidates
    required = str(audit_status(rows)["required_acceptance_fields"])
    assert "province" in required
    assert "PV or solar generation" in required
    assert "official source URL or document ID" in required
