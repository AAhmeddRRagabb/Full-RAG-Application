from models.db_schemas import Asset
from .base_obj_model import BaseObjModel
from sqlalchemy import select


class AssetModel(BaseObjModel):
    """
    Building a data model for the assets table
    """
    def __init__(self, db_client):
        super().__init__(db_client = db_client)

    
    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client)
        return instance
    

    async def create_asset(self, asset: Asset):
        async with self.db_client() as session:
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
            return asset
    
    
    async def get_asset_record(self, project_id: int, asset_name: str) -> Asset | None:
        async with self.db_client() as session:
            result = await session.execute(
                select(Asset).where(
                    Asset.asset_project_id == project_id,
                    Asset.asset_name == asset_name
                )
            )

            return result.scalar_one_or_none()

    async def get_all_project_assets(self, project_id: int, asset_type: str) -> list[Asset]:
        async with self.db_client() as session:
            result = await session.execute(
                select(Asset).where(
                    Asset.asset_project_id == project_id,
                    Asset.asset_type == asset_type
                )
            )

            return list(result.scalars().all())
