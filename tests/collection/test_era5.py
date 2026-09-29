"""Unit tests for ERA5 collectors (no live Zenodo / GCS / CDS calls)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.collection.climate import era5_arco, era5_cds, era5_zenodo
from src.collection.climate.download_era5_data import extract as extract_orchestrated
from src.collection.climate.era5_cds import (
    BRAZIL_AREA,
    DEFAULT_VARIABLES,
    attempt_month,
    build_request,
    extract as extract_cds,
    iter_months,
    month_filename,
    write_manifest,
)


class FakeCds:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, str]] = []

    def retrieve(self, name: str, request: dict, target: str) -> None:
        self.calls.append((name, request, target))
        Path(target).write_bytes(b"CDF\x01fake-era5")


def test_month_filename():
    assert month_filename(2020, 3) == "era5_land_202003.nc"


def test_build_request_february_non_leap():
    req = build_request(2021, 2)
    assert req["year"] == "2021"
    assert req["month"] == "02"
    assert req["day"] == [f"{d:02d}" for d in range(1, 29)]
    assert req["variable"] == DEFAULT_VARIABLES
    assert req["area"] == BRAZIL_AREA
    assert len(req["time"]) == 24


def test_build_request_february_leap():
    assert build_request(2020, 2)["day"][-1] == "29"


def test_iter_months_full_year():
    months = iter_months(2019, 2019)
    assert len(months) == 12
    assert months[0] == (2019, 1)


def test_cds_attempt_month_skips_existing(tmp_path: Path):
    dest = tmp_path / "era5_land_202001.nc"
    dest.write_bytes(b"already-here")
    client = FakeCds()
    entry = attempt_month(client, 2020, 1, tmp_path)
    assert entry.status == "existing"
    assert client.calls == []


def test_cds_extract_writes_manifest(tmp_path: Path):
    result = extract_cds(
        out_dir=tmp_path, from_year=2020, to_year=2020, client=FakeCds(), delay=0.0
    )
    assert result.downloaded == 12
    assert result.failed == 0


def test_zenodo_uncovered_years():
    gaps = era5_zenodo.uncovered_years(2020, 2025)
    assert 2023 in gaps and 2024 in gaps
    assert 2020 not in gaps and 2025 not in gaps


def test_zenodo_records_for_years():
    recs = era5_zenodo.records_for_years(2020, 2025)
    ids = {r[0] for r in recs}
    assert 10036212 in ids
    assert 18257037 in ids
    assert era5_zenodo.records_for_years(2023, 2024) == []


def test_zenodo_extract_mocked(tmp_path: Path):
    class Sess:
        pass

    def fake_list(record_id: int, session) -> dict:
        return {
            "2m_temperature_mean.parquet": {
                "url": f"https://example.test/{record_id}/t.parquet",
                "size": 4,
                "checksum": "",
            }
        }

    # Patch download_file to avoid network.
    original = era5_zenodo.download_file

    def fake_download(url, destination, *, session, expected_size=0, expected_md5=""):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"data")
        return 4

    era5_zenodo.download_file = fake_download  # type: ignore[assignment]
    try:
        result = era5_zenodo.extract(
            out_dir=tmp_path,
            from_year=2020,
            to_year=2022,
            files=["2m_temperature_mean.parquet"],
            session=Sess(),  # type: ignore[arg-type]
            list_files_fn=fake_list,
        )
    finally:
        era5_zenodo.download_file = original  # type: ignore[assignment]

    assert result.downloaded == 1
    assert result.failed == 0
    assert (tmp_path / "zenodo" / "1950_2022" / "2m_temperature_mean.parquet").exists()


def test_arco_attempt_month_skips_existing(tmp_path: Path):
    dest = tmp_path / "arco" / "era5_arco_202301.nc"
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"x")
    entry = era5_arco.attempt_month(2023, 1, tmp_path, open_fn=lambda _: None)
    assert entry.status == "existing"


def test_orchestrator_zenodo_then_arco_gaps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def fake_zenodo(**kwargs):
        from src.common import ExtractResult

        man = kwargs["out_dir"] / "zenodo" / "manifest.csv"
        man.parent.mkdir(parents=True, exist_ok=True)
        man.write_text("backend,status\nzenodo,downloaded\n", encoding="utf-8")
        return ExtractResult(1, 0, 0, man, None)

    def fake_arco(**kwargs):
        from src.common import ExtractResult

        assert kwargs["years"] == [2023, 2024]
        man = kwargs["out_dir"] / "arco" / "manifest.csv"
        man.parent.mkdir(parents=True, exist_ok=True)
        man.write_text("backend,year,status\narco,2023,downloaded\n", encoding="utf-8")
        return ExtractResult(2, 0, 0, man, None)

    monkeypatch.setattr(era5_zenodo, "extract", fake_zenodo)
    monkeypatch.setattr(era5_arco, "extract", fake_arco)

    result = extract_orchestrated(
        out_dir=tmp_path,
        from_year=2020,
        to_year=2024,
        backends=["zenodo", "arco"],
    )
    assert result.downloaded == 3
    assert result.manifest_path.exists()


def test_write_manifest_failures(tmp_path: Path):
    from src.collection.climate.era5_cds import Entry

    entries = [
        Entry(year=2020, month=1, filename="a.nc", status="downloaded"),
        Entry(year=2020, month=2, filename="b.nc", status="failed", error="boom"),
    ]
    _manifest, failures = write_manifest(entries, tmp_path)
    assert "boom" in failures.read_text(encoding="utf-8")
