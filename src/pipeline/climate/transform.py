"""Orchestrate Zenodo + ARCO climate → UF × epidemiological-week features."""

from __future__ import annotations

import gzip
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

from .spec import (
    DEFAULT_RAINY_DAY_MM,
    OUTPUT_NAME,
    SOURCE_ARCO,
    SOURCE_ZENODO,
)
from .steps import (
    build_arco_month,
    build_zenodo_coverage,
    load_municipalities,
    nearest_grid_indices,
)

log = logging.getLogger("pipeline.climate")

FORMAT_PARQUET = "parquet"
FORMAT_CSV_GZ = "csv_gz"
DEFAULT_FORMATS = (FORMAT_PARQUET, FORMAT_CSV_GZ)

_ARCO_RE = re.compile(r"era5_arco_(\d{4})(\d{2})\.nc")


@dataclass
class ClimateTransformResult:
    """Outcome of one climate transformation run."""

    sources: list[str] = field(default_factory=list)
    years: list[int] = field(default_factory=list)
    rows_out: int = 0
    failed: int = 0
    outputs: list[Path] = field(default_factory=list)
    elapsed: float = 0.0

    def __str__(self) -> str:
        parts = [
            f"sources={','.join(self.sources) or '-'}",
            f"years={len(self.years)}",
            f"rows={self.rows_out:,}",
            f"failed={self.failed}",
            f"elapsed={self.elapsed:.1f}s",
        ]
        if self.outputs:
            parts.append(f"outputs={', '.join(p.name for p in self.outputs)}")
        return f"ClimateTransformResult({', '.join(parts)})"


def discover_zenodo_coverages(era5_dir: Path) -> list[Path]:
    zenodo = era5_dir / "zenodo"
    if not zenodo.is_dir():
        return []
    return sorted(
        path for path in zenodo.iterdir()
        if path.is_dir() and any(path.glob("*.parquet"))
    )


def discover_arco_files(
    era5_dir: Path, from_year: int | None, to_year: int | None
) -> list[tuple[int, Path]]:
    arco = era5_dir / "arco"
    if not arco.is_dir():
        return []
    found: list[tuple[int, Path]] = []
    for path in sorted(arco.glob("era5_arco_*.nc")):
        match = _ARCO_RE.fullmatch(path.name)
        if match is None:
            continue
        year = int(match.group(1))
        if from_year is not None and year < from_year:
            continue
        if to_year is not None and year > to_year:
            continue
        found.append((year, path))
    return found


def transform(
    era5_dir: Path,
    out_dir: Path,
    municipalities_path: Path,
    from_year: int | None = None,
    to_year: int | None = None,
    backends: list[str] | tuple[str, ...] = (SOURCE_ZENODO, SOURCE_ARCO),
    rainy_day_mm: float = DEFAULT_RAINY_DAY_MM,
    formats: tuple[str, ...] | list[str] = DEFAULT_FORMATS,
) -> ClimateTransformResult:
    """Build the UF×EW climate feature table from downloaded ERA5 products."""
    started = time.monotonic()
    result = ClimateTransformResult()
    backends_set = {b.lower() for b in backends}

    municipalities_lf = load_municipalities(municipalities_path)
    municipalities_df = municipalities_lf.collect()

    pieces: list[pl.DataFrame] = []

    if SOURCE_ZENODO in backends_set:
        coverages = discover_zenodo_coverages(era5_dir)
        if not coverages:
            log.warning("No Zenodo coverage folders under %s/zenodo", era5_dir)
        for coverage_dir in coverages:
            log.info("zenodo: aggregating %s", coverage_dir.name)
            # Year-chunk to keep peak memory bounded on the ~3 GB historical files.
            years = _years_for_coverage(coverage_dir, from_year, to_year)
            if not years:
                continue
            for year in years:
                try:
                    frame = build_zenodo_coverage(
                        coverage_dir,
                        municipalities_lf,
                        SOURCE_ZENODO,
                        from_year=year,
                        to_year=year,
                        rainy_day_mm=rainy_day_mm,
                    ).collect(engine="streaming")
                except Exception as error:
                    log.error("zenodo %s year %d failed: %s", coverage_dir.name, year, error)
                    result.failed += 1
                    continue
                if frame.height == 0:
                    continue
                log.info("zenodo %s %d -> %d rows", coverage_dir.name, year, frame.height)
                pieces.append(frame)
                if year not in result.years:
                    result.years.append(year)
            if SOURCE_ZENODO not in result.sources and years:
                result.sources.append(SOURCE_ZENODO)

    if SOURCE_ARCO in backends_set:
        arco_files = discover_arco_files(era5_dir, from_year, to_year)
        if not arco_files:
            log.warning("No ARCO NetCDF files under %s/arco", era5_dir)
        else:
            lat_idx, lon_idx = _arco_muni_indices(arco_files[0][1], municipalities_df)
            for year, path in arco_files:
                log.info("arco: aggregating %s", path.name)
                try:
                    frame = build_arco_month(
                        path,
                        municipalities_df,
                        lat_idx,
                        lon_idx,
                        municipalities_lf,
                        SOURCE_ARCO,
                        rainy_day_mm=rainy_day_mm,
                    ).collect()
                except Exception as error:
                    log.error("arco %s failed: %s", path.name, error)
                    result.failed += 1
                    continue
                if frame.height == 0:
                    continue
                log.info("arco %s -> %d rows", path.name, frame.height)
                pieces.append(frame)
                if year not in result.years:
                    result.years.append(year)
            if SOURCE_ARCO not in result.sources and arco_files:
                result.sources.append(SOURCE_ARCO)

    if not pieces:
        raise FileNotFoundError(
            f"No climate inputs found under {era5_dir} for backends={sorted(backends_set)}. "
            f"Run `arboili era5` first, or check pipeline.climate.from_year/to_year."
        )

    # Weeks that straddle month/coverage boundaries can appear twice — re-aggregate
    # is not needed for pop-weighted means from disjoint days, but ARCO months and
    # Zenodo years should not overlap by design. Concatenate and drop exact dups.
    series = (
        pl.concat(pieces, how="vertical")
        .unique(subset=["ew", "state_abbrev", "source"], keep="first")
        .sort("source", "state_abbrev", "ew")
    )

    result.years = sorted(result.years)
    result.rows_out = series.height
    result.outputs = _write(series, out_dir, formats)
    result.elapsed = time.monotonic() - started
    log.info(
        "climate: %d rows, sources=%s, years=%s–%s",
        series.height,
        result.sources,
        result.years[0] if result.years else None,
        result.years[-1] if result.years else None,
    )
    return result


_COVERAGE_RE = re.compile(r"^(?P<lo>\d{4})(?:_(?P<hi>\d{4}))?$")


def _years_for_coverage(
    coverage_dir: Path, from_year: int | None, to_year: int | None
) -> list[int]:
    """Year span from the Zenodo coverage folder name (`1950_2022`, `2025`).

    Falls back to scanning dates only when the folder name is not parseable.
    """
    match = _COVERAGE_RE.fullmatch(coverage_dir.name)
    if match:
        lo = int(match.group("lo"))
        hi = int(match.group("hi") or lo)
    else:
        sample = next(coverage_dir.glob("2m_temperature_mean.parquet"), None)
        if sample is None:
            sample = next(coverage_dir.glob("*.parquet"), None)
        if sample is None:
            return []
        bounds = (
            pl.scan_parquet(sample)
            .select(
                pl.col("date").dt.year().min().alias("lo"),
                pl.col("date").dt.year().max().alias("hi"),
            )
            .collect()
            .row(0)
        )
        lo, hi = int(bounds[0]), int(bounds[1])

    if from_year is not None:
        lo = max(lo, from_year)
    if to_year is not None:
        hi = min(hi, to_year)
    if lo > hi:
        return []
    return list(range(lo, hi + 1))


def _arco_muni_indices(
    sample_nc: Path, municipalities: pl.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    import xarray as xr

    ds = xr.open_dataset(sample_nc)
    try:
        return nearest_grid_indices(
            municipalities["lat"].to_numpy(),
            municipalities["lon"].to_numpy(),
            np.asarray(ds["latitude"].values),
            np.asarray(ds["longitude"].values),
        )
    finally:
        ds.close()


def _write(
    series: pl.DataFrame, out_dir: Path, formats: tuple[str, ...] | list[str]
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        if fmt == FORMAT_PARQUET:
            path = out_dir / f"{OUTPUT_NAME}.parquet"
            series.write_parquet(path, compression="zstd")
        elif fmt == FORMAT_CSV_GZ:
            path = out_dir / f"{OUTPUT_NAME}.csv.gz"
            with gzip.open(path, "wb", compresslevel=6) as handle:
                series.write_csv(handle)
        else:
            raise ValueError(f"Unknown output format {fmt!r}; expected {DEFAULT_FORMATS}")
        log.info("wrote %s (%.1f MB)", path, path.stat().st_size / 1e6)
        written.append(path)
    return written
