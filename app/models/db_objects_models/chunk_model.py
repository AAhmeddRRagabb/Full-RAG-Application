# ----------------------------------------------------
# Building a database model for chunks
# ----------------------------------------------------

from models.enums import ResponsesEnum
from models.db_schemas import DataChunk

from .base_obj_model import BaseObjModel
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

class ChunkModel(BaseObjModel):
    """
    Data model for the chunks table

    Methods:
        insert_chunk(chunk)                         : inserting a chunk into the database.  
        insert_many_chunks(chunks, batch_size)      : many chunks batch-insertion into the database.  
        get_chunk(chunk_id)                         : retrieving a chunk from the databse.
        get_user_chunks(user_id, page_no, page_size): accessing all user chunks.
        get_user_chunks_count(user_id)              : counting user chunks.
        has_asset_chunks(user_id, asset_id)         : checking if user has chunks for the given asset.
        delete_user_chunks(user_id)                 : delete all user chunks
    """
    def __init__(self, db_client):
        super().__init__(db_client)


    # ------------------------------ Insertion ----------------------------- #
    async def insert_chunk(self, chunk: DataChunk) -> bool:
        """
        Returns:
            a bool indicates whether the chunk has been inserted successfully or not.
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(chunk)
                await session.commit()        # commit the results
                await session.refresh(chunk)  # update the current python object chunk

        except Exception as e:
            self.logger.error(f"Error Inserting Chunk: {e}")
            return False
        
        return True

    async def insert_many_chunks(self, chunks: list[DataChunk], batch_size: int = 100) -> bool:
        """
        Returns:
            a bool indicates whether the chunks have been inserted successfully or not.
        """
        
        session: AsyncSession

        try:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]

                async with self.db_client() as session:
                    session.add_all(batch)
                    await session.commit()

        except Exception as e:
            self.logger.error(f"Error Inserting Chunks: {e}")
            return False

        return True
    
    # ------------------------------ Retrieving -------------------------------- #
    async def has_asset_chunks(self, user_id: int, asset_id: int) -> bool:
        """
        Returns:
            does have asset chunks -> True   
            else -> False
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                count = await session.scalar(
                    select(func.count()).select_from(DataChunk).where(
                        DataChunk.chunk_user_id == user_id,
                        DataChunk.chunk_asset_id == asset_id
                    )
                )

        except Exception as e:
            self.logger.error(f"Error Checking User Chunks: {e}")
            return None

        return count > 0

    async def get_chunk(self, chunk_id: int) -> DataChunk | None:
        """
        Returns:   
            if success -> the chunk    
            if failure -> None
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(DataChunk).where(DataChunk.chunk_id == chunk_id)
                )

                record = result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Error Accessing Chunk: {e}")
            return None

        return record


    async def get_user_chunks(self, user_id: int, page_no: int = 1, page_size: int = 50) -> list[DataChunk] | None:
            """
            Returns:
                if success -> list of user chunks  
                if failure -> None
            """
            session: AsyncSession
    
            try:
                async with self.db_client() as session:
                    result = await session.execute(
                        select(DataChunk)
                        .where(DataChunk.chunk_user_id == user_id)
                        .order_by(DataChunk.chunk_id)
                        .offset((page_no - 1) * page_size)
                        .limit(page_size)
                    )
    
                    records = list(result.scalars().all())
    
            except Exception as e:
                self.logger.error(f"Error Accessing User Chunks: {e}")
                return None
    
            return records


    async def get_user_chunks_count(self, user_id: int) -> int | None:
        """
        Returns:
            if success -> number of user chunks  
            if failure -> None
        """
        session: AsyncSession

        total_count = 0

        try:
            async with self.db_client() as session:
                count_sql = select(func.count(DataChunk.chunk_id)).where(DataChunk.chunk_user_id == user_id)
                records_count = await session.execute(count_sql)
                total_count = records_count.scalar()

        except Exception as e:
            self.logger.error(f"Error Accessing Num of User Chunks: {e}")
            return None
        
        return total_count

    # ------------------------------ Deleting -------------------------------- #
    async def delete_user_chunks(self, user_id: int) -> bool:
        """
        Returns:
            a bool indicates whether the chunks have been inserted successfully or not.
        """

        session: AsyncSession
        
        try:
            async with self.db_client() as session:
                await session.execute(
                    delete(DataChunk).where(DataChunk.chunk_user_id == user_id)
                )
                await session.commit()

        except Exception as e:
            self.logger.error(f"Error Deleting Chunks: {e}")
            return False

        return True