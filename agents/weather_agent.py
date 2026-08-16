from datetime import date, timedelta

from shared_utils.cache import get_cached, set_cached
from shared_utils.mock_weather import get_mock_weather

NAMESPACE = "flight_weather"


def _compute_risk_score(day_forecast: dict) -> int:
    rainfall = day_forecast["rainfall_mm"]
    wind = day_forecast["wind_speed_kmph"]

    score = 0
    if rainfall > 30:
        score += 5
    elif rainfall > 10:
        score += 3
    elif rainfall > 0:
        score += 1

    if wind > 20:
        score += 4
    elif wind > 12:
        score += 2

    return min(score, 10)


def get_weather_for_date(location: str, target_date: str) -> dict:
    cached_result = get_cached(NAMESPACE, location, target_date)
    if cached_result is not None:
        print(f"[weather_agent] Cache HIT for {location} on {target_date}")
        cached_result["from_cache"] = True
        return cached_result

    print(f"[weather_agent] Cache MISS for {location} on {target_date} — fetching")

    target = date.fromisoformat(target_date)
    today = date.today()
    day_offset = (target - today).days

    weather_bundle = get_mock_weather(location, season="Kharif")
    forecast = weather_bundle["forecast_7_day"]

    if 0 <= day_offset < len(forecast):
        day_data = forecast[day_offset]
    else:
        day_data = forecast[-1]

    result = {
        "location": location,
        "date": target_date,
        "temperature_c": day_data["temperature_c"],
        "rainfall_mm": day_data["rainfall_mm"],
        "wind_speed_kmph": day_data["wind_speed_kmph"],
        "risk_score": _compute_risk_score(day_data),
        "from_cache": False
    }

    set_cached(NAMESPACE, result, location, target_date)
    return result


if __name__ == "__main__":
    test_date = (date.today() + timedelta(days=2)).isoformat()
    result = get_weather_for_date("Goa", test_date)
    print(result)

    print("\n--- Running again (should be cache hit) ---")
    result2 = get_weather_for_date("Goa", test_date)
    print(result2)