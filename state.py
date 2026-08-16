from typing import TypedDict, Optional, List, Dict, Any, Annotated
import operator


class FlightBookingState(TypedDict):
    origin: str
    destination: str
    start_date: str
    end_date: str

    weather_data: Optional[Dict[str, Any]]
    price_data: Optional[Dict[str, Any]]
    best_date: Optional[str]
    recommendation: Optional[str]
    errors: Annotated[List[str], operator.add]


if __name__ == "__main__":
    sample: FlightBookingState = {
        "origin": "BLR",
        "destination": "GOI",
        "start_date": "2026-08-05",
        "end_date": "2026-08-08",
        "weather_data": None,
        "price_data": None,
        "best_date": None,
        "recommendation": None,
        "errors": []
    }
    print(sample)