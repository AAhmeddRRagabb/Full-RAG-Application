from models.db_schemas import Chat, Message

from .base_obj_model import BaseObjModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class ChatModel(BaseObjModel):
    def __init__(self, db_client):
        super().__init__(db_client = db_client)


    async def insert_chat(self, chat: Chat) -> bool:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                session.add(chat)
                await session.commit()
                await session.refresh(chat)

        except Exception as e:
            self.logger.error(f"Error Inserting Chat: {e}")
            return False

        return True


    async def get_user_chats(self, user_id: int) -> list[Chat] | None:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(Chat)
                    .where(Chat.user_id == user_id)
                    .order_by(Chat.chat_id)
                )

                chats = list(result.scalars().all())

        except Exception as e:
            self.logger.error(f"Error Accessing User Chats: {e}")
            return None

        return chats


    async def get_user_chat(self, user_id: int, chat_id: int) -> Chat | None:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(Chat).where(
                        Chat.chat_id == chat_id,
                        Chat.user_id == user_id,
                    )
                )

                chat = result.scalar_one_or_none()

        except Exception as e:
            self.logger.error(f"Error Accessing Chat: {e}")
            return None

        return chat


    async def update_chat_name(self, user_id: int, chat_id: int, chat_name: str) -> Chat | None:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(Chat).where(
                        Chat.chat_id == chat_id,
                        Chat.user_id == user_id,
                    )
                )

                chat = result.scalar_one_or_none()
                if chat is None:
                    return None

                chat.chat_name = chat_name
                await session.commit()
                await session.refresh(chat)

        except Exception as e:
            self.logger.error(f"Error Renaming Chat: {e}")
            return None

        return chat


    async def update_chat_settings(self, user_id: int, chat_id: int, chat_settings: dict) -> Chat | None:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(Chat).where(
                        Chat.chat_id == chat_id,
                        Chat.user_id == user_id,
                    )
                )

                chat = result.scalar_one_or_none()
                if chat is None:
                    return None

                chat.chat_settings = chat_settings
                await session.commit()
                await session.refresh(chat)

        except Exception as e:
            self.logger.error(f"Error Updating Chat Settings: {e}")
            return None

        return chat


    async def delete_user_chat(self, user_id: int, chat_id: int) -> bool:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    delete(Chat).where(
                        Chat.chat_id == chat_id,
                        Chat.user_id == user_id,
                    )
                )

                await session.commit()

        except Exception as e:
            self.logger.error(f"Error Deleting Chat: {e}")
            return False

        return result.rowcount > 0


    async def insert_message(self, message: Message) -> bool:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                session.add(message)
                await session.commit()
                await session.refresh(message)

        except Exception as e:
            self.logger.error(f"Error Inserting Message: {e}")
            return False

        return True


    async def get_chat_messages(self, user_id: int, chat_id: int) -> list[Message] | None:
        session: AsyncSession

        try:
            async with self.db_client() as session:
                result = await session.execute(
                    select(Message)
                    .join(Chat, Message.chat_id == Chat.chat_id)
                    .where(
                        Chat.chat_id == chat_id,
                        Chat.user_id == user_id,
                    )
                    .order_by(Message.created_at, Message.message_id)
                )

                messages = list(result.scalars().all())

        except Exception as e:
            self.logger.error(f"Error Accessing Chat Messages: {e}")
            return None

        return messages
