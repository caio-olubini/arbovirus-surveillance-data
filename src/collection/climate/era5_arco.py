"""
Fallback climate fetch: Google ARCO-ERA5 (public GCS Zarr, anonymous).

No CDS account, no queue. Covers years Zenodo does not (notably 2023–2024).
Product is ERA5 at 0.25° (not ERA5-Land 0.1°) — fine for UF aggregates.

Writes one daily-aggregated NetCDF per month under ``out_dir/arco/``.
"""

from __future__ import annotations

import calendar
import csv
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ...common import ExtractResult

log = logging.getLogger("era5.arco")

DEFAULT_ZARR = (
    "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
)

# N, W, S, E — continental Brazil
BRAZIL_AREA = [5.5, -74.0, -34.0, -34.0]

DEFAULT_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "total_precipitation",
    "surface_pressure",
]

MANIFEST_FILENAME = "manifest.csv"
FAILURES_FILENAME = "failures.csv"
STATUS_DOWNLOADED = "downloaded"
STATUS_EXISTING = "existing"
STATUS_FAILED = "failed"


@dataclass
class Entry:
    backend: str = "arco"
    year: int = 0
    month: int = 0
    filename: str = ""
    status: str = ""
    error: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


_FIELDS = ["backend", "year", "month", "filename", "status", "error", "timestamp"]


def month_filename(year: int, month: int) -> str:
    return f"era5_arco_{year}{month:02d}.nc"


def _lon_slice(west: float, east: float, lon_min: float, lon_max: float) -> slice:
    """ARCO longitudes are usually 0–360; accept either convention."""
    if lon_min >= 0 and west < 0:
        return slice(west % 360, east % 360)
    return slice(west, east)


def open_arco_dataset(zarr_path: str = DEFAULT_ZARR) -> Any:
    import xarray as xr

    return xr.open_zarr(zarr_path, consolidated=True, storage_options={"token": "anon"})


def export_month(
    ds: Any,
    year: int,
    month: int,
    destination: Path,
    *,
    variables: list[str],
    area: list[float],
) -> None:
    """Subset Brazil × month, aggregate hour→day, write NetCDF."""
    north, west, south, east = area
    last_day = calendar.monthrange(year, month)[1]
    t0 = f"{year:04d}-{month:02d}-01"
    t1 = f"{year:04d}-{month:02d}-{last_day:02d}"

    missing = [v for v in variables if v not in ds.data_vars]
    if missing:
        raise KeyError(f"variables not in ARCO store: {missing}")

    lon = ds["longitude"]
    lon_sl = _lon_slice(west, east, float(lon.min()), float(lon.max()))
    # Latitude in ARCO decreases north→south.
    lat_sl = slice(north, south)

    subset = ds[variables].sel(time=slice(t0, t1), latitude=lat_sl, longitude=lon_sl)
    if subset.sizes.get("time", 0) == 0:
        raise RuntimeError(f"no ARCO timesteps for {year}-{month:02d}")

    pieces = []
    for name in variables:
        da = subset[name]
        if name == "total_precipitation":
            daily = da.resample(time="1D").sum(keep_attrs=True)
        else:
            daily = da.resample(time="1D").mean(keep_attrs=True)
        pieces.append(daily.to_dataset(name=name))

    import xarray as xr

    out = xr.merge(pieces)
    out.attrs["source"] = "ARCO-ERA5 (gcp-public-data-arco-era5)"
    out.attrs["note"] = (
        "Daily aggregates over Brazil; precip=sum, others=mean. "
        "ERA5 0.25°, not ERA5-Land."
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    out.to_netcdf(tmp)
    tmp.replace(destination)


def attempt_month(
    year: int,
    month: int,
    out_dir: Path,
    *,
    ds: Any | None = None,
    zarr_path: str = DEFAULT_ZARR,
    variables: list[str] | None = None,
    area: list[float] | None = None,
    open_fn: Callable[[str], Any] | None = None,
) -> Entry:
    filename = month_filename(year, month)
    rel = f"arco/{filename}"
    dest = out_dir / "arco" / filename
    entry = Entry(year=year, month=month, filename=rel)

    if dest.exists() and dest.stat().st_size > 0:
        entry.status = STATUS_EXISTING
        log.info("skipping %s (already on disk)", rel)
        return entry

    try:
        dataset = ds
        if dataset is None:
            opener = open_fn or open_arco_dataset
            dataset = opener(zarr_path)
        export_month(
            dataset,
            year,
            month,
            dest,
            variables=variables or DEFAULT_VARIABLES,
            area=area or BRAZIL_AREA,
        )
        entry.status = STATUS_DOWNLOADED
        log.info("saved %s", rel)
    except Exception as exc:
        entry.status = STATUS_FAILED
        entry.error = str(exc)
        log.warning("FAILED %04d-%02d — %s", year, month, exc)
    return entry


def write_manifest(entries: list[Entry], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_FILENAME
    failures_path = output_dir / FAILURES_FILENAME
    rows = [asdict(e) for e in entries]
    failed = [r for r in rows if r["status"] == STATUS_FAILED]
    for path, data in ((manifest_path, rows), (failures_path, failed)):
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            writer.writeheader()
            writer.writerows(data)
    return manifest_path, failures_path


def extract(
    out_dir: Path,
    years: list[int],
    *,
    variables: list[str] | None = None,
    area: list[float] | None = None,
    zarr_path: str = DEFAULT_ZARR,
    open_fn: Callable[[str], Any] | None = None,
    ds: Any | None = None,
) -> ExtractResult:
    """Download ARCO daily-aggregated months for each year in ``years``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not years:
        manifest, failures = write_manifest([], out_dir / "arco")
        return ExtractResult(0, 0, 0, manifest, failures)

    now = datetime.now()
    dataset = ds
    if dataset is None and open_fn is None:
        log.info("opening ARCO Zarr (anonymous GCS)…")
        dataset = open_arco_dataset(zarr_path)

    entries: list[Entry] = []
    for year in sorted(years):
        last_month = 12 if year < now.year else now.month
        for month in range(1, last_month + 1):
            entries.append(
                attempt_month(
                    year,
                    month,
                    out_dir,
                    ds=dataset,
                    zarr_path=zarr_path,
                    variables=variables,
                    area=area,
                    open_fn=open_fn,
                )
            )

    manifest_path, failures_path = write_manifest(entries, out_dir / "arco")
    counts = {STATUS_DOWNLOADED: 0, STATUS_EXISTING: 0, STATUS_FAILED: 0}
    for e in entries:
        counts[e.status] = counts.get(e.status, 0) + 1
    return ExtractResult(
        downloaded=counts[STATUS_DOWNLOADED],
        existing=counts[STATUS_EXISTING],
        failed=counts[STATUS_FAILED],
        manifest_path=manifest_path,
        failures_path=failures_path,
    )
