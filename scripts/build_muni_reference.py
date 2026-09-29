"""Build data/climate/br_municipalities.csv from IBGE pop + municipality centroids.

One-off helper — not part of the runtime pipeline. Requires xlrd to read the
IBGE .xls (``uv run --with xlrd python scripts/build_muni_reference.py``).

Sources:
  - IBGE Estimativas 2024 (POP2024_*.xls), sheet MUNICÍPIOS
  - kelvins/Municipios-Brasileiros centroids (codigo_ibge, lat, lon)
  - data/epidemiological/br_federative_units.csv for state_code join
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
POP_XLS = Path("/tmp/arboili_ref/POP2024.xls")
COORDS_CSV = Path("/tmp/arboili_ref/municipios.csv")
FU_CSV = ROOT / "data/epidemiological/br_federative_units.csv"
OUT = ROOT / "data/climate/br_municipalities.csv"


def parse_pop(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else None


def main() -> None:
    raw = pd.read_excel(POP_XLS, sheet_name="MUNICÍPIOS", header=None)
    body = raw.iloc[2:].copy()
    body.columns = ["uf", "cod_uf", "cod_munic", "name", "population", "x"]
    body = body.dropna(subset=["cod_uf", "cod_munic", "population"])
    body["population"] = body["population"].map(parse_pop)
    body["cod_uf"] = body["cod_uf"].astype(int).astype(str).str.zfill(2)
    body["cod_munic"] = (
        body["cod_munic"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(5)
    )
    body["code_muni"] = (body["cod_uf"] + body["cod_munic"]).astype(int)
    body["state_abbrev"] = body["uf"].astype(str).str.strip()

    pop = pl.DataFrame(
        {
            "code_muni": body["code_muni"].tolist(),
            "state_abbrev": body["state_abbrev"].tolist(),
            "muni_name": body["name"].astype(str).tolist(),
            "population": body["population"].tolist(),
        }
    ).drop_nulls(subset=["population"])

    coords = pl.read_csv(COORDS_CSV).select(
        pl.col("codigo_ibge").alias("code_muni"),
        pl.col("latitude").alias("lat"),
        pl.col("longitude").alias("lon"),
    )
    fu = pl.read_csv(FU_CSV).select(
        pl.col("ABBREVIATION").alias("state_abbrev"),
        pl.col("CODE").cast(pl.Int16).alias("state_code"),
    )

    out = (
        pop.join(coords, on="code_muni", how="left")
        .join(fu, on="state_abbrev", how="inner")
        .select(
            "code_muni",
            "state_code",
            "state_abbrev",
            "muni_name",
            "population",
            "lat",
            "lon",
        )
        .sort("code_muni")
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.write_csv(OUT)
    print(f"wrote {OUT} ({out.height} municipalities, {OUT.stat().st_size} bytes)")
    print(f"states={out['state_abbrev'].n_unique()} missing_lat={out['lat'].null_count()}")


if __name__ == "__main__":
    main()
