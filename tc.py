import time
from pathlib import Path
import tomllib
from urllib.parse import urljoin, urlencode

import requests

BASE_DIR = Path(__file__).parent

CONFIG_FILE = BASE_DIR / "config.toml"

EVENT_INDEXER_API_URL = "https://eventindexer.katla.taiko.xyz/"
HTTP_TIMEOUT = 10
INTERVAL = 3

def validate_address(value):
    if not isinstance(value, str):
        return False
    if not value.startswith("0x"):
        return False
    if len(value) != 42:
        return False

    return True

def load_config(path):
    with path.open("rb") as fp:
        raw_config = tomllib.load(fp)

    address_list = raw_config.get("address_list", [])
    slack_webhook_url = raw_config.get("slack_webhook_url", "")
    api_base = raw_config.get("api_base", EVENT_INDEXER_API_URL)
    interval = raw_config.get("interval", INTERVAL)

    return {
        "address_list": [a for a in address_list if validate_address(a)],
        "slack_webhook_url": slack_webhook_url,
        "api_base": api_base,
        "interval": int(interval)
    }

def notify_to_slack(webhook_url, msg):
    data = { "text": str(msg) }
    headers = { "Content-type": "application/json" }
    response = requests.post(webhook_url, json=data, headers=headers, timeout=HTTP_TIMEOUT)
    response.raise_for_status()

def fetch_address_events(base_url, event, address):
    params = {
        "address": address,
        "event": event,
    }
    event_url = urljoin(base_url, "eventByAddress") + "?" + urlencode(params)
    response = requests.get(event_url, timeout=HTTP_TIMEOUT, headers={"Accept": "application/json"})
    response.raise_for_status()
    data = response.json()
    return data["count"]

def main():
    config = load_config(CONFIG_FILE)
    interval = config["interval"]
    base_url = config["api_base"]
    msgs = []
    for address in config["address_list"]:
        proposed = fetch_address_events(base_url, "BlockProposed", address)
        time.sleep(interval)

        proven = fetch_address_events(base_url, "BlockProven", address)
        time.sleep(interval)

        msgs.append("- {address} proposed: {proposed:,}, proven: {proven:,}".format(
            address=address,
            proposed=proposed,
            proven=proven,
        ))

    if not msgs:
        return

    msg = "\n".join(msgs)
    if slack_webhook_url := config["slack_webhook_url"]:
        notify_to_slack(slack_webhook_url, msg)
    else:
        print(msg)

if __name__ == "__main__":
    main()
