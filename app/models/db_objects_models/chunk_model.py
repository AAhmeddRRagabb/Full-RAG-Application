# ----------------------------------------------------
# Building a database collection for chunks
# ----------------------------------------------------


from bson.objectid import ObjectId
from models.enums import DatabaseCollectionsEnum
from models.db_schemas import DataChunk
from .base_obj_model import BaseObjModel
from pymongo import InsertOne

class ChunkModel(BaseObjModel):
    """
    Data model for the chunks collection
    """
    def __init__(self, db_client):
        super().__init__(db_client)
        self.collection = self.db_client[DatabaseCollectionsEnum.COLLECTION_CHUNKS_NAME.value]


    @classmethod
    async def create_instance(cls, db_client):
        instance = cls(db_client)
        await instance.init_collection_indexes()
        return instance


    async def init_collection_indexes(self):
        indexes = DataChunk.get_indexes()
        for idx in indexes:
            await self.collection.create_index(
                idx["key"],
                name = idx["name"],
                unique = idx["unique"]
            )


    async def insert_chunk(self, chunk: DataChunk):
        result = await self.collection.insert_one(
            chunk.model_dump(by_alias = True, exclude_none = True)
        )

        chunk._id = result.inserted_id

        return chunk
    


    async def get_chunk(self, chunk_id: str):
        record = await self.collection.find_one({
            "_id" : chunk_id
        })

        if record is None or not record:
            return None
        
        return DataChunk(**record)


    async def insert_many_chunks(self, chunks: list[DataChunk], batch_size: int = 100):
        """Insert many chunks in batches to enable efficient inserting"""
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            operations = [
                InsertOne(document = chunk.model_dump(by_alias = True, exclude_none = True))
                for chunk in batch
            ]

            # insert the batch
            await self.collection.bulk_write(operations)

        return len(chunks)
    

    async def delete_chunks_by_project_id(self, project_id: ObjectId):
        result = await self.collection.delete_many({
            "chunk_project_id" : project_id
        })

        return result.deleted_count
    
    async def get_project_chunks(self, project_id: ObjectId, page_no: int = 1, page_size: int = 50):
        records = await self.collection.find({
            "chunk_project_id": project_id
        }).skip((page_no - 1) * page_size).limit(page_size).to_list(length = None)

        return [DataChunk(**record) for record in records]