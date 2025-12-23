import asyncio
import random

from dotenv import load_dotenv
from flask import Flask, render_template, send_from_directory, request, redirect, url_for
import os

import bot
import dbconnection
import utils
from bot import message_queue
from dbconnection import DBUser

load_dotenv()
WEBSITE_PORT: int = int(os.getenv('WEBSITE_PORT', '5000'))

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")


@app.route('/', methods=['GET'])
def main_page():
    """
    Renders the main page.
    :return:
    """
    return render_template("main_page.html", app_link=utils.localize("template.app_link"))


@app.route('/tos', methods=['GET'])
def tos_page():
    """
    Renders the terms of service page.
    :return:
    """
    return render_template("tos_page.html")


@app.route('/privacy', methods=['GET'])
def privacy_page():
    """
    Renders the privacy policy page.
    :return:
    """
    return render_template("privacy_page.html")


@app.errorhandler(404)
def not_found(_e=None):
    """
    Renders the 404 not found page.
    Plus some funnies.
    """
    flavor_text = utils.localize(f"website.404.flavor_text_{random.randint(1, 10)}")
    return render_template("not_found_page.html", flavor_text=flavor_text)


@app.route('/<username>', methods=['GET'])
def send_page(username: str):
    """
    Renders the send message page for the given username.
    404 if the user does not exist.
    If the user's inbox is closed, shows a disabled page.
    If a message is provided in the query parameters, sends the message and redirects to the sent page.
    :param username:
    :return:
    """

    db_user = dbconnection.get_db_user_by_username(username)
    if not db_user:
        return not_found()
    if not db_user.is_inbox_open:
        disabled_title = utils.localize("website.disabled_page.title")
        disabled_header = utils.localize("website.disabled_page.header").format(username)
        disabled_description = utils.localize("website.disabled_page.description")
        return render_template("disabled_page.html", disabled_title=disabled_title,
                               disabled_header=disabled_header, disabled_description=disabled_description)
    message = request.args.get('message', type=str)
    if message:
        send_message(db_user, message)
        return redirect(url_for('sent_page', username=username))
    return render_template(
        "send_page.html", username=username, inbox_title=db_user.inbox_title,
        user_avatar=db_user.avatar_url, placeholder=utils.localize("website.send_page.placeholder"))


@app.route('/sent', methods=['GET'])
def sent_page():
    """
    Renders the sent confirmation page.
    Also uses the username query parameter to show who the message was sent to.
    :return:
    """
    username = request.args.get('username', type=str)

    if not username:
        return redirect(url_for('main_page'))
    sent_title = utils.localize("website.sent_page.title")
    sent_header = utils.localize("website.sent_page.header").format(username)
    again = utils.localize("website.sent_page.again")
    return render_template("sent_page.html",
                           sent_title=sent_title, sent_header=sent_header, again=again)


@app.route('/favicon.ico', methods=['GET'])
def favicon():
    """
    Serves the favicon.
    :return:
    """
    return send_from_directory(os.path.join(app.root_path, 'web/static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


async def run_website():
    """
    Runs the website using Hypercorn.
    :return:
    """
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = [f"localhost:{WEBSITE_PORT}"]
    await serve(app, config)


def send_message(to_user: DBUser, message: str) -> None:
    """
    Sends a message to the given user by putting it in the bot's message queue.
    :param to_user:
    :param message:
    :return:
    """
    asyncio.run_coroutine_threadsafe(message_queue.put((to_user.user_id, message)), bot.bot.loop)
