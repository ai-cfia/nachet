from typing import Dict, Any, Type, List
from uuid import UUID
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
    async def get_all(cls, user_id: UUID, **kwargs) -> Dict[str, Any]:
        """Override to change response key from 'items' to 'seeds' for backward compatibility."""
        result = await super().get_all(user_id, **kwargs)
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
        try:
            seeds = None
            async with sessionmanager.get_session() as session:
                seeds = await SeedDataService(session).get_seed_data()
            return {"seeds": [seed._asdict() for seed in seeds] if seeds else []}
        except Exception as e:
            raise SeedError(f"Failed to retrieve seed data: {str(e)}") from e
