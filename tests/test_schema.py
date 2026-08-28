from scac_harness.schema import load_sst_schema


def test_schema_identity() -> None:
    schema = load_sst_schema()
    assert schema["properties"]["schema"]["const"] == "scac-sst-v0.1"
    assert schema["additionalProperties"] is False
