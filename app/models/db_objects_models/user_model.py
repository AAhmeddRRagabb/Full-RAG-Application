# ----------------------------------------------------
# Building a database model for users
# ----------------------------------------------------


from models.system_schemas import ComponentResult
from models.enums import ResponsesEnum
from models.db_schemas import User

from .base_obj_model import BaseObjModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

class UserModel(BaseObjModel):
    """
    Data model for the user table
    """
    def __init__(self, db_client):
        super().__init__(db_client)
        


    async def insert_user(self, user: User) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: the user inserted
                if failure -> error & respone message
        """
        session: AsyncSession

        try:
            async with self.db_client() as session:
                async with session.begin():
                    session.add(user)

                await session.commit()  
                await session.refresh(user)

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.USER_INNER_ERROR.value)

        return self._return_success(content = user)
    

    async def get_user(self, user_name: str) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: the user
                if failure -> error & respone message
        """
        session: AsyncSession

        if not user_name or not user_name.strip():
            return self._return_failure(message = ResponsesEnum.USER_INVALID_NAME.value)

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
            return self._return_failure(error = e, message = ResponsesEnum.USER_INNER_ERROR.value)

        return self._return_success(user)

    

    async def get_user_or_insert_it(self, user_name: str) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: the user
                if failure -> error & respone message
        """
        session: AsyncSession

        if not user_name or not user_name.strip():
            return self._return_failure(message = ResponsesEnum.USER_INVALID_NAME.value)

        try:
            async with self.db_client() as session:
                async with session.begin():
                    result = await session.execute(
                        select(User).where(User.user_name == user_name)
                    )

                    user = result.scalar_one_or_none()

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.USER_INNER_ERROR.value)

        
        if user is None:
            user = User(
                user_name = user_name
            )

            return await self.insert_user(user)

        return self._return_success(user)
        


    async def get_all_users(self, page: int = 1, page_size: int = 10) :
        """
        Returns:
            ComponentResult:
                if success -> content: dict contains users & num_pages
                if failure -> error & respone message
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
            return self._return_failure(error = e, message = ResponsesEnum.USER_INNER_ERROR.value)
    
        return self._return_success(content = {
            'users' : users, 
            'num_pages': total_pages
        })
