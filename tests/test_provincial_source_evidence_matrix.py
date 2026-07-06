from scripts.provincial_source_evidence_matrix import build_rows


def test_provincial_source_evidence_matrix_covers_all_source_rows():
    rows = build_rows()
    assert len(rows) == 62
    datasets = {row["dataset"] for row in rows}
    assert datasets == {
        "provincial_pv_capacity_2024",
        "nea_pv_utilization_rate_2024",
    }


def test_provincial_source_evidence_matrix_marks_current_status():
    rows = build_rows()
    capacity = [row for row in rows if row["dataset"] == "provincial_pv_capacity_2024"]
    utilization = [row for row in rows if row["dataset"] == "nea_pv_utilization_rate_2024"]
    assert all(row["row_level_official_status"] == "complete" for row in capacity)
    assert all(row["row_level_official_status"] == "complete" for row in utilization)
    assert {row["metric"] for row in utilization} == {"PV generation utilization rate"}
    assert all(row["current_source_url"] for row in rows)
    assert all(row["required_evidence"] for row in rows)
    assert all(row["next_action"] for row in rows)
