from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.property_reference as property_reference


def test_build_property_reference_context_prefers_sibling_reference_outputs(monkeypatch):
    fixture_repo = ROOT / "tests" / "fixtures" / "property_reference_repo"
    downturn_path = fixture_repo / "data" / "exports" / "downturn_overlay_table.parquet"
    downturn_path.parent.mkdir(parents=True, exist_ok=True)
    downturn_path.touch()

    monkeypatch.setattr(property_reference, "_discover_property_reference_source_dirs", lambda: [fixture_repo])

    def fake_read_parquet(path):
        if Path(path) == downturn_path:
            return property_reference._fallback_downturn_overlays()
        raise AssertionError(f"Unexpected parquet path requested: {path}")

    monkeypatch.setattr(property_reference.pd, "read_parquet", fake_read_parquet)

    context = property_reference.build_property_reference_context()

    assert set(context["region_risk"]["property_segment"]) == {"Offices", "Warehouses"}
    assert set(context["property_cycle"]["property_segment"]) == {"Offices", "Warehouses"}
    assert context["arrears_environment"].iloc[0]["macro_housing_risk_score"] == 1.75
    assert set(context["downturn_overlays"]["scenario"]) == {"base", "mild", "moderate", "severe"}

    segment_row = context["segment_reference"].loc[
        context["segment_reference"]["property_segment"] == "Offices"
    ].iloc[0]
    assert segment_row["region_risk_band"] == "High"
    assert segment_row["market_softness_band"] == "High"
    assert "Fixture region risk reference" in segment_row["source_note"]
    assert "Fixture property cycle reference" in segment_row["cycle_source_note"]

    provenance = context["reference_provenance"]
    assert set(provenance["dataset_name"]) == {
        "property_region_risk",
        "property_cycle",
        "property_arrears_environment",
        "property_downturn_overlays",
    }
    assert (provenance["status"] == "loaded").all()
