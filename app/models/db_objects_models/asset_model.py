
from models.db_schemas import Asset
from models.enums import ResponsesEnum
from .chunk_model import ChunkModel

from .base_obj_model import BaseObjModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

class AssetModel(BaseObjModel):
    """
    Building a data model for the assets table

    Methods:
        insert_asset(asset)        : inserting an asset in the database.
        get_asset(asset)           : getting an asset
        get_user_assets(user_id)   : getting all user assets
        delete_user_assets(user_id): deleting all user assets
    """
    def __init__(self, db_client):
        super().__init__(db_client = db_client)


    # ------------------------------- Insertion ---------------------------------- #
    async def insert_asset(self, asset: Asset) -> bool:
        """
        Returns:
            a bool indicates whether the asset has been created successfully or not.
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                session.add(asset)
                await session.commit()
                await session.refresh(asset)
            
        except Exception as e:
            self.logger.error(f"Error Inserting Asset: {e}")
            return False

        return True
    

    # ------------------------------- Retrieving Info ----------------------------- #
    async def get_asset(self, user_id: int, asset_name: str) -> Asset | None:
        """
        Returns:
            if success -> the asset  
            if failure -> None
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

                record = result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Error Accessing Asset: {e}")
            return None

        
        return record



    async def get_user_assets(self, user_id: int, asset_type: str) -> list[Asset] | None:
        """
        Returns:
            if success -> list of user assets  
            if failure -> None
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

                assets = list(result.scalars().all())

        except Exception as e:
            self.logger.error(f"Error Accessing Assets: {e}")
            return None

        return assets

    # -------------------------- Deleting -------------------------------- #
    async def delete_user_assets(self, user_id: int) -> bool:
        """
        Returns:
            a bool indicates whether the assets have been deleted successfully or not.
        """
        session: AsyncSession

        # delete related chunks
        if not await ChunkModel(db_client = self.db_client).delete_user_chunks(user_id = user_id):
            return False

        try:
            async with self.db_client() as session:
                await session.execute(
                    delete(Asset).where(
                        Asset.asset_user_id == user_id
                    )
                )

                await session.commit()
                

        except Exception as e:
            self.logger.error(f"Error Deleting Assets: {e}")
            return False

        return True
