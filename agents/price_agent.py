import random
from datetime import date, timedelta

from shared_utils.cache import get_cached, set_cached

NAMESPACE = "flight_price"

AIRLINES = ["IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air"]


def get_mock_price(origin: str, destination: str, target_date: str) -> dict:
    random.seed(f"{origin}_{destination}_{target_date}")

    base_price = random.randint(3000, 9000)
    flights = []
    for airline in random.sample(AIRLINES, k=3):
        price_variation = random.randint(-500, 1500)
        flights.append({
            "airline": airline,
            "price": base_price + price_variation,
            "departure_time": f"{random.randint(5, 22)}:{random.choice(['00', '15', '30', '45'])}",
            "duration_hours": round(random.uniform(1.5, 4.0), 1)
        })

    flights.sort(key=lambda f: f["price"])

    return {
        "origin": origin,
        "destination": destination,
        "date": target_date,
        "flights": flights,
        "cheapest_price": flights[0]["price"]
    }


def get_price_for_date(origin: str, destination: str, target_date: str) -> dict:
    cached_result = get_cached(NAMESPACE, origin, destination, target_date)
    if cached_result is not None:
        print(f"[price_agent] Cache HIT for {origin}->{destination} on {target_date}")
        cached_result["from_cache"] = True
        return cached_result

    print(f"[price_agent] Cache MISS for {origin}->{destination} on {target_date} — fetching")
    result = get_mock_price(origin, destination, target_date)
    result["from_cache"] = False
    set_cached(NAMESPACE, result, origin, destination, target_date)
    return result


if __name__ == "__main__":
    test_date = (date.today() + timedelta(days=2)).isoformat()
    result = get_price_for_date("BLR", "GOI", test_date)
    print(result)

    print("\n--- Running again (should be cache hit) ---")
    result2 = get_price_for_date("BLR", "GOI", test_date)
    print(result2)