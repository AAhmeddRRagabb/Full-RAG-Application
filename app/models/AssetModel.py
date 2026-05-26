from bson.objectid import ObjectId
from .db_schemas import Asset
from .enums.DatabaseEnum import DatabaseEnum
from .BaseDataModel import BaseDataModel

class AssetModel(BaseDataModel):
    """
    Building an data model for the assets collection
    """
    def __init__(self, db_client):
        super().__init__(db_client = db_client)
        self.collection = self.db_client[DatabaseEnum.COLLECTION_ASSETS_NAME.value]

    
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
    
    
    async def get_all_project_assets(self, project_id: str):
        return await self.collection.find({
            "asset_project_id": ObjectId(project_id) if isinstance(project_id, str) else project_id
        }).to_list(length = None)