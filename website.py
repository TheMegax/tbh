import asyncio
from flask import Flask, render_template, send_from_directory, request, redirect
import os

import bot
import dbconnection
from bot import message_queue
from dbconnection import DBUser

app = Flask(__name__, template_folder="web/templates")


@app.route('/', methods=['GET'])
def main_page():
    return render_template("send_page.html")


@app.route('/404', methods=['GET'])
def not_found():
    return render_template("not_found.html")


@app.route('/<username>', methods=['GET'])
def send_page(username: str):
    db_user = dbconnection.get_db_user_by_username(username)
    if not db_user:
        return redirect('/404')
    if not db_user.is_inbox_open:
        return redirect('/404')  # TODO change this
    message = request.args.get('message', default="", type=str)
    if message != "":
        send_message(db_user, message)
    return render_template("send_page.html", username=username, inbox_title=db_user.inbox_title)


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'web/assets'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


async def run_website():
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:5000"]
    await serve(app, config)


def send_message(to_user: DBUser, message: str) -> None:
    asyncio.run_coroutine_threadsafe(message_queue.put((to_user.user_id, message)), bot.bot.loop)
