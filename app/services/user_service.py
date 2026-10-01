from dataclasses import dataclass

from app import security


@dataclass
class User:
    id: int
    username: str
    hashed_password: str


# In-memory storage: resets whenever the application restarts.
_users: dict[int, User] = {}
_next_id = 1


def reset_users() -> None:
    global _next_id
    _users.clear()
    _next_id = 1


def get_by_id(user_id: int) -> User | None:
    return _users.get(user_id)


def get_by_username(username: str) -> User | None:
    return next((u for u in _users.values() if u.username == username), None)


def create_user(username: str, password: str) -> User | None:
    """Create a user, or return None if the username is already taken."""
    global _next_id
    if get_by_username(username) is not None:
        return None
    user = User(_next_id, username, security.hash_password(password))
    _users[user.id] = user
    _next_id += 1
    return user


def authenticate(username: str, password: str) -> User | None:
    user = get_by_username(username)
    if user is None:
        security.verify_password(password, security.DUMMY_HASH)
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user
