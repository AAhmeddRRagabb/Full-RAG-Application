# ----------------------------------------------------
# Building a database model for chunks
# ----------------------------------------------------

from models.enums import ResponsesEnum
from models.db_schemas import DataChunk

from .base_obj_model import BaseObjModel, ObjectModelResult
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

class ChunkModel(BaseObjModel):
    """
    Data model for the chunks table
    """
    def __init__(self, db_client):
        super().__init__(db_client)



    async def insert_chunk(self, chunk: DataChunk) -> ObjectModelResult:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(chunk)
                await session.commit()        # commit the results
                await session.refresh(chunk)  # update the current python object chunk
        except Exception as e:
            return self._return_failure(message = ResponsesEnum.CHUNK_INNER_ERROR.value, error = e)

        
        return self._return_success(content = chunk)
    


    async def get_chunk(self, chunk_id: int) -> ObjectModelResult:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(DataChunk).where(DataChunk.chunk_id == chunk_id)
                )
        except Exception as e:
            return self._return_failure(message = ResponsesEnum.CHUNK_INNER_ERROR.value, error = e) 


        return self._return_success(content = result.scalar_one_or_none())


    async def insert_many_chunks(self, chunks: list[DataChunk], batch_size: int = 100):
        """Insert many chunks in batches to enable efficient inserting"""
        session: AsyncSession

        try:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]

                async with self.db_client() as session:
                    session.add_all(batch)
                    await session.commit()
        except Exception as e:
            return self._return_failure(message = ResponsesEnum.CHUNK_INNER_ERROR.value, error = e)

        return self._return_success(content = len(chunks))
    

    async def delete_chunks_by_project_id(self, project_id: int) -> ObjectModelResult:
        session: AsyncSession
        
        try:
            async with self.db_client() as session:
                result = await session.execute(
                    delete(DataChunk).where(DataChunk.chunk_project_id == project_id)
                )
                await session.commit()
        except Exception as e:
            return self._return_failure(message = ResponsesEnum.CHUNK_INNER_ERROR.value, error = e)

        return self._return_success(result.rowcount)
        
    
    async def get_project_chunks(self, project_id: int, page_no: int = 1, page_size: int = 50):
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(DataChunk)
                    .where(DataChunk.chunk_project_id == project_id)
                    .order_by(DataChunk.chunk_id)
                    .offset((page_no - 1) * page_size)
                    .limit(page_size)
                )

        except Exception as e:
            return self._return_failure(message = ResponsesEnum.CHUNK_INNER_ERROR.value, error = e)

        return self._return_success(content = list(result.scalars().all())
)