from flask import Flask, render_template, send_from_directory, request
import os

app = Flask(__name__, template_folder="web/templates")


@app.route('/')
def main_page():
    return render_template("send_page.html")


@app.route('/<username>', methods=['GET'])
def send_page(username: str):
    message = request.args.get('message', default="", type=str)
    return render_template("send_page.html", username=username)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'web/assets'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


async def run_website():
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:5000"]
    await serve(app, config)
