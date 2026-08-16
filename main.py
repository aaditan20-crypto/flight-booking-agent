from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import random
import string
import secrets

from orchestrator import weather_node, price_node
from shared_utils.ollama_client import ask_ollama
from state import FlightBookingState

app = FastAPI()

session_stats = {"total_tokens": 0, "gemini_calls": 0}

VALID_USERNAME = "admin"
VALID_PASSWORD = "flight123"

active_sessions = {}
user_bookings = {}


def get_current_user(request: Request) -> Optional[str]:
    token = request.cookies.get("session_token")
    if token and token in active_sessions:
        return active_sessions[token]
    return None


def require_login(request: Request) -> str:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return user


class LoginRequest(BaseModel):
    username: str
    password: str


class TripRequest(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    preferred_airline: Optional[str] = None


class ExplainRequest(BaseModel):
    origin: str
    destination: str
    date: str
    risk_score: float
    rainfall_mm: float
    cheapest_price: float
    airline: str


class BookRequest(BaseModel):
    origin: str
    destination: str
    date: str
    airline: str
    price: float
    departure_time: str


@app.post("/api/login")
def login(req: LoginRequest, response: Response):
    if req.username == VALID_USERNAME and req.password == VALID_PASSWORD:
        token = secrets.token_hex(16)
        active_sessions[token] = req.username
        response.set_cookie(key="session_token", value=token, httponly=True, max_age=3600 * 8)
        return {"status": "success"}
    raise HTTPException(status_code=401, detail="Invalid username or password")


@app.post("/api/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token in active_sessions:
        del active_sessions[token]
    response.delete_cookie("session_token")
    return {"status": "logged_out"}


@app.get("/")
def serve_root(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login.html")
    return FileResponse("static/app.html")


@app.get("/login.html")
def serve_login():
    return FileResponse("static/login.html")


@app.post("/api/plan-trip")
def plan_trip(req: TripRequest, user: str = Depends(require_login)):
    state: FlightBookingState = {
        "origin": req.origin.upper(),
        "destination": req.destination.upper(),
        "start_date": req.start_date,
        "end_date": req.end_date,
        "weather_data": None,
        "price_data": None,
        "best_date": None,
        "recommendation": None,
        "errors": []
    }

    weather_result = weather_node(state)
    price_result = price_node(state)

    weather = weather_result.get("weather_data", {})
    price = price_result.get("price_data", {})
    errors = weather_result.get("errors", []) + price_result.get("errors", [])

    airline_filter = req.preferred_airline.strip() if req.preferred_airline else None
    if airline_filter and airline_filter.lower() == "any":
        airline_filter = None

    comparison = []
    for d in sorted(weather.keys()):
        w = weather[d]
        p = price.get(d, {})
        all_flights = p.get("flights", [])

        if airline_filter:
            filtered_flights = [f for f in all_flights if f["airline"].lower() == airline_filter.lower()]
        else:
            filtered_flights = all_flights

        cheapest = filtered_flights[0]["price"] if filtered_flights else None

        comparison.append({
            "date": d,
            "risk_score": w["risk_score"],
            "rainfall_mm": w["rainfall_mm"],
            "temperature_c": w["temperature_c"],
            "wind_speed_kmph": w["wind_speed_kmph"],
            "cheapest_price": cheapest,
            "flights": filtered_flights,
            "weather_from_cache": w.get("from_cache", False),
            "price_from_cache": p.get("from_cache", False)
        })

    return {
        "comparison": comparison,
        "errors": errors,
        "session_stats": session_stats,
        "filtered_by_airline": airline_filter
    }


@app.post("/api/explain-date")
def explain_date(req: ExplainRequest, user: str = Depends(require_login)):
    user_message = f"""
Route: {req.origin} -> {req.destination}
Date: {req.date}
Weather risk score: {req.risk_score}/10
Rainfall: {req.rainfall_mm}mm
Cheapest flight: {req.cheapest_price} INR ({req.airline})

Explain in 2-3 short sentences whether this looks like a good day to fly, mentioning
the price and weather tradeoff in plain, friendly language.
"""
    try:
        explanation = ask_ollama(
            "You are a helpful flight booking assistant. Be concise and practical.",
            user_message
        )
    except Exception as e:
        explanation = (
            "🤖 AI-powered explanations run on a local AI model (Ollama) and are only "
            "available when this app is running on the developer's own machine. "
            f"Here's the raw data instead: risk score {req.risk_score}/10, "
            f"rainfall {req.rainfall_mm}mm, cheapest flight ₹{req.cheapest_price} with {req.airline}."
        )

    estimated_tokens = int((len(user_message.split()) + len(explanation.split())) * 1.3)
    session_stats["total_tokens"] += estimated_tokens
    session_stats["gemini_calls"] += 1

    return {"explanation": explanation, "session_stats": session_stats}


@app.post("/api/book-flight")
def book_flight(req: BookRequest, user: str = Depends(require_login)):
    ref_code = "FB-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    booking = {
        "booking_reference": ref_code,
        "origin": req.origin,
        "destination": req.destination,
        "date": req.date,
        "airline": req.airline,
        "price": req.price,
        "departure_time": req.departure_time
    }
    user_bookings.setdefault(user, []).insert(0, booking)
    return {"status": "confirmed", **booking}


@app.get("/api/my-bookings")
def my_bookings(user: str = Depends(require_login)):
    return {"bookings": user_bookings.get(user, [])}


@app.get("/api/session-stats")
def get_session_stats(user: str = Depends(require_login)):
    return session_stats


@app.get("/api/whoami")
def whoami(request: Request):
    user = get_current_user(request)
    return {"logged_in": user is not None, "username": user}


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)