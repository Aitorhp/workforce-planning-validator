import validator_engine

def test_legacy_public_api_remains_available():
    required={"MAX_CONSECUTIVE_DAYS","MAX_SHIFT_HOURS","MIN_SHIFT_HOURS","MIN_REST_HOURS","SCHEDULE_SOURCES","load_json_bytes","detect_schedule_sources","run_validation","result_dataframes","build_excel_bytes"}
    assert required.issubset(set(validator_engine.__all__))
    assert validator_engine.MAX_CONSECUTIVE_DAYS == 5
    assert validator_engine.MAX_SHIFT_HOURS == 7.5
