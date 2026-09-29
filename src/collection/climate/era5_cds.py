"""
Last-resort ERA5-Land download via Copernicus CDS (``cdsapi``).

Prefer the orchestrator in ``download_era5_data`` (Zenodo → ARCO → CDS).
Use this module directly only when cloud mirrors are unavailable.

Requires ``~/.cdsapirc`` and acceptance of the ERA5-Land licence on the CDS site.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ...common import ExtractResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

DATASET = "reanalysis-era5-land"
DEFAULT_OUT_DIR = DATA_DIR / "climate" / "era5" / "cds"
FIRST_YEAR = 2000

# N, W, S, E — continental Brazil plus a small buffer.
BRAZIL_AREA = [5.5, -74.0, -34.0, -34.0]

# Core variables for dengue climate features (temp, RH via dewpoint, precip, pressure).
DEFAULT_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "total_precipitation",
    "surface_pressure",
]

# 0.25° keeps monthly files tractable while remaining fine enough for UF aggregates.
DEFAULT_GRID = [0.25, 0.25]

HOURS = [f"{h:02d}:00" for h in range(24)]
DAYS = [f"{d:02d}" for d in range(1, 32)]

MANIFEST_FILENAME = "manifest.csv"
FAILURES_FILENAME = "failures.csv"

STATUS_DOWNLOADED = "downloaded"
STATUS_EXISTING = "existing"
STATUS_FAILED = "failed"

log = logging.getLogger("era5.cds")


class CdsClient(Protocol):
    """Minimal surface of ``cdsapi.Client`` used here (also for tests)."""

    def retrieve(self, name: str, request: dict[str, Any], target: str) -> Any: ...


@dataclass
class Entry:
    year: int
    month: int
    filename: str = ""
    dataset: str = DATASET
    status: str = ""
    error: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


def month_filename(year: int, month: int) -> str:
    return f"era5_land_{year}{month:02d}.nc"


def build_request(
    year: int,
    month: int,
    *,
    variables: list[str] | None = None,
    area: list[float] | None = None,
    grid: list[float] | None = None,
) -> dict[str, Any]:
    """CDS request body for one calendar month of hourly ERA5-Land over Brazil."""
    request: dict[str, Any] = {
        "variable": list(variables or DEFAULT_VARIABLES),
        "year": str(year),
        "month": f"{month:02d}",
        "day": DAYS[: calendar.monthrange(year, month)[1]],
        "time": HOURS,
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": list(area or BRAZIL_AREA),
    }
    if grid is not None:
        request["grid"] = list(grid)
    return request


def iter_months(from_year: int, to_year: int) -> list[tuple[int, int]]:
    now = datetime.now()
    months: list[tuple[int, int]] = []
    for year in range(from_year, to_year + 1):
        last_month = 12 if year < now.year else now.month
        for month in range(1, last_month + 1):
            months.append((year, month))
    return months


def make_client() -> CdsClient:
    try:
        import cdsapi
    except ImportError as exc:
        raise RuntimeError(
            "cdsapi is not installed. Run `uv sync` (or `uv add cdsapi`)."
        ) from exc
    return cdsapi.Client()


def attempt_month(
    client: CdsClient,
    year: int,
    month: int,
    output_dir: Path,
    *,
    variables: list[str] | None = None,
    area: list[float] | None = None,
    grid: list[float] | None = None,
    dataset: str = DATASET,
) -> Entry:
    filename = month_filename(year, month)
    entry = Entry(year=year, month=month, filename=filename, dataset=dataset)
    destination = output_dir / filename

    if destination.exists() and destination.stat().st_size > 0:
        entry.status = STATUS_EXISTING
        log.info("skipping %s (already on disk)", filename)
        return entry

    # CDS sometimes returns a .zip even when netcdf is requested; accept either
    # the target name or a sibling .zip produced by the client.
    zip_destination = destination.with_suffix(".zip")
    if zip_destination.exists() and zip_destination.stat().st_size > 0:
        entry.filename = zip_destination.name
        entry.status = STATUS_EXISTING
        log.info("skipping %s (already on disk)", zip_destination.name)
        return entry

    request = build_request(year, month, variables=variables, area=area, grid=grid)
    tmp = destination.with_suffix(destination.suffix + ".part")
    try:
        log.info("requesting %s %04d-%02d (%s)", dataset, year, month, filename)
        output_dir.mkdir(parents=True, exist_ok=True)
        if tmp.exists():
            tmp.unlink()
        client.retrieve(dataset, request, str(tmp))
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError("CDS retrieve finished but wrote an empty file")
        # Prefer .nc; if the client wrote a zip under the .part name, rename accordingly.
        final = destination
        if tmp.read_bytes()[:2] == b"PK":
            final = zip_destination
            entry.filename = final.name
        tmp.rename(final)
        entry.status = STATUS_DOWNLOADED
        log.info("saved %s (%d bytes)", final, final.stat().st_size)
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        entry.status = STATUS_FAILED
        entry.error = str(exc)
        log.warning("FAILED %04d-%02d — %s", year, month, exc)

    return entry


_FIELDS = ["year", "month", "filename", "dataset", "status", "error", "timestamp"]


def write_manifest(entries: list[Entry], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_FILENAME
    failures_path = output_dir / FAILURES_FILENAME

    rows = [asdict(e) for e in entries]
    failed_rows = [r for r in rows if r["status"] == STATUS_FAILED]

    for path, data in ((manifest_path, rows), (failures_path, failed_rows)):
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDS)
            writer.writeheader()
            writer.writerows(data)

    return manifest_path, failures_path


def extract(
    out_dir: Path = DEFAULT_OUT_DIR,
    from_year: int = FIRST_YEAR,
    to_year: int | None = None,
    *,
    variables: list[str] | None = None,
    area: list[float] | None = None,
    grid: list[float] | None = None,
    dataset: str = DATASET,
    client: CdsClient | None = None,
    delay: float = 1.0,
) -> ExtractResult:
    """Download monthly ERA5-Land files for ``[from_year, to_year]``.

    Pass a mock ``client`` in tests. Without one, builds a real ``cdsapi.Client``.
    """
    if to_year is None:
        to_year = datetime.now().year
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cds = client if client is not None else make_client()
    entries: list[Entry] = []

    for year, month in iter_months(from_year, to_year):
        entry = attempt_month(
            cds,
            year,
            month,
            out_dir,
            variables=variables,
            area=area,
            grid=grid if grid is not None else DEFAULT_GRID,
            dataset=dataset,
        )
        entries.append(entry)
        if entry.status == STATUS_DOWNLOADED and delay > 0:
            time.sleep(delay)

    manifest_path, failures_path = write_manifest(entries, out_dir)
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUT_DIR,
        help=f"Where to save NetCDF/ZIP files (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument("--from-year", type=int, default=FIRST_YEAR)
    parser.add_argument("--to-year", type=int, default=datetime.now().year)
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args()
    result = extract(
        out_dir=args.output_dir,
        from_year=args.from_year,
        to_year=args.to_year,
    )
    log.info("%s", result)
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
