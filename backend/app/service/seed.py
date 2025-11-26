from beartype.typing import Dict, Any, Type, List, cast
from uuid import UUID
import re

from app.service.base_crud import BaseCRUDService, BaseCRUDDataService
from app.datastore.seed import SeedDataService
from app.db.model import Seed
from app.db.utils import sessionmanager
from app.exceptions import (
    SeedNotFoundError,
    SeedCreationError,
    SeedUpdateError,
    SeedDeletionError,
    SeedError,
)


class SeedService(BaseCRUDService[Seed]):
    """Service operations on seed data."""

    @classmethod
    def get_entity_name(cls) -> str:
        return "Seed"

    @classmethod
    def get_data_service_class(cls) -> Type[BaseCRUDDataService[Seed]]:
        return SeedDataService

    @classmethod
    def serialize_entity(cls, entity: Seed) -> Dict[str, Any]:
        """Serialize Seed entity to dictionary."""
        return {
            "seed_id": str(entity.id),  # Keep seed_id for backward compatibility
            "name_code": entity.name_code,
            "family": entity.family,
            "genus": entity.genus,
            "species": entity.species,
            "subspecies": entity.subspecies,
            "variety": entity.variety,
            "synonyms": entity.synonyms,
            "author": entity.author,
            "subspecies_author": entity.subspecies_author,
            "variety_author": entity.variety_author,
            "url": entity.url,
            "metadata": entity.seed_metadata,
            "original_ista_2025": entity.original_ista_2025,
            "active": entity.active,
            "date_created": entity.date_created.isoformat(),
            "date_updated": entity.date_updated.isoformat(),
        }

    @classmethod
    def get_not_found_exception(cls) -> Type[Exception]:
        return SeedNotFoundError

    @classmethod
    def get_creation_exception(cls) -> Type[Exception]:
        return SeedCreationError

    @classmethod
    def get_update_exception(cls) -> Type[Exception]:
        return SeedUpdateError

    @classmethod
    def get_deletion_exception(cls) -> Type[Exception]:
        return SeedDeletionError

    @classmethod
    async def get_by_id(
        cls,
        requester_id: UUID,
        entity_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get a seed by ID with debug logging.

        Args:
            requester_id: UUID of the user making the request
            entity_id: UUID of the seed to retrieve

        Returns:
            Dictionary representation of the seed

        Raises:
            SeedNotFoundError: If seed not found
        """
        from app.service.logs import LogService
        import time

        logger = LogService.get_logger()

        logger.debug(
            "Fetching seed by ID",
            seed_id=str(entity_id),
            requester_id=str(requester_id),
        )

        start_time = time.time()

        try:
            # Call parent get_by_id method
            result = await super().get_by_id(requester_id, entity_id)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Seed retrieved successfully",
                seed_id=str(entity_id),
                name_code=result.get("name_code"),
                active=result.get("active"),
                duration_ms=round(elapsed_ms, 2),
            )

            return result
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to retrieve seed",
                seed_id=str(entity_id),
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(elapsed_ms, 2),
            )
            raise

    @classmethod
    async def get_all(
        cls,
        requester_id: UUID,
        offset: int = 0,
        limit: int = 100,
        filters: Dict[str, Any] | None = None,
        order_by: str | None = None,
        order_direction: str = "asc",
    ) -> Dict[str, Any]:
        """Override to change response key from 'items' to 'seeds' for backward compatibility."""
        result = await super().get_all(
            requester_id,
            offset=offset,
            limit=limit,
            filters=filters,
            order_by=order_by,
            order_direction=order_direction,
        )
        result["seeds"] = result.pop("items")  # Rename key
        return result

    @staticmethod
    async def get_seed_data() -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve active seed data with subset of columns.

        Returns simplified seed information for active seeds only.
        This is a public endpoint that doesn't require authentication.

        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary with 'seeds' key containing list of seed records.
            Each seed record contains: seed_id, name_code, family, genus, species, seed_metadata

        Raises:
            SeedError: If data retrieval fails
        """
        from app.service.logs import LogService
        import time

        logger = LogService.get_logger()

        logger.debug("Fetching seed data")

        start_time = time.time()

        try:
            seeds = None
            async with sessionmanager.get_session() as session:
                seeds = await SeedDataService(session).get_seed_data()

            # Convert UUID seed_id to string for API response
            serialized_seeds = (
                [{**seed, "seed_id": str(seed["seed_id"])} for seed in seeds]
                if seeds
                else []
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Seed data retrieved",
                seed_count=len(serialized_seeds),
                duration_ms=round(elapsed_ms, 2),
            )

            # TypedDict (SeedDataRow) is compatible with Dict[str, Any] at runtime
            return {"seeds": cast(List[Dict[str, Any]], serialized_seeds)}
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to retrieve seed data",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(elapsed_ms, 2),
            )
            raise SeedError(f"Failed to retrieve seed data: {str(e)}") from e

    @staticmethod
    async def get_seeds_by_labels(labels: List[str]) -> Dict[str, UUID]:
        """
        Get seeds matching the provided labels (case-insensitive).

        Efficiently queries only the seeds needed based on ML model labels.
        Much more efficient than loading all seeds into memory.

        Args:
            labels: List of label strings to match (e.g., ["Avena fatua", "AMBRO_PSI"])

        Returns:
            Dict[str, UUID]: Dictionary mapping lowercase labels to seed UUIDs
            Example: {"avena fatua": UUID("..."), "ambro_psi": UUID("...")}

        Raises:
            SeedError: If data retrieval fails
        """
        from app.service.logs import LogService
        import time

        logger = LogService.get_logger()

        logger.debug("Fetching seeds by labels", label_count=len(labels))

        start_time = time.time()

        try:
            seed_lookup = None
            async with sessionmanager.get_session() as session:
                seed_lookup = await SeedDataService(session).get_seeds_by_labels(labels)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(
                "Seeds retrieved by labels",
                label_count=len(labels),
                seeds_found=len(seed_lookup),
                duration_ms=round(elapsed_ms, 2),
            )

            return seed_lookup
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to retrieve seeds by labels",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(elapsed_ms, 2),
            )
            raise SeedError(f"Failed to retrieve seeds by labels: {str(e)}") from e

    @staticmethod
    def normalize_taxonomic_name(name: str) -> str:
        """
        Normalize taxonomic names (genus/species) for blob storage paths.

        Used to create consistent, filesystem-safe names for blob storage organization.

        Rules:
        - Lowercase only
        - Only letters (a-z) and dashes allowed
        - Remove all other characters
        - Multiple consecutive dashes collapsed to single dash
        - Strip leading/trailing dashes

        Args:
            name: Raw taxonomic name (e.g., "Avena Fatua")

        Returns:
            Normalized name (e.g., "avena-fatua")

        Example:
            >>> SeedService.normalize_taxonomic_name("Avena Fatua")
            'avena-fatua'
            >>> SeedService.normalize_taxonomic_name("Bromus-tectorum")
            'bromus-tectorum'
        """
        if not name:
            return "unknown"

        # Convert to lowercase
        name = name.lower().strip()

        # Replace spaces with dashes
        name = name.replace(" ", "-")

        # Remove all characters except a-z and dashes
        name = re.sub(r"[^a-z\-]", "", name)

        # Collapse multiple consecutive dashes
        name = re.sub(r"-+", "-", name)

        # Strip leading/trailing dashes
        name = name.strip("-")

        return name if name else "unknown"
