import json
from datetime import datetime

with open("localization/en-US.json") as f:
    localization: dict = json.load(f)


def localize(key: str):
    if key not in localization:
        return key
    return localization[key]


def formatlog(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[{0}]    {1}".format(timestamp, msg))
