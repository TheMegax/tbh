import sqlite3
from pathlib import Path

from discord import User

import utils

from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select

origins = ['unknown', 'server', 'group_chat', 'direct_message', 'browser']


# <<< MODELS >>> #
class DBUser(SQLModel, table=True):
    user_id: int = Field(primary_key=True)
    username: Optional[str] = Field(default="")
    avatar_url: Optional[str] = Field(default="")
    is_inbox_open: Optional[bool] = Field(default=False)
    inbox_title: Optional[str] = Field(default=utils.localize("template.default_inbox_title"))


class DBMessage(SQLModel, table=True):
    message_id: int = Field(primary_key=True)
    origin: Optional[str] = Field(default=origins[0])


engine = create_engine("sqlite:///database.db")
session: Session = Session(engine)


# <<< USERS >>> #
def get_or_create_db_user(user_id: int, discord_user: User = None) -> DBUser | None:
    db_user = session.get(DBUser, user_id)
    if discord_user:
        username = discord_user.name
        avatar_url = discord_user.avatar.url
    else:
        username = ""
        avatar_url = ""

    # Updating the user if needed
    if db_user and discord_user:
        if db_user.username != username:
            db_user.username = username
        if db_user.avatar_url != avatar_url:
            db_user.avatar_url = avatar_url
        session.add(db_user)
        session.commit()
    elif not db_user:
        utils.formatlog(f'Adding new user with ID "{user_id}"')

        db_user = DBUser(user_id=user_id, username=username, avatar_url=avatar_url)
        session.add(db_user)
        session.commit()
    return db_user


def get_db_user_by_username(username: str) -> DBUser | None:
    statement = select(DBUser).where(DBUser.username == username)
    # noinspection PyTypeChecker
    results = session.exec(statement)
    for user in results:
        return user


def update_db_user(db_user: DBUser):
    session.add(db_user)
    session.commit()


# <<< MESSAGES >>> #
def get_db_message(message_id: int) -> DBMessage | None:
    return session.get(DBMessage, message_id)


def create_db_message(message_id: int, origin: str) -> None:
    db_message = session.get(DBMessage, message_id)
    if not db_message:
        utils.formatlog(f'Creating new message with ID "{message_id}" and origin "{origin}"')
        db_message = DBMessage(message_id=message_id, origin=origin)
        session.add(db_message)
        session.commit()


def update_db_message(db_message: DBMessage):
    session.add(db_message)
    session.commit()


def delete_db_message(message_id: int) -> bool:
    db_message = session.get(DBMessage, message_id)
    if db_message:
        session.delete(db_message)
        session.commit()
        return True
    return False


# <<< DATABASE >>> #
def initialize_database() -> None:
    SQLModel.metadata.create_all(engine)
    migrate_to_sqlmodel()


def migrate_to_sqlmodel() -> None:
    old_db = Path("servers.db")
    if old_db.is_file():
        with sqlite3.connect('servers.db') as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users")
            data = cursor.fetchall()
            for user in data:
                db_user = get_or_create_db_user(user_id=user[0])
                db_user.is_inbox_open = user[1]
                db_user.inbox_title = user[2]
                update_db_user(db_user)

            cursor.execute("SELECT * FROM asks")
            data = cursor.fetchall()
            for message in data:
                create_db_message(message_id=message[0], origin=message[1])

        old_db.unlink()
