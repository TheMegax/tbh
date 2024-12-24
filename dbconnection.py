import sqlite3
from pathlib import Path

import utils

from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session

origins = ['unknown', 'server', 'group_chat', 'direct_message']


class DBUser(SQLModel, table=True):
    user_id: int = Field(primary_key=True)
    username: Optional[str] = Field(default="")
    is_inbox_open: Optional[bool] = Field(default=False)
    inbox_title: Optional[str] = Field(default=utils.localize("template.default_inbox_title"))


class DBMessage(SQLModel, table=True):
    message_id: int = Field(primary_key=True)
    origin: Optional[str] = Field(default=origins[0])


engine = create_engine("sqlite:///database.db")


# <<< USERS >>> #
def get_or_create_db_user(user_id: int, username: str) -> DBUser | None:
    with Session(engine) as session:
        db_user = session.get(DBUser, user_id)
        # Updating the username
        if db_user and db_user.username != username:
            db_user.username = username
            session.add(db_user)
            session.commit()
        elif not db_user:
            utils.formatlog(f'Adding new user with ID "{user_id}"')
            db_user = DBUser(user_id=user_id, username=username)
            session.add(db_user)
            session.commit()
        return db_user


def update_db_user(db_user: DBUser):
    with Session(engine) as session:
        session.add(db_user)
        session.commit()


# <<< MESSAGES >>> #
def get_db_message(message_id: int) -> DBMessage | None:
    with Session(engine) as session:
        return session.get(DBMessage, message_id)


def create_db_message(message_id: int, origin: str) -> None:
    with Session(engine) as session:
        db_message = session.get(DBMessage, message_id)
        if not db_message:
            utils.formatlog(f'Creating new message with ID "{message_id}" and origin "{origin}"')
            db_message = DBMessage(message_id=message_id, origin=origin)
            session.add(db_message)
            session.commit()


def update_db_message(db_message: DBMessage):
    with Session(engine) as session:
        session.add(db_message)
        session.commit()


def delete_db_message(message_id: int) -> bool:
    with Session(engine) as session:
        db_message = session.get(DBMessage, message_id)
        if db_message:
            session.delete(db_message)
            session.commit()
            return True
    return False


# <<< DATABASE >>> #
async def initialize_database() -> None:
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
                db_user = get_or_create_db_user(user_id=user[0], username="")
                db_user.is_inbox_open = user[1]
                db_user.inbox_title = user[2]
                update_db_user(db_user)

            cursor.execute("SELECT * FROM asks")
            data = cursor.fetchall()
            for message in data:
                create_db_message(message_id=message[0], origin=message[1])

        old_db.unlink()
