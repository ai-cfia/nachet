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
            Seed.seed_metadata,
        ).where(Seed.active.is_(True))
        result = await self.session.execute(query)
        return [row._asdict() for row in result.all()]  # type: ignore[misc]

    async def get_seeds_by_labels(self, labels: list[str]) -> dict[str, UUID]:
        """
        Get seeds matching the provided labels (case-insensitive).

        Matches labels against both name_code and full species name (genus + species).
        Returns a dictionary mapping lowercase labels to seed UUIDs.

        Args:
            labels: List of label strings to match (e.g., ["Avena fatua", "AMBRO_PSI"])

        Returns:
            Dictionary mapping lowercase labels to seed UUIDs
            Example: {"avena fatua": UUID("..."), "ambro_psi": UUID("...")}
        """
        from sqlalchemy import func, or_

        if not labels:
            return {}

        # Convert all labels to lowercase for case-insensitive matching
        lowercase_labels = [label.lower() for label in labels]

        # Build query with case-insensitive matching on name_code and full species name
        query = select(Seed.id, Seed.name_code, Seed.genus, Seed.species).where(
            Seed.active.is_(True),
            or_(
                # Match on name_code (case-insensitive)
                func.lower(Seed.name_code).in_(lowercase_labels),
                # Match on full species name: "Genus species" (case-insensitive)
                func.lower(func.concat(Seed.genus, " ", Seed.species)).in_(
                    lowercase_labels
                ),
            ),
        )

        result = await self.session.execute(query)

        # Build lookup dictionary mapping lowercase labels to seed UUIDs
        seed_lookup: dict[str, UUID] = {}
        for row in result.all():
            seed_id = row.id
            name_code = row.name_code
            genus = row.genus or ""
            species = row.species or ""

            # Add mapping by name_code
            if name_code:
                seed_lookup[name_code.lower()] = seed_id

            # Add mapping by full species name
            if genus and species:
                full_species_name = f"{genus} {species}".lower()
                seed_lookup[full_species_name] = seed_id

        return seed_lookup
