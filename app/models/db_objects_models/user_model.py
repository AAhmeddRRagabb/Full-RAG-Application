# ----------------------------------------------------
# Building a database model for users
# ----------------------------------------------------

from uuid import UUID
from models.enums import ResponsesEnum
from models.db_schemas import User

from .base_obj_model import BaseObjModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

class UserModel(BaseObjModel):
    """
    Data model for the user table

    Methods:
        insert_user(user)               : inserting a user into the database.
        get_user_by_email(email)        : retrieving a user from the database using the email.
        get_user_by_uuid(user_uuid)     : retrieving a user from the database using the user_uuid.
        get_all_users(page, page_size)  : get all users in the database.
        delete_all_users()              : delete users
    """
    def __init__(self, db_client):
        super().__init__(db_client)
        
    # ---------------------------- Insertion ------------------------------- #
    async def insert_user(self, user: User) -> bool:
        """
        Returns:
            a bool indicates whether the user has been inserted successfully or not.
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(user)

                await session.commit()  
                await session.refresh(user)

        except Exception as e:
            self.logger.error(f"Error Inserting User: {e}")
            return False

        return True
    
    # ----------------------- Retrieving Info ------------------------ #
    async def get_user_by_email(self, email: str) -> User | None:
        """
        Returns:
            if success -> the user  
            if failure -> None
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    result = await session.execute(
                        statement = select(User).where(
                            User.user_email == email
                        )
                    )

                    user = result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Error Accessing User: {e}")
            return None

        return user


    async def get_user_by_uuid(self, user_uuid: UUID) -> User | None:
        """
        Returns:
            if success -> the user  
            if failure -> None
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    result = await session.execute(
                        statement = select(User).where(
                            User.user_uuid == user_uuid
                        )
                    )

                    user = result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Error Accessing User: {e}")
            return None

        return user



    async def get_all_users(self, page: int = 1, page_size: int = 10) -> dict[str] | None:
        """
        Returns:   
            if success -> a dict contains {users - total_pages}   
            if failure -> None
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():

                    total_documents = await session.scalar(select(func.count()).select_from(User))
                    
                    # pages
                    total_pages = total_documents // page_size
                    if total_documents % page_size > 0:
                        total_pages += 1
        
                    skipped_pages = (page - 1) * page_size
                    result = await session.execute(
                        select(User).offset(skipped_pages).limit(page_size)
                    )
                    users = list(result.scalars().all())

        except Exception as e:
            self.logger.error(f"Error Accessing Users: {e}")
            return None
    
        return {
            "users"      : users,
            "total_pages": total_pages
        }

    # ----------------------- Delete Users ------------------------ #
    async def delete_all_users(self) -> bool:
        """
        Returns:
            a bool indicates whether the users have been deleted or not.
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    await session.execute(
                        text("TRUNCATE TABLE users RESTART IDENTITY CASCADE")
                    )
            return True

        except Exception as e:
            self.logger.exception(f"Error deleting users: {e}")
            return False
    