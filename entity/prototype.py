import asyncio
import json
import time
from datetime import datetime
from uuid import uuid4

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

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

@app.route("/auth/register", methods=["POST"])
async def register():
    data = await request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400
    if email in users:
        return jsonify({"error": "User already exists"}), 400

    user_id = str(uuid4())
    users[email] = {
        "user_id": user_id,
        "name": data.get("name"),
        "password": data.get("password")  # TODO: Encrypt password in production
    }
    return jsonify({"message": "User registered successfully", "userId": user_id})

@app.route("/auth/login", methods=["POST"])
async def login():
    data = await request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = users.get(email)
    if not user or user.get("password") != password:
        return jsonify({"error": "Invalid credentials"}), 401

    # TODO: Replace with real JWT token generation.
    token = "dummy.jwt.token." + user["user_id"]
    return jsonify({"token": token, "userId": user["user_id"]})

@app.route("/gyms/search", methods=["POST"])
async def gyms_search():
    # Accept search filters and retrieve gym data from GymAPI with business logic applied.
    data = await request.get_json()
    location = data.get("location")
    workoutTypes = data.get("workoutTypes")
    priceRange = data.get("priceRange")
    sortBy = data.get("sortBy")

    # Prepare payload for external GymAPI calls
    availability_payload = {
        "location": location,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "workoutType": workoutTypes[0] if workoutTypes else "general"
    }

    pricing_payload = {
        "gymId": "dummy-gym-id"  # TODO: Dynamically set gymId when available
    }

    schedule_payload = {
        "gymId": "dummy-gym-id",  # TODO: Dynamically set gymId when available
        "date": datetime.now().strftime("%Y-%m-%d")
    }

    # Call GymAPI for availability
    availability_data = await fetch_gym_api(GYM_AVAILABILITY_URL, availability_payload)
    # Call GymAPI for pricing
    pricing_data = await fetch_gym_api(GYM_PRICING_URL, pricing_payload)
    # Call GymAPI for schedule
    schedule_data = await fetch_gym_api(GYM_SCHEDULE_URL, schedule_payload)

    # If any call fails, provide fallback options using cached data if available.
    if availability_data is None or pricing_data is None or schedule_data is None:
        # TODO: Implement logic to retrieve cached/alternative data.
        message = "Some of the external data could not be retrieved. Displaying cached results."
        results = list(gyms_cache.values())  # Fallback using cached gyms data
        return jsonify({"message": message, "results": results})

    # Build a combined results list from external API responses.
    # For prototype, we assume the data is well-formed.
    results = []
    for gym in availability_data.get("gyms", []):
        gym_id = gym.get("gymId")
        # Combine mocked pricing and schedule with the gym availability.
        gym_details = {
            "gymId": gym_id,
            "name": f"Gym {gym_id}",
            "address": "123 Main Street, City",  # Placeholder
            "rating": 4.5,  # Placeholder
            "services": [workoutTypes[0]] if workoutTypes else ["general"],
            "availability": gym.get("availableSlots"),
            "pricing": pricing_data.get("pricing") if pricing_data else {},
            "schedule": schedule_data.get("schedule") if schedule_data else []
        }
        # Cache gym details for later retrieval
        gyms_cache[gym_id] = gym_details
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
async def gym_book():
    data = await request.get_json()
    user_id = data.get("userId")
    gym_id = data.get("gymId")
    session_date = data.get("sessionDate")
    time_slot = data.get("timeSlot")

    # Validate existence of gym in local cache for prototype.
    if gym_id not in gyms_cache:
        return jsonify({"error": "Gym not found"}), 404

    booking_id = str(uuid4())
    booking = {
        "bookingId": booking_id,
        "gymId": gym_id,
        "sessionDate": session_date,
        "timeSlot": time_slot,
        "status": "processing",
        "requestedAt": datetime.now().isoformat()
    }

    # Store booking in local cache for the user.
    user_bookings = bookings_cache.get(user_id, [])
    user_bookings.append(booking)
    bookings_cache[user_id] = user_bookings

    # Simulate external processing (payment, availability check) in background.
    asyncio.create_task(process_booking(booking))

    return jsonify({
        "bookingId": booking_id,
        "status": "processing",
        "message": "Booking is being processed. You will be notified upon confirmation."
    })

async def process_booking(booking):
    # Simulate processing delay and external API call.
    await asyncio.sleep(2)  # Simulate delay
    # TODO: Replace with actual processing logic (call GymAPI for payment and availability confirmation).
    booking["status"] = "confirmed"
    print(f"Processed booking: {booking['bookingId']} - confirmed.")

@app.route("/gyms/review", methods=["POST"])
async def gym_review():
    data = await request.get_json()
    user_id = data.get("userId")
    gym_id = data.get("gymId")
    rating = data.get("rating")
    comment = data.get("comment")

    if gym_id not in gyms_cache:
        return jsonify({"error": "Gym not found"}), 404

    review = {
        "reviewId": str(uuid4()),
        "userId": user_id,
        "rating": rating,
        "comment": comment,
        "createdAt": datetime.now().isoformat()
    }
    gym_reviews = reviews_cache.get(gym_id, [])
    gym_reviews.append(review)
    reviews_cache[gym_id] = gym_reviews

    return jsonify({"message": "Review submitted successfully", "reviewId": review["reviewId"]})

@app.route("/bookings", methods=["GET"])
async def get_bookings():
    # Assume userId is provided as a query parameter for prototype.
    user_id = request.args.get("userId")
    user_bookings = bookings_cache.get(user_id, [])
    return jsonify({"bookings": user_bookings})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)