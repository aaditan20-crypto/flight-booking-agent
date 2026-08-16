from datetime import date, timedelta

from shared_utils.ollama_client import ask_ollama

from langgraph.graph import StateGraph, START, END
from state import FlightBookingState
from agents.weather_agent import get_weather_for_date
from agents.price_agent import get_price_for_date


RECOMMENDATION_SYSTEM_PROMPT = """You are a Flight Booking Assistant.
You receive weather and price data for MULTIPLE candidate travel dates on the
same route, plus which date was algorithmically picked as the best overall option.
Write a short, friendly, practical recommendation (4-6 sentences max) explaining
why that date is the best choice, briefly comparing it to at least one other
date's tradeoff (e.g. cheaper but riskier, or safer but pricier). No JSON, plain text.
"""


def _date_range(start_date: str, end_date: str) -> list:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def weather_node(state: FlightBookingState) -> dict:
    weather_by_date = {}
    errors = []
    for d in _date_range(state["start_date"], state["end_date"]):
        try:
            weather_by_date[d] = get_weather_for_date(state["destination"], d)
        except Exception as e:
            errors.append(f"Weather agent failed for {d}: {e}")
    return {"weather_data": weather_by_date, "errors": errors}


def price_node(state: FlightBookingState) -> dict:
    price_by_date = {}
    errors = []
    for d in _date_range(state["start_date"], state["end_date"]):
        try:
            price_by_date[d] = get_price_for_date(state["origin"], state["destination"], d)
        except Exception as e:
            errors.append(f"Price agent failed for {d}: {e}")
    return {"price_data": price_by_date, "errors": errors}


def pick_best_date_node(state: FlightBookingState) -> dict:
    weather = state.get("weather_data") or {}
    price = state.get("price_data") or {}

    common_dates = set(weather.keys()) & set(price.keys())
    if not common_dates:
        return {"best_date": None}

    def combined_score(d):
        risk = weather[d]["risk_score"]
        cheapest = price[d]["cheapest_price"]
        return (risk * 500) + cheapest

    best = min(common_dates, key=combined_score)
    return {"best_date": best}


def recommendation_node(state: FlightBookingState) -> dict:
    weather = state.get("weather_data") or {}
    price = state.get("price_data") or {}
    best_date = state.get("best_date")

    if not weather or not price or not best_date:
        return {"recommendation": "Could not generate a recommendation due to missing data."}

    comparison_lines = []
    for d in sorted(weather.keys()):
        w = weather[d]
        p = price[d]
        marker = " <-- BEST OVERALL PICK" if d == best_date else ""
        comparison_lines.append(
            f"{d}: risk_score={w['risk_score']}/10, rainfall={w['rainfall_mm']}mm, "
            f"cheapest_price={p['cheapest_price']} INR{marker}"
        )

    user_message = f"""
Route: {state['origin']} -> {state['destination']}
Candidate dates comparison:
{chr(10).join(comparison_lines)}

Best overall pick: {best_date}
"""

    recommendation_text = ask_ollama(RECOMMENDATION_SYSTEM_PROMPT, user_message)
    return {"recommendation": recommendation_text}


def build_graph():
    graph = StateGraph(FlightBookingState)

    graph.add_node("weather_node", weather_node)
    graph.add_node("price_node", price_node)
    graph.add_node("pick_best_date_node", pick_best_date_node)
    graph.add_node("recommendation_node", recommendation_node)

    graph.add_edge(START, "weather_node")
    graph.add_edge(START, "price_node")

    graph.add_edge("weather_node", "pick_best_date_node")
    graph.add_edge("price_node", "pick_best_date_node")

    graph.add_edge("pick_best_date_node", "recommendation_node")
    graph.add_edge("recommendation_node", END)

    return graph.compile()


if __name__ == "__main__":
    app = build_graph()

    initial_state: FlightBookingState = {
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

    final_state = app.invoke(initial_state)
    print("\n=== BEST DATE ===")
    print(final_state["best_date"])
    print("\n=== RECOMMENDATION ===")
    print(final_state["recommendation"])
    print("\n=== ERRORS ===")
    print(final_state["errors"])