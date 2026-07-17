import os
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("BRIGHT_DATA_API_KEY")

BASE_URL = "https://api.brightdata.com/datasets/v3"


def _session():
    """A requests session that automatically retries transient network failures
    (DNS blips, connection resets, 5xx errors) instead of failing immediately —
    important here since polling can run for several minutes at a time."""
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,  # 2s, 4s, 8s, 16s, 32s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _error_detail(e):
    """Pull Bright Data's actual error body out of a failed response, since
    raise_for_status() alone discards it and just gives a generic 400/500 message."""
    response = getattr(e, "response", None)
    if response is not None:
        try:
            return response.json()
        except ValueError:
            return response.text.strip() or str(e)
    return str(e)


def trigger_scraping_niche(api_key, keyword, num_of_posts, start_date, end_date, country, endpoint):
    payload = [{
        "keyword": keyword,
        "num_of_posts": num_of_posts,
        "start_date": start_date,
        "end_date": end_date,
        "country": country,
    }]

    try:
        response = _session().post(endpoint, headers=_headers(api_key), json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        detail = _error_detail(e)
        print(f"Error triggering niche scrape: {detail}")
        return {"error": detail}


def trigger_scraping_channels(api_key, channel_urls, num_of_posts, start_date, end_date, order_by, country):
    dataset_id = "gd_lk56epmy2i5g7lzu0k"
    endpoint = (
        f"{BASE_URL}/trigger?dataset_id={dataset_id}"
        f"&include_errors=true&type=discover_new&discover_by=url"
    )

    payload = [
        {
            "url": url,
            "num_of_posts": num_of_posts,
            "start_date": start_date,
            "end_date": end_date,
            "order_by": order_by,
            "country": country,
        }
        for url in channel_urls
    ]

    try:
        response = _session().post(endpoint, headers=_headers(api_key), json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        detail = _error_detail(e)
        print(f"Error triggering channel scrape: {detail}")
        return {"error": detail}


def get_progress(api_key, snapshot_id):
    endpoint = f"{BASE_URL}/progress/{snapshot_id}"
    try:
        response = _session().get(endpoint, headers=_headers(api_key), timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        detail = _error_detail(e)
        print(f"Error getting progress: {detail}")
        return {"error": detail}


def get_output(api_key, snapshot_id, format="json"):
    endpoint = f"{BASE_URL}/snapshot/{snapshot_id}?format={format}"
    try:
        response = _session().get(endpoint, headers=_headers(api_key), timeout=120)
        response.raise_for_status()
        text = response.text.strip()

        if not text:
            print("Bright Data returned an empty snapshot body.")
            return [[]]

        # Try the whole response as one JSON document first (Bright Data
        # commonly returns a single JSON array here, sometimes pretty-printed
        # across multiple lines, so splitting by "\n" is not reliable).
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [data]
            return [[data]]
        except json.JSONDecodeError:
            pass

        # Fall back to newline-delimited JSON: one full record per line.
        records = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        if not records:
            print("Could not parse any records from Bright Data's response.")
        return [records]
    except requests.exceptions.RequestException as e:
        detail = _error_detail(e)
        print(f"Error getting output: {detail}")
        return None