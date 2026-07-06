from scripts.release_manifest import build_manifest


def test_release_manifest_contains_required_files():
    rows = build_manifest()
    paths = {str(row["path"]) for row in rows}
    assert "docs/PAPER_C_draft.md" in paths
    assert "docs/SUPPORTING_INFORMATION_DRAFT.md" in paths
    assert "data/source_tables/provincial_pv_capacity_2024.csv" in paths
    assert "outputs/figures/NEWFig4_economics_timing.png" in paths


def test_release_manifest_files_exist_and_have_hashes():
    rows = build_manifest()
    assert all(row["exists"] for row in rows)
    assert all(row["bytes"] > 0 for row in rows)
    assert all(len(str(row["sha256"])) == 64 for row in rows)
