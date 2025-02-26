import asyncio
import json
import time
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

# In-memory mocks for persistence
users = {}
gyms_cache = {}       # key: gym_id, value: gym details
reviews_cache = {}    # key: gym_id, value: list of reviews
bookings_cache = {}   # key: user_id, value: list of bookings

# TODO: Replace these URLs with the actual GymAPI endpoints.
GYM_AVAILABILITY_URL = "https://api.example.com/gym/availability"  # Placeholder
GYM_PRICING_URL = "https://api.example.com/gym/pricing"            # Placeholder
GYM_SCHEDULE_URL = "https://api.example.com/gym/schedule"          # Placeholder

# Data models for request validation using primitives only.
@dataclass
class UserRegisterReq:
    name: str
    email: str
    password: str

@dataclass
class UserLoginReq:
    email: str
    password: str

@dataclass
class GymSearchReq:
    latitude: float
    longitude: float
    workoutType: str  # Using only one workout type for prototype simplicity.
    minPrice: float
    maxPrice: float
    sortBy: str

@dataclass
class GymBookReq:
    userId: str
    gymId: str
    sessionDate: str
    timeSlot: str

@dataclass
class GymReviewReq:
    userId: str
    gymId: str
    rating: int
    comment: str

@dataclass
class BookingsQuery:
    userId: str

async def fetch_gym_api(url, payload):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    # TODO: Handle specific non-200 responses as needed.
                    return None
        except Exception as e:
            print(f"GymAPI request failed: {e}")
            return None

# POST endpoints: Validation decorator is placed after the route decorator (workaround for quart-schema issue).
@app.route("/auth/register", methods=["POST"])
@validate_request(UserRegisterReq)  # Workaround: For POST, validation goes after route.
async def register(data: UserRegisterReq):
    email = data.email
    if not email:
        return jsonify({"error": "Email required"}), 400
    if email in users:
        return jsonify({"error": "User already exists"}), 400

    user_id = str(uuid4())
    users[email] = {
        "user_id": user_id,
        "name": data.name,
        "password": data.password  # TODO: Encrypt password in production
    }
    return jsonify({"message": "User registered successfully", "userId": user_id})

@app.route("/auth/login", methods=["POST"])
@validate_request(UserLoginReq)  # Workaround: For POST, validation goes after route.
async def login(data: UserLoginReq):
    email = data.email
    password = data.password
    user = users.get(email)
    if not user or user.get("password") != password:
        return jsonify({"error": "Invalid credentials"}), 401

    # TODO: Replace with real JWT token generation.
    token = "dummy.jwt.token." + user["user_id"]
    return jsonify({"token": token, "userId": user["user_id"]})

@app.route("/gyms/search", methods=["POST"])
@validate_request(GymSearchReq)  # Workaround: For POST, validation goes after route.
async def gyms_search(data: GymSearchReq):
    # Prepare payload for external GymAPI calls using validated data.
    availability_payload = {
        "location": {
            "latitude": data.latitude,
            "longitude": data.longitude
        },
        "date": datetime.now().strftime("%Y-%m-%d"),
        "workoutType": data.workoutType if data.workoutType else "general"
    }

    pricing_payload = {
        "gymId": "dummy-gym-id"  # TODO: Dynamically set gymId when available
    }

    schedule_payload = {
        "gymId": "dummy-gym-id",  # TODO: Dynamically set gymId when available
        "date": datetime.now().strftime("%Y-%m-%d")
    }

    # Call GymAPI for availability, pricing, and schedule.
    availability_data = await fetch_gym_api(GYM_AVAILABILITY_URL, availability_payload)
    pricing_data = await fetch_gym_api(GYM_PRICING_URL, pricing_payload)
    schedule_data = await fetch_gym_api(GYM_SCHEDULE_URL, schedule_payload)

    # If any call fails, provide fallback options using cached data if available.
    if availability_data is None or pricing_data is None or schedule_data is None:
        # TODO: Implement logic to retrieve cached/alternative data.
        message = "Some of the external data could not be retrieved. Displaying cached results."
        results = list(gyms_cache.values())  # Fallback using cached gyms data
        return jsonify({"message": message, "results": results})

    results = []
    for gym in availability_data.get("gyms", []):
        gym_id = gym.get("gymId")
        gym_details = {
            "gymId": gym_id,
            "name": f"Gym {gym_id}",
            "address": "123 Main Street, City",  # Placeholder
            "rating": 4.5,  # Placeholder
            "services": [data.workoutType] if data.workoutType else ["general"],
            "availability": gym.get("availableSlots"),
            "pricing": pricing_data.get("pricing") if pricing_data else {},
            "schedule": schedule_data.get("schedule") if schedule_data else []
        }
        gyms_cache[gym_id] = gym_details  # Cache gym details for later retrieval
        results.append(gym_details)

    # TODO: Add sorting based on sortBy (price, rating, etc.) if needed.
    return jsonify({"results": results})

@app.route("/gyms/<gym_id>", methods=["GET"])
async def gym_details(gym_id):
    gym = gyms_cache.get(gym_id)
    if not gym:
        return jsonify({"error": "Gym not found"}), 404

    # Retrieve reviews from cache
    gym_reviews = reviews_cache.get(gym_id, [])
    gym["reviews"] = gym_reviews
    return jsonify(gym)

@app.route("/gyms/book", methods=["POST"])
@validate_request(GymBookReq)  # Workaround: For POST, validation goes after route.
async def gym_book(data: GymBookReq):
    if data.gymId not in gyms_cache:
        return jsonify({"error": "Gym not found"}), 404

    booking_id = str(uuid4())
    booking = {
        "bookingId": booking_id,
        "gymId": data.gymId,
        "sessionDate": data.sessionDate,
        "timeSlot": data.timeSlot,
        "status": "processing",
        "requestedAt": datetime.now().isoformat()
    }

    user_bookings = bookings_cache.get(data.userId, [])
    user_bookings.append(booking)
    bookings_cache[data.userId] = user_bookings

    # Fire and forget the processing task.
    asyncio.create_task(process_booking(booking))

    return jsonify({
        "bookingId": booking_id,
        "status": "processing",
        "message": "Booking is being processed. You will be notified upon confirmation."
    })

async def process_booking(booking):
    await asyncio.sleep(2)  # Simulate delay
    # TODO: Replace with actual processing logic (call GymAPI for payment and availability confirmation).
    booking["status"] = "confirmed"
    print(f"Processed booking: {booking['bookingId']} - confirmed.")

@app.route("/gyms/review", methods=["POST"])
@validate_request(GymReviewReq)  # Workaround: For POST, validation goes after route.
async def gym_review(data: GymReviewReq):
    if data.gymId not in gyms_cache:
        return jsonify({"error": "Gym not found"}), 404

    review = {
        "reviewId": str(uuid4()),
        "userId": data.userId,
        "rating": data.rating,
        "comment": data.comment,
        "createdAt": datetime.now().isoformat()
    }
    gym_reviews = reviews_cache.get(data.gymId, [])
    gym_reviews.append(review)
    reviews_cache[data.gymId] = gym_reviews

    return jsonify({"message": "Review submitted successfully", "reviewId": review["reviewId"]})

# GET endpoint with query parameters; validation decorator goes first.
@validate_querystring(BookingsQuery)  # Workaround: For GET, validation goes first.
@app.route("/bookings", methods=["GET"])
async def get_bookings():
    user_id = request.args.get("userId")
    user_bookings = bookings_cache.get(user_id, [])
    return jsonify({"bookings": user_bookings})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)