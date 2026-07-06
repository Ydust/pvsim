from scripts.source_audit_gate import build_summaries


def test_source_audit_summaries_cover_both_tables():
    summaries = build_summaries()
    assert {summary.table for summary in summaries} == {
        "Provincial PV capacity 2024",
        "NEA provincial PV utilization rate 2024",
    }
    assert sum(summary.row_count for summary in summaries) == 62


def test_source_audit_is_submission_ready_for_official_layers():
    summaries = build_summaries()
    assert all(summary.missing_provenance_count == 0 for summary in summaries)
    assert sum(summary.row_level_complete_count for summary in summaries) == 62
    assert sum(summary.pending_row_level_count for summary in summaries) == 0
    assert all(summary.submission_ready for summary in summaries)
    utilization = [
        summary
        for summary in summaries
        if summary.table == "NEA provincial PV utilization rate 2024"
    ][0]
    assert utilization.submission_ready
