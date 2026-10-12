


from models.request_schemas.auth import UserPublic
from models.db_schemas import User



def build_public_user(user: User) -> UserPublic:
    return UserPublic(
        user_name = user.user_name,
        user_email = user.user_email,
        user_uuid_prefix = user.user_uuid.hex[:3],
    )