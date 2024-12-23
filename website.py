from flask import Flask, render_template

app = Flask(__name__, template_folder="web/templates")


@app.route('/')
def main_page():
    return render_template("send_page.html")


async def run_website():
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:5000"]
    await serve(app, config)
