from bson.objectid import ObjectId
from models.db_schemas import Asset
from models.enums import DatabaseCollectionsEnum
from .base_obj_model import BaseObjModel


class AssetModel(BaseObjModel):
    """
    Building a data model for the assets collection
    """
    def __init__(self, db_client):
        super().__init__(db_client = db_client)
        self.collection = self.db_client[DatabaseCollectionsEnum.COLLECTION_ASSETS_NAME.value]

    
    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client)
        await instance.init_collection_indexes()
        return instance
    

    async def init_collection_indexes(self):
        indexes = Asset.get_indexes()
        for idx in indexes:
            await self.collection.create_index(
                idx["key"],
                name = idx["name"],
                unique = idx["unique"]
            )
        
    
    async def create_asset(self, asset: Asset):
        result = await self.collection.insert_one(asset.model_dump(by_alias = True, exclude_unset = True))
        asset._id = result.inserted_id
        return asset
    
    
    async def get_asset_record(self, project_id: str, asset_name: str) -> Asset:
        record = await self.collection.find_one({
            "asset_project_id": ObjectId(project_id) if isinstance(project_id, str) else project_id,
            "asset_name": asset_name
        })

        if record:
            return Asset(**record)
        
        return None

    async def get_all_project_assets(self, project_id: str, asset_type: str) -> list[Asset]:
        records = await self.collection.find({
            "asset_project_id": ObjectId(project_id) if isinstance(project_id, str) else project_id,
            "asset_type": asset_type
        }).to_list(length = None)

        return [Asset(**record) for record in records]