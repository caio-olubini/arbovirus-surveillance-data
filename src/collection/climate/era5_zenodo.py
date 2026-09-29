"""
Primary climate fetch: Zenodo ERA5-Land zonal stats for Brazilian municipalities.

HTTP bulk download — no CDS queue, no API key. Files are already daily
municipality aggregates (ready for a later EW×UF transform).

Records:
  - 10.5281/zenodo.10036212 — 1950–2022 (~3 GB/file)
  - 10.5281/zenodo.18257037 — 2025 (~35 MB/file)

Gap years 2023–2024 (and anything after the latest Zenodo cut) are left to
the ARCO fallback in ``download_era5_data``.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

from ...common import ExtractResult

log = logging.getLogger("era5.zenodo")

ZENODO_API = "https://zenodo.org/api/records"

# Dengue-relevant variables only (skip wind to save ~6 GB on the historical set).
DEFAULT_FILES = [
    "2m_temperature_mean.parquet",
    "2m_temperature_min.parquet",
    "2m_temperature_max.parquet",
    "2m_dewpoint_temperature_mean.parquet",
    "total_precipitation_sum.parquet",
    "surface_pressure_mean.parquet",
]

# (record_id, coverage_label, year_start, year_end)
DEFAULT_RECORDS: list[tuple[int, str, int, int]] = [
    (10036212, "1950_2022", 1950, 2022),
    (18257037, "2025", 2025, 2025),
]

MANIFEST_FILENAME = "manifest.csv"
FAILURES_FILENAME = "failures.csv"
STATUS_DOWNLOADED = "downloaded"
STATUS_EXISTING = "existing"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

CHUNK = 8 * 1024 * 1024
MAX_RETRIES = 3


@dataclass
class Entry:
    backend: str = "zenodo"
    record_id: int = 0
    coverage: str = ""
    filename: str = ""
    url: str = ""
    status: str = ""
    error: str = ""
    bytes: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


_FIELDS = [
    "backend", "record_id", "coverage", "filename", "url",
    "status", "error", "bytes", "timestamp",
]


def records_for_years(
    from_year: int,
    to_year: int,
    records: list[tuple[int, str, int, int]] | None = None,
) -> list[tuple[int, str, int, int]]:
    """Return Zenodo records that overlap ``[from_year, to_year]``."""
    chosen = []
    for rec in records or DEFAULT_RECORDS:
        _id, label, start, end = rec
        if end < from_year or start > to_year:
            continue
        chosen.append(rec)
    return chosen


def uncovered_years(
    from_year: int,
    to_year: int,
    records: list[tuple[int, str, int, int]] | None = None,
) -> list[int]:
    """Calendar years in range that no Zenodo record covers (→ ARCO gap)."""
    covered: set[int] = set()
    for _id, _label, start, end in records or DEFAULT_RECORDS:
        covered.update(range(start, end + 1))
    return [y for y in range(from_year, to_year + 1) if y not in covered]


def list_record_files(record_id: int, session: requests.Session | None = None) -> dict[str, dict]:
    """Map filename → {url, size, checksum} for one Zenodo record."""
    sess = session or requests.Session()
    resp = sess.get(f"{ZENODO_API}/{record_id}", timeout=60)
    resp.raise_for_status()
    out: dict[str, dict] = {}
    for f in resp.json().get("files", []):
        out[f["key"]] = {
            "url": f["links"]["self"],
            "size": int(f.get("size") or 0),
            "checksum": f.get("checksum") or "",
        }
    return out


def _md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(
    url: str,
    destination: Path,
    *,
    session: requests.Session,
    expected_size: int = 0,
    expected_md5: str = "",
) -> int:
    """Stream ``url`` to ``destination``; return bytes written. Resumable via .part."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with session.get(url, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as out:
                    for chunk in resp.iter_content(CHUNK):
                        if chunk:
                            out.write(chunk)
            size = tmp.stat().st_size
            if expected_size and size != expected_size:
                raise RuntimeError(
                    f"size mismatch for {destination.name}: got {size}, expected {expected_size}"
                )
            if expected_md5.startswith("md5:"):
                digest = expected_md5.split(":", 1)[1]
                if _md5_file(tmp) != digest:
                    raise RuntimeError(f"md5 mismatch for {destination.name}")
            tmp.replace(destination)
            return size
        except Exception as exc:
            last_error = exc
            log.warning("attempt %d/%d failed for %s (%s)", attempt, MAX_RETRIES, url, exc)
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            time.sleep(2 * attempt)
    raise RuntimeError(f"giving up on {url}") from last_error


def attempt_file(
    record_id: int,
    coverage: str,
    filename: str,
    meta: dict,
    out_dir: Path,
    session: requests.Session,
) -> Entry:
    dest = out_dir / "zenodo" / coverage / filename
    entry = Entry(
        record_id=record_id,
        coverage=coverage,
        filename=str(dest.relative_to(out_dir)) if dest.exists() or True else filename,
        url=meta["url"],
    )
    entry.filename = f"zenodo/{coverage}/{filename}"

    if dest.exists() and dest.stat().st_size > 0:
        if meta.get("size") and dest.stat().st_size == meta["size"]:
            entry.status = STATUS_EXISTING
            entry.bytes = dest.stat().st_size
            log.info("skipping %s (already on disk)", entry.filename)
            return entry

    try:
        log.info("downloading %s", entry.filename)
        size = download_file(
            meta["url"],
            dest,
            session=session,
            expected_size=int(meta.get("size") or 0),
            expected_md5=str(meta.get("checksum") or ""),
        )
        entry.status = STATUS_DOWNLOADED
        entry.bytes = size
        log.info("saved %s (%d bytes)", entry.filename, size)
    except Exception as exc:
        entry.status = STATUS_FAILED
        entry.error = str(exc)
        log.warning("FAILED %s — %s", entry.filename, exc)
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
    from_year: int = 2000,
    to_year: int | None = None,
    *,
    files: list[str] | None = None,
    records: list[tuple[int, str, int, int]] | None = None,
    session: requests.Session | None = None,
    list_files_fn: Callable[[int, requests.Session], dict[str, dict]] | None = None,
) -> ExtractResult:
    if to_year is None:
        to_year = datetime.now().year
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = files or DEFAULT_FILES
    sess = session or requests.Session()
    list_fn = list_files_fn or list_record_files

    entries: list[Entry] = []
    chosen = records_for_years(from_year, to_year, records)
    if not chosen:
        log.warning("no Zenodo records overlap %d–%d", from_year, to_year)

    for record_id, coverage, _start, _end in chosen:
        try:
            available = list_fn(record_id, sess)
        except Exception as exc:
            for name in wanted:
                entries.append(Entry(
                    record_id=record_id, coverage=coverage, filename=name,
                    status=STATUS_FAILED, error=f"list files: {exc}",
                ))
            continue

        for name in wanted:
            if name not in available:
                entries.append(Entry(
                    record_id=record_id, coverage=coverage, filename=name,
                    status=STATUS_FAILED, error="file not in Zenodo record",
                ))
                continue
            entries.append(
                attempt_file(record_id, coverage, name, available[name], out_dir, sess)
            )

    # Annotate gap years so the orchestrator / manifest document the hand-off.
    for year in uncovered_years(from_year, to_year, records):
        entries.append(Entry(
            coverage="gap",
            filename=f"(year {year})",
            status=STATUS_SKIPPED,
            error="no Zenodo coverage — deferred to ARCO fallback",
        ))

    manifest_path, failures_path = write_manifest(entries, out_dir / "zenodo")
    counts = {STATUS_DOWNLOADED: 0, STATUS_EXISTING: 0, STATUS_FAILED: 0}
    for e in entries:
        if e.status in counts:
            counts[e.status] += 1
    return ExtractResult(
        downloaded=counts[STATUS_DOWNLOADED],
        existing=counts[STATUS_EXISTING],
        failed=counts[STATUS_FAILED],
        manifest_path=manifest_path,
        failures_path=failures_path,
    )
