from beartype.typing import Type, TypedDict, Optional
from uuid import UUID
from sqlalchemy import select
from app.datastore.base_crud import BaseCRUDDataService
from app.db.model import Seed


class SeedDataRow(TypedDict):
    """Row type for seed data query results."""

    seed_id: UUID
    name_code: str
    family: str
    genus: str
    species: str
    subspecies: Optional[str]
    variety: Optional[str]
    synonyms: Optional[str]
    author: Optional[str]
    subspecies_author: Optional[str]
    variety_author: Optional[str]
    url: Optional[str]
    seed_metadata: Optional[dict]


class SeedDataService(BaseCRUDDataService[Seed]):
    """Data access layer for seed database operations."""

    @classmethod
    def get_model_class(cls) -> Type[Seed]:
        return Seed

    async def get_seed_data(self) -> list[SeedDataRow]:
        """
        Get active seed data with subset of columns.

        Returns only specific columns (seed_id, name_code, family, genus, species, seed_metadata)
        for active seeds only.

        Returns:
            List of dictionaries with seed data
        """
        query = select(
            Seed.id.label("seed_id"),
            Seed.name_code,
            Seed.family,
            Seed.genus,
            Seed.species,
            Seed.subspecies,
            Seed.variety,
            Seed.synonyms,
            Seed.author,
            Seed.subspecies_author,
            Seed.variety_author,
            Seed.url,
            Seed.seed_metadata,
        ).where(Seed.active.is_(True))
        result = await self.session.execute(query)
        return [row._asdict() for row in result.all()]  # type: ignore[misc]

    async def get_seeds_by_labels(self, labels: list[str]) -> dict[str, UUID]:
        """
        Get seeds matching the provided labels (case-insensitive).

        Matches labels against full species name (genus + species) only.
        Returns a dictionary mapping lowercase labels to seed UUIDs.

        Args:
            labels: List of label strings to match (e.g., ["Avena fatua", "Bromus tectorum"])

        Returns:
            Dictionary mapping lowercase labels to seed UUIDs
            Example: {"avena fatua": UUID("..."), "bromus tectorum": UUID("...")}
        """
        from sqlalchemy import func

        if not labels:
            return {}

        # Convert all labels to lowercase for case-insensitive matching
        lowercase_labels = [label.lower() for label in labels]

        # Build query with case-insensitive matching on full species name only
        query = select(Seed.id, Seed.genus, Seed.species).where(
            Seed.active.is_(True),
            # Match on full species name: "Genus species" (case-insensitive)
            func.lower(func.concat(Seed.genus, " ", Seed.species)).in_(
                lowercase_labels
            ),
        )

        result = await self.session.execute(query)

        # Build lookup dictionary mapping lowercase labels to seed UUIDs
        seed_lookup: dict[str, UUID] = {}
        for row in result.all():
            seed_id = row.id
            genus = row.genus or ""
            species = row.species or ""

            # Add mapping by full species name
            if genus and species:
                full_species_name = f"{genus} {species}".lower()
                seed_lookup[full_species_name] = seed_id

        return seed_lookup
