import os
from string import Template

from PIL import Image, ImageChops
from dotenv import load_dotenv

import html
import json
from datetime import datetime

load_dotenv()
BROWSER: str = os.getenv('HTML2IMAGE_BROWSER', 'chrome')
BROWSER_LOCATION: str = os.getenv('HTML2IMAGE_BROWSER_LOCATION')
USE_HTML_JSON_SERVICE: bool = bool(int(os.getenv('USE_HTML_JSON_SERVICE', "0")))
SERVICE_PORT: str = os.getenv('SERVICE_PORT')

with open("localization/en-US.json") as f:
    localization: dict = json.load(f)


def localize(key: str):
    """
    Retrieves the localized string for the given key.
    If the key does not exist, it returns the key itself.
    :param key:
    :return:
    """
    if key not in localization:
        return key
    return localization[key]


def formatlog(msg: str):
    """
    Formats and prints a log message with a timestamp.
    :param msg:
    :return:
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[{0}]    {1}".format(timestamp, msg))


if USE_HTML_JSON_SERVICE:
    import requests

    formatlog("Using HTML to Image JSON service for rendering.")
else:
    from html2image import Html2Image

    hti = Html2Image(disable_logging=True, browser=BROWSER, browser_executable=BROWSER_LOCATION)
    formatlog("Using html2image library for rendering.")


def generate_image(template_path: str, substitutions: dict, img_id: int) -> str:
    """
    Generates an image from an HTML template and substitutions.
    Note: This does NOT check if the image was generated successfully.
    :param template_path:
    :param substitutions:
    :param img_id:
    :return:
    """
    escaped_substitutions = {
        key: value if key.endswith('_html') else html.escape(str(value)).replace('\n', '<br>')
        for key, value in substitutions.items()
    }

    with open(template_path, "r") as file:
        data = file.read()

        html_temp = Template(data)
        html_filled = html_temp.substitute(**escaped_substitutions)
        output_name = f"{img_id}.png"
        screenshot_and_crop(html_str=html_filled, save_as=output_name)

    return output_name


def generate_link_image(inbox_title: str, img_id: int) -> str:
    """
    Generates an image for the link preview.
    :param inbox_title:
    :param img_id:
    :return:
    """
    return generate_image(
        template_path="web/html-render/link.html",
        substitutions={"ask_title": inbox_title},
        img_id=img_id
    )


def generate_message_image(inbox_title: str, msg: str, img_id: int, image_data: str = None) -> str:
    """
    Generates an image for the inbox message.
    :param inbox_title:
    :param msg:
    :param img_id:
    :param image_data:
    :return:
    """
    return generate_image(
        template_path="web/html-render/answer.html",
        substitutions={
            "ask_title": inbox_title,
            "ask_msg": msg,
            "attached_image_html": f'<hr style="border: 0; border-top: 4px solid rgba(0,0,0,0.1); width: 90%; margin: '
                                   f'10px 0;"><img src="{image_data}" class="embedded-image" />' if image_data else ""
        },
        img_id=img_id
    )


def screenshot_and_crop(html_str: str, save_as: str):
    """
    Takes a screenshot of the given HTML string and crops the result.
    :param html_str:
    :param save_as:
    :return:
    """
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
        hti.screenshot(html_str=html_str, save_as=save_as, size=(1920, 4000))

    im_rgb = Image.open(save_as).convert('RGB')
    bg = Image.new('RGB', im_rgb.size, (228, 228, 255))
    diff = ImageChops.difference(im_rgb, bg)
    bbox = diff.getbbox()

    if bbox:
        padding_y = 60
        padding_x = 80
        left, upper, right, lower = bbox
        left = max(0, left - padding_x)
        upper = max(0, upper - padding_y)
        right = min(im_rgb.width, right + padding_x)
        lower = min(im_rgb.height, lower + padding_y)

        im_original = Image.open(save_as)
        im_original.crop((left, upper, right, lower)).save(save_as)
