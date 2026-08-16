import random
from datetime import date, timedelta

def get_mock_weather(location: str, season: str = "Kharif") -> dict:
    season = season.strip().capitalize()

    season_profiles = {
        "Kharif": (24, 34, 40, 0.7),
        "Rabi": (10, 25, 10, 0.15),
        "Summer": (28, 42, 5, 0.05)
    }

    temp_min, temp_max, rainfall_max, rainfall_chance = season_profiles.get(
        season, (24, 34, 40, 0.7)
    )

    today = date.today()
    forecast = []
    for day_offset in range(0, 7):
        forecast_date = today + timedelta(days=day_offset)
        will_rain = random.random() < rainfall_chance
        rainfall = round(random.uniform(0, rainfall_max), 1) if will_rain else 0.0

        forecast.append({
            "day": day_offset + 1,
            "date": forecast_date.strftime("%A, %d %B %Y"),
            "temperature_c": round(random.uniform(temp_min, temp_max), 1),
            "humidity_percent": round(random.uniform(30, 85), 1),
            "rainfall_mm": rainfall,
            "wind_speed_kmph": round(random.uniform(5, 25), 1)
        })

    return {
        "location": location,
        "season": season,
        "forecast_7_day": forecast
    }