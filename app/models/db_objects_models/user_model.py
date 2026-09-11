# ----------------------------------------------------
# Building a database model for users
# ----------------------------------------------------


from models.enums import ResponsesEnum
from models.db_schemas import User

from .base_obj_model import BaseObjModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

class UserModel(BaseObjModel):
    """
    Data model for the user table

    Methods:
        insert_user(user)               : inserting a user into the database.
        get_user_by_name(user_name)     : retrieving a user from the database.
        get_user_or_insert_it(user_name): used to retrieve user if found / insert user if not found.
        get_all_users(page, page_size)  : get all users in the database.
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
    async def get_user_by_name(self, user_name: str) -> User | None:
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
                            User.user_name == user_name
                        )
                    )

                    user = result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Error Accessing User: {e}")
            return None


        return user

    
    async def get_user_or_insert_it(self, user_name: str) -> User | None:
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
                        select(User).where(User.user_name == user_name)
                    )

                    user = result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Error Accessing User: {e}")
            return None

        
        if user is None:
            user = User(user_name = user_name)

            inserted = await self.insert_user(user)
            if inserted:
                return user
            else:
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