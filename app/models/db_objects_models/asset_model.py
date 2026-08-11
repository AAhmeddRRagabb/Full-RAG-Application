
from models.db_schemas import Asset
from models.enums import ResponsesEnum
from .chunk_model import ChunkModel
from models.system_schemas import ComponentResult

from .base_obj_model import BaseObjModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

class AssetModel(BaseObjModel):
    """
    Building a data model for the assets table
    """
    def __init__(self, db_client):
        super().__init__(db_client = db_client)


    async def create_asset(self, asset: Asset) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: the asset created
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                session.add(asset)
                await session.commit()
                await session.refresh(asset)
            
        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.ASSET_INNER_ERROR.value)

        return self._return_success(content = asset)
    

    
    async def get_asset_record(self, user_id: int, asset_name: str) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: the asset 
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(Asset).where(
                        Asset.asset_user_id == user_id,
                        Asset.asset_name == asset_name
                    )
                )
        except Exception as e:
            return self._return_failure(message = ResponsesEnum.ASSET_INNER_ERROR.value, error = e)

        record = result.scalar_one_or_none()
        return self._return_success(content = record)



    async def get_all_user_assets(self, user_id: int, asset_type: str) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: list of the user assets
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(Asset).where(
                        Asset.asset_user_id == user_id,
                        Asset.asset_type == asset_type
                    )
                )
        except Exception as e:
            return self._return_failure(message = ResponsesEnum.ASSET_INNER_ERROR.value, error = e)

        return self._return_success(content = list(result.scalars().all()))


    async def delete_all_user_assets(self, user_id: int) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: dict contains the n_deleted_assets & n_deleted_chunks [related chunks deleted]
                if failure -> error & respone message
        """
        session: AsyncSession

        # delete related chunks
        chunks_delete_result = await ChunkModel(db_client = self.db_client).delete_chunks_by_user_id(user_id = user_id)
        if not chunks_delete_result.success:
            return self._return_failure(message = ResponsesEnum.ASSET_INNER_ERROR.value, error = chunks_delete_result.error)

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    delete(Asset).where(
                        Asset.asset_user_id == user_id
                    )
                )

                await session.commit()
                

        except Exception as e:
            return self._return_failure(message = ResponsesEnum.ASSET_INNER_ERROR.value, error = e)

        return self._return_success(content = {
            "n_deleted_assets": result.rowcount,
            "n_deleted_chunks": chunks_delete_result.content
        })
