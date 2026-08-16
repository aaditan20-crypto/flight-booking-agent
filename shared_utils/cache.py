import json
import os
import hashlib
from datetime import datetime, timedelta

AGRI_APP_PATH = r"C:\Users\aadit\smart-agri-assistant"
AGRI_CACHE_FILE = os.path.join(AGRI_APP_PATH, "app_cache.json")
LOCAL_CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "flight_app_cache.json")

# Use agri app's shared cache if it exists on this machine, otherwise use our own
if os.path.exists(AGRI_APP_PATH):
    CACHE_FILE = AGRI_CACHE_FILE
    print(f"[cache] Using shared agri app cache: {CACHE_FILE}")
else:
    CACHE_FILE = LOCAL_CACHE_FILE
    print(f"[cache] Agri app not found on this machine — using local cache: {CACHE_FILE}")

CACHE_VALID_HOURS = 6


def _make_cache_key(*parts) -> str:
    raw_key = "_".join(str(p).strip().lower() for p in parts)
    return hashlib.md5(raw_key.encode()).hexdigest()


def _load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_cache(cache: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_cached(namespace: str, *key_parts):
    cache = _load_cache()
    key = f"{namespace}_{_make_cache_key(*key_parts)}"

    if key not in cache:
        return None

    entry = cache[key]
    cached_time = datetime.fromisoformat(entry["cached_at"])
    if datetime.now() - cached_time > timedelta(hours=CACHE_VALID_HOURS):
        return None

    return entry["data"]


def set_cached(namespace: str, data: dict, *key_parts):
    cache = _load_cache()
    key = f"{namespace}_{_make_cache_key(*key_parts)}"
    cache[key] = {
        "cached_at": datetime.now().isoformat(),
        "data": data
    }
    _save_cache(cache)