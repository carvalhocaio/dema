from typing import Protocol

from dema.sections.catalog import SectionCatalog


class SectionSource(Protocol):
    def load(self) -> SectionCatalog: ...
