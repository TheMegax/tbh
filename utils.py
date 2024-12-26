import os
from string import Template

from PIL import Image
from dotenv import load_dotenv

import html
import json
from datetime import datetime

load_dotenv()
BROWSER: str = os.getenv('HTML2IMAGE_BROWSER', 'chrome')
BROWSER_LOCATION: str = os.getenv('HTML2IMAGE_BROWSER_LOCATION')
USE_HTML_JSON_SERVICE: bool = bool(int(os.getenv('USE_HTML_JSON_SERVICE', "0")))
SERVICE_PORT: str = os.getenv('SERVICE_PORT')

if USE_HTML_JSON_SERVICE:
    import requests
else:
    from html2image import Html2Image

    hti = Html2Image(disable_logging=True, browser=BROWSER, browser_executable=BROWSER_LOCATION)

with open("localization/en-US.json") as f:
    localization: dict = json.load(f)


def localize(key: str):
    if key not in localization:
        return key
    return localization[key]


def formatlog(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[{0}]    {1}".format(timestamp, msg))


def generate_image(template_path: str, substitutions: dict, img_id: int) -> str:
    escaped_substitutions = {key: html.escape(value) for key, value in substitutions.items()}

    with open(template_path, "r") as file:
        data = file.read()

        html_temp = Template(data)
        html_filled = html_temp.substitute(**escaped_substitutions)
        output_name = f"{img_id}.png"
        screenshot_and_crop(html_str=html_filled, save_as=output_name)

    return output_name


def generate_link_image(inbox_title: str, img_id: int) -> str:
    return generate_image(
        template_path="web/html-render/link.html",
        substitutions={"ask_title": inbox_title},
        img_id=img_id
    )


def generate_message_image(inbox_title: str, msg: str, img_id: int) -> str:
    return generate_image(
        template_path="web/html-render/answer.html",
        substitutions={"ask_title": inbox_title, "ask_msg": msg},
        img_id=img_id
    )


def screenshot_and_crop(html_str: str, save_as: str):
    if USE_HTML_JSON_SERVICE:
        json_data = {
            'html': html_str,
            'export': {
                'type': 'png'
            },
        }
        response = requests.post(f'http://localhost:{SERVICE_PORT}/1/screenshot', json=json_data)

        with open(save_as, 'wb') as img:
            img.write(response.content)
    else:
        hti.screenshot(html_str=html_str, save_as=save_as)
    im = Image.open(save_as)
    width, height = im.size
    p1_x = 300
    p1_y = 50
    p2_x = width - 300
    p2_y = height - 50

    im.crop((p1_x, p1_y, p2_x, p2_y)).save(save_as)
