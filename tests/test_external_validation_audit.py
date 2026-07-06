from scripts.external_validation_audit import build_rows


def test_external_validation_audit_has_location_resolved_operation_layer():
    rows = build_rows()
    assert rows
    acceptable = [row for row in rows if row["acceptable"]]
    names = {row["name"] for row in acceptable}
    assert "NEA provincial PV generation utilization rate" in names
    assert "CTGR operating-region PV generation layer" in names


def test_external_validation_audit_checks_pv_wrf_candidates():
    rows = build_rows()
    names = {str(row["name"]) for row in rows}
    assert "PV_WRF global power plant database" in names
    assert "PV_WRF climate inputs" in names


def test_external_validation_audit_lists_partial_national_check():
    rows = build_rows()
    national = [
        row for row in rows if row["name"] == "NBS national aggregate solar generation check"
    ]
    assert len(national) == 1
    assert national[0]["has_generation"]
    assert national[0]["has_capacity"]
    assert not national[0]["has_location"]
    assert not national[0]["acceptable"]


def test_external_validation_audit_lists_spatial_absolute_generation_context():
    rows = build_rows()
    spatial = [
        row for row in rows if row["name"] == "NBS provincial total electricity generation layer"
    ]
    assert len(spatial) == 1
    assert spatial[0]["has_generation"]
    assert spatial[0]["has_location"]
    assert spatial[0]["has_time_axis"]
    assert not spatial[0]["has_capacity"]
    assert not spatial[0]["acceptable"]


def test_external_validation_audit_lists_official_pv_utilization_layer():
    rows = build_rows()
    layer = [
        row for row in rows if row["name"] == "NEA provincial PV generation utilization rate"
    ]
    assert len(layer) == 1
    assert layer[0]["has_generation"]
    assert layer[0]["has_location"]
    assert layer[0]["has_time_axis"]
    assert layer[0]["acceptable"]


def test_external_validation_audit_lists_ctgr_absolute_pv_generation_sample():
    rows = build_rows()
    layer = [
        row for row in rows if row["name"] == "CTGR operating-region PV generation layer"
    ]
    assert len(layer) == 1
    assert layer[0]["has_generation"]
    assert layer[0]["has_location"]
    assert layer[0]["has_time_axis"]
    assert not layer[0]["has_capacity"]
    assert layer[0]["acceptable"]


def test_external_validation_audit_records_climatetrace_negative_result():
    rows = build_rows()
    layer = [
        row for row in rows if row["name"] == "Climate TRACE China power source API response"
    ]
    assert len(layer) == 1
    assert layer[0]["has_generation"]
    assert layer[0]["has_location"]
    assert not layer[0]["acceptable"]
