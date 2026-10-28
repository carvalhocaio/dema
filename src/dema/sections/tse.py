from dataclasses import dataclass
from pathlib import Path

import polars as pl

from dema.domain.election import ElectionRound
from dema.sections.catalog import KEY_COLUMNS, SectionCatalog

COLUMN_MAPPING = {
    "SG_UF": "state",
    "CD_MUNICIPIO": "municipality_code",
    "NR_ZONA": "zone",
    "NR_SECAO": "number",
    "QT_ELEITOR_SECAO": "eligible_voters",
}
ROUND_COLUMN = "NR_TURNO"


@dataclass(frozen=True, slots=True)
class TseSectionSource:
    csv_path: Path
    round: ElectionRound = ElectionRound.FIRST

    def load(self) -> SectionCatalog:
        lazy = pl.scan_csv(
            self.csv_path,
            separator=";",
            encoding="utf8-lossy",
            infer_schema=False,
        )
        header = set(lazy.collect_schema().names())
        missing = COLUMN_MAPPING.keys() - header
        if missing:
            raise ValueError(f"TSE file missing columns: {sorted(missing)}")
        if ROUND_COLUMN in header:
            lazy = lazy.filter(pl.col(ROUND_COLUMN).cast(pl.Int8) == self.round)
        frame = (
            lazy.select(
                pl.col(source).str.strip_chars().alias(target)
                for source, target in COLUMN_MAPPING.items()
            )
            .with_columns(pl.col("eligible_voters").cast(pl.Int32))
            .filter(pl.col("eligible_voters") > 0)
            .unique(subset=KEY_COLUMNS, keep="first", maintain_order=True)
            .collect()
        )
        return SectionCatalog(frame)
