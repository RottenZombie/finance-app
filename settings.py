import json
import os

FILE = "config.json"


DEFAULT = {
    "theme": "White",
    "precision": 2,
    "start_tab": 0
}


def load():
    if not os.path.exists(FILE):
        return DEFAULT

    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return DEFAULT


def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=4)

