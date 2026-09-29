"""
Climate collection orchestrator — fastest path first, with fallbacks.

Order (default):
  1. **Zenodo** — HTTP bulk ERA5-Land municipality daily parquets (no key, no queue)
  2. **ARCO**  — Google public ERA5 Zarr for years Zenodo misses (2023–2024, …)
  3. **CDS**   — Copernicus ``cdsapi`` last resort (slow queue; needs ~/.cdsapirc)

    uv run arboili era5
    uv run arboili era5 --from-year 2020 --to-year 2024
    uv run arboili era5 --backends zenodo          # primary only
    uv run arboili era5 --backends zenodo,arco,cds # force CDS as third

Layout::

    data/climate/era5/
      zenodo/1950_2022/*.parquet
      zenodo/2025/*.parquet
      arco/era5_arco_YYYYMM.nc
      cds/era5_land_YYYYMM.nc      # only if cds backend enabled
      manifest.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ...common import ExtractResult
from . import era5_arco, era5_zenodo

log = logging.getLogger("era5")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "climate" / "era5"
DEFAULT_BACKENDS = ("zenodo", "arco")
ALL_BACKENDS = ("zenodo", "arco", "cds")


@dataclass
class _Sum:
    downloaded: int = 0
    existing: int = 0
    failed: int = 0

    def add(self, result: ExtractResult) -> None:
        self.downloaded += result.downloaded
        self.existing += result.existing
        self.failed += result.failed


def _write_combined_manifest(
    out_dir: Path,
    *,
    zenodo_result: ExtractResult | None,
    arco_result: ExtractResult | None,
    cds_result: ExtractResult | None,
    gap_years: list[int],
) -> Path:
    path = out_dir / "manifest.csv"
    rows: list[dict[str, str]] = []

    def _absorb(label: str, result: ExtractResult | None) -> None:
        if result is None or not result.manifest_path.exists():
            return
        with result.manifest_path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                row = dict(row)
                row.setdefault("backend", label)
                rows.append(row)

    _absorb("zenodo", zenodo_result)
    _absorb("arco", arco_result)
    _absorb("cds", cds_result)
    for year in gap_years:
        # Document intentional hand-off even when ARCO was not requested.
        if not any(r.get("backend") == "arco" and r.get("year") == str(year) for r in rows):
            rows.append({
                "backend": "gap",
                "year": str(year),
                "status": "uncovered",
                "error": "no Zenodo coverage; enable arco (default) or cds",
            })

    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames or ["backend", "status"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def extract(
    out_dir: Path = DEFAULT_OUT_DIR,
    from_year: int = 2000,
    to_year: int | None = None,
    *,
    backends: list[str] | tuple[str, ...] | None = None,
    zenodo_files: list[str] | None = None,
    area: list[float] | None = None,
    variables: list[str] | None = None,
    # CDS-only knobs (ignored unless "cds" in backends)
    grid: list[float] | None = None,
    dataset: str | None = None,
    delay: float = 1.0,
    cds_client: object | None = None,
) -> ExtractResult:
    """Run Zenodo → ARCO → (optional) CDS and merge counts + manifests."""
    if to_year is None:
        to_year = datetime.now().year
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    chosen = tuple(backends or DEFAULT_BACKENDS)
    unknown = [b for b in chosen if b not in ALL_BACKENDS]
    if unknown:
        raise ValueError(f"unknown era5 backends {unknown}; choose from {ALL_BACKENDS}")

    totals = _Sum()
    zenodo_result: ExtractResult | None = None
    arco_result: ExtractResult | None = None
    cds_result: ExtractResult | None = None

    gap_years = era5_zenodo.uncovered_years(from_year, to_year)
    log.info(
        "ERA5 plan: years %d–%d | backends=%s | Zenodo gaps=%s",
        from_year, to_year, ",".join(chosen), gap_years or "none",
    )

    if "zenodo" in chosen:
        log.info("── backend: zenodo (primary, HTTP bulk) ──")
        zenodo_result = era5_zenodo.extract(
            out_dir=out_dir,
            from_year=from_year,
            to_year=to_year,
            files=zenodo_files,
        )
        totals.add(zenodo_result)
        log.info("zenodo → %s", zenodo_result)

    if "arco" in chosen and gap_years:
        log.info("── backend: arco (fallback for %s) ──", gap_years)
        arco_result = era5_arco.extract(
            out_dir=out_dir,
            years=gap_years,
            variables=variables or era5_arco.DEFAULT_VARIABLES,
            area=area or era5_arco.BRAZIL_AREA,
        )
        totals.add(arco_result)
        log.info("arco → %s", arco_result)
    elif "arco" in chosen:
        log.info("arco skipped — Zenodo already covers %d–%d", from_year, to_year)

    # CDS: full range if it is the only backend; otherwise only Zenodo gap years.
    if "cds" in chosen:
        from . import era5_cds

        only_cds = chosen == ("cds",)
        cds_years = list(range(from_year, to_year + 1)) if only_cds else list(gap_years)
        if not cds_years:
            log.info("cds skipped — no gap years left for last-resort fill")
        else:
            log.info("── backend: cds (last resort for %s) ──", cds_years)
            cds_result = era5_cds.extract(
                out_dir=out_dir / "cds",
                from_year=min(cds_years),
                to_year=max(cds_years),
                variables=variables,
                area=area,
                grid=grid,
                dataset=dataset or era5_cds.DATASET,
                client=cds_client,  # type: ignore[arg-type]
                delay=delay,
            )
            totals.add(cds_result)
            log.info("cds → %s", cds_result)

    combined = _write_combined_manifest(
        out_dir,
        zenodo_result=zenodo_result,
        arco_result=arco_result,
        cds_result=cds_result,
        gap_years=gap_years if "arco" not in chosen else [],
    )
    return ExtractResult(
        downloaded=totals.downloaded,
        existing=totals.existing,
        failed=totals.failed,
        manifest_path=combined,
        failures_path=out_dir / "zenodo" / "failures.csv",
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--from-year", type=int, default=2000)
    p.add_argument("--to-year", type=int, default=datetime.now().year)
    p.add_argument(
        "--backends",
        default=",".join(DEFAULT_BACKENDS),
        help="Comma-separated: zenodo,arco,cds (default: zenodo,arco)",
    )
    return p.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args()
    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    result = extract(
        out_dir=args.output_dir,
        from_year=args.from_year,
        to_year=args.to_year,
        backends=backends,
    )
    log.info("%s", result)
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
