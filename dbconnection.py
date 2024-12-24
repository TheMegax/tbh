import sqlite3
import utils

from typing import Optional
from sqlmodel import Field, SQLModel


class DBUser(SQLModel, table=True):
    user_id: int = Field(primary_key=True)
    username: Optional[str] = Field(default="")
    is_inbox_open: Optional[bool] = Field(default=False)
    inbox_title: Optional[str] = Field(default=utils.localize("template.default_inbox_title"))


origins = ['unknown', 'server', 'group_chat', 'direct_message']

create_user_table = """
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  are_asks_open INTEGER NOT NULL DEFAULT 0,
  ask_title TEXT DEFAULT 'Send me anonymous messages!'
);
"""

create_ask_table = """
CREATE TABLE IF NOT EXISTS asks (
  ask_id INTEGER PRIMARY KEY,
  origin TEXT DEFAULT 'unknown'
);
"""


class User:
    user_id: int
    are_asks_open: bool
    ask_title: str

    def __init__(self, user_id: int, are_asks_open: bool, ask_title: str):
        self.user_id = user_id
        self.are_asks_open = are_asks_open
        self.ask_title = ask_title


class Ask:
    ask_id: int
    origin: str

    def __init__(self, ask_id: int, origin: str):
        self.ask_id = ask_id
        self.origin = origin


async def get_or_create_user(user_id: int) -> User | None:
    try:
        with sqlite3.connect('servers.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id=?)", (user_id,))
            data = cursor.fetchone()
            if not data[0]:
                utils.formatlog(f'Adding new user with ID {user_id}')
                cursor.execute("INSERT INTO users (user_id) VALUES( ? )", (user_id,))
                conn.commit()
            cursor.execute("SELECT user_id, are_asks_open, ask_title "
                           "FROM users WHERE user_id=?", (user_id,))
            data = cursor.fetchone()
            return User(data[0], bool(data[1]), data[2])
    except sqlite3.Error as e:
        utils.formatlog(f"Could not get user with ID {user_id}!\n{e}")
    return None


async def get_ask(ask_id: int) -> Ask | None:
    try:
        with sqlite3.connect('servers.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM asks WHERE ask_id=?)", (ask_id,))
            data = cursor.fetchone()
            if not data[0]:
                return None
            cursor.execute("SELECT ask_id, origin "
                           "FROM asks WHERE ask_id=?", (ask_id,))
            data = cursor.fetchone()
            return Ask(data[0], data[1])
    except sqlite3.Error as e:
        utils.formatlog(f"Could not get ask with ID {ask_id}!\n{e}")
    return None


async def get_or_create_ask(ask_id: int, origin: str = origins[0]) -> Ask | None:
    try:
        with sqlite3.connect('servers.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM asks WHERE ask_id=?)", (ask_id,))
            data = cursor.fetchone()
            if not data[0]:
                cursor.execute("INSERT INTO asks (ask_id, origin) VALUES( ?, ? )", (ask_id, origin))
                conn.commit()
            cursor.execute("SELECT ask_id, origin "
                           "FROM asks WHERE ask_id=?", (ask_id,))
            data = cursor.fetchone()
            return Ask(data[0], data[1])
    except sqlite3.Error as e:
        utils.formatlog(f"Could not get ask with ID {ask_id}!\n{e}")
    return None


async def remove_ask(ask_id: int) -> bool:
    try:
        with sqlite3.connect('servers.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT EXISTS(SELECT 1 FROM asks WHERE ask_id=?)", (ask_id,))
            data = cursor.fetchone()
            if not data[0]:
                return False
            cursor.execute("DELETE FROM asks WHERE ask_id=?", (ask_id,))
            conn.commit()
            return True
    except sqlite3.Error as e:
        utils.formatlog(f"Could not delete ask with ID {ask_id}!\n{e}")
    return False


async def update_db_column(table_name: str, row_id: int, data_name: str, column: str, value: any) -> bool:
    try:
        with sqlite3.connect('servers.db') as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {table_name} SET {column} = ? WHERE {data_name}=?", (value, row_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        utils.formatlog(f"Could not update {table_name} column {column} in {row_id}!\n{e}")
    return False


async def initialize_database() -> None:
    try:
        with sqlite3.connect('servers.db') as conn:
            cursor = conn.cursor()
            cursor.execute(create_ask_table)
            cursor.execute(create_user_table)
            conn.commit()
    except sqlite3.Error as e:
        utils.formatlog(str(e))
