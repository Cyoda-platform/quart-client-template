import asyncio
import json
import time
import uuid

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# In-memory "databases" (mocks)
users = {}
profiles = {}
user_counter = 1

lessons = {}
lesson_counter = 1

reviews_db = {}
ratings_db = {}

# Global lock for safe incrementing of counters (for prototype simplicity)
counter_lock = asyncio.Lock()


# ---------- Helper Functions ----------

async def external_rating_calculation(data):
    # TODO: Replace with a real HTTP call to a rating service API if available
    async with aiohttp.ClientSession() as session:
        # Mocks a POST request to an external service
        # Here, we just simulate with a delay
        await asyncio.sleep(1)  # Simulate network latency
        # Use a fake calculation: average of provided review ratings
        ratings = [review["rating"] for review in data.get("reviews", [])]
        if ratings:
            new_rating = sum(ratings) / len(ratings)
        else:
            new_rating = 0.0
        return {"new_rating": round(new_rating, 1)}


async def process_rating(entity_job, data):
    # Simulate processing of the rating calculation asynchronously
    result = await external_rating_calculation(data)
    entity_job["status"] = "completed"
    ratings_db[data["user_id"]] = result["new_rating"]
    # TODO: Optionally notify user/service about rating update


# ---------- Authentication Endpoints ----------

@app.route('/api/auth/register', methods=['POST'])
async def register():
    data = await request.get_json()
    global user_counter

    async with counter_lock:
        user_id = user_counter
        user_counter += 1

    # Create a new user object (mock)
    user = {
        "id": user_id,
        "username": data.get("username"),
        "email": data.get("email"),
        # Password stored in plain text for prototype only. TODO: Hash passwords!
        "password": data.get("password")
    }
    users[user_id] = user
    # Also create an empty profile for the user
    profiles[user_id] = {
        "id": user_id,
        "username": data.get("username"),
        "bio": "",
        "skills": [],
        "rating": 0.0,
        "reviews": []
    }
    return jsonify({
        "message": "User registered successfully",
        "user": {"id": user_id, "username": data.get("username")}
    })


@app.route('/api/auth/login', methods=['POST'])
async def login():
    data = await request.get_json()
    # For prototype, we search manually. TODO: Implement proper auth and secure password verification.
    for user in users.values():
        if user["email"] == data.get("email") and user["password"] == data.get("password"):
            # Generate a dummy JWT token (insecure, for prototype only)
            token = str(uuid.uuid4())
            return jsonify({
                "token": token,
                "user": {"id": user["id"], "username": user["username"]}
            })
    return jsonify({"message": "Invalid credentials"}), 401


# ---------- User Profile Endpoints ----------

@app.route('/api/users/<int:user_id>', methods=['GET'])
async def get_profile(user_id):
    profile = profiles.get(user_id)
    if not profile:
        return jsonify({"message": "User not found"}), 404
    return jsonify(profile)


@app.route('/api/users/<int:user_id>', methods=['PATCH'])
async def update_profile(user_id):
    data = await request.get_json()
    profile = profiles.get(user_id)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    # Update bio if present
    if "bio" in data:
        profile["bio"] = data["bio"]

    # Update skills if provided (only update experience, not verification status)
    if "skills" in data:
        for updated_skill in data["skills"]:
            skill_found = False
            for skill in profile["skills"]:
                if skill["name"] == updated_skill["name"]:
                    skill["experience_years"] = updated_skill["experience_years"]
                    skill_found = True
                    break
            if not skill_found:
                # Add new skill entry if it doesn't exist
                profile["skills"].append({
                    "name": updated_skill["name"],
                    "experience_years": updated_skill["experience_years"],
                    "verified": False
                })
    return jsonify({"message": "Profile updated"})


# ---------- Skill Management Endpoints ----------

@app.route('/api/skills/add', methods=['POST'])
async def add_skill():
    data = await request.get_json()
    user_id = data.get("user_id")
    skill_name = data.get("skill")
    experience_years = data.get("experience_years")

    profile = profiles.get(user_id)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    # Add skill (default verified = False)
    profile["skills"].append({
        "name": skill_name,
        "experience_years": experience_years,
        "verified": False
    })
    return jsonify({"message": "Skill added"})


@app.route('/api/skills/verify', methods=['POST'])
async def verify_skill():
    data = await request.get_json()
    user_id = data.get("user_id")
    skill_name = data.get("skill")
    verification_method = data.get("verification_method")
    verification_data = data.get("verification_data")

    profile = profiles.get(user_id)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    # Find the skill and mark as verified
    for skill in profile["skills"]:
        if skill["name"] == skill_name:
            # TODO: Use verification_method and verification_data to actually verify the skill
            skill["verified"] = True
            return jsonify({"message": "Skill verified successfully"})
    return jsonify({"message": "Skill not found"}), 404


# ---------- Lesson Booking Endpoints ----------

@app.route('/api/lessons/search', methods=['GET'])
async def search_lessons():
    # For GET endpoints, simply return data from our local cache
    skill = request.args.get("skill")
    location = request.args.get("location")  # Not used in prototype, but could filter based on location
    # TODO: Improve filtering logic based on location/other factors
    result = []
    for lesson in lessons.values():
        if lesson["skill"].lower() == skill.lower():
            result.append(lesson)
    return jsonify(result)


@app.route('/api/lessons/book', methods=['POST'])
async def book_lesson():
    data = await request.get_json()
    global lesson_counter
    student_id = data.get("student_id")
    lesson_id = data.get("lesson_id")  # In a real system we would reference an existing lesson by teacher etc.
    date = data.get("date")

    # TODO: Validate if lesson exists and check availability
    async with counter_lock:
        booking_id = lesson_counter
        lesson_counter += 1

    lessons[booking_id] = {
        "lesson_id": booking_id,
        "teacher": "user123",  # TODO: Derive teacher from lesson_id mapping
        "skill": "Python",     # TODO: Get skill details from lesson data
        "price": 20,           # TODO: Derive pricing from lesson data
        "rating": 4.9,         # TODO: Calculate based on teacher's rating
        "student_id": student_id,
        "date": date
    }
    return jsonify({"message": "Lesson booked"})


# ---------- Reviews and Rating Endpoints ----------

@app.route('/api/reviews', methods=['POST'])
async def submit_review():
    data = await request.get_json()
    from_user = data.get("from_user")
    to_user = data.get("to_user")
    lesson_id = data.get("lesson_id")
    rating = data.get("rating")
    comment = data.get("comment")

    profile = profiles.get(to_user)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    review = {"from": f"user{from_user}", "rating": rating, "comment": comment}
    profile["reviews"].append(review)

    # Optionally store review for rating calculation
    reviews_db.setdefault(to_user, []).append({"rating": rating})
    return jsonify({"message": "Review submitted"})


@app.route('/api/rating/calculate', methods=['POST'])
async def calculate_rating():
    data = await request.get_json()
    user_id = data.get("user_id")
    # Business logic could use reviews and verified skills to calculate average rating,
    # but here we simulate an external call.
    entity_job = {"status": "processing", "requestedAt": time.time()}

    # Fire and forget the processing task.
    asyncio.create_task(process_rating(entity_job, data))
    return jsonify({
        "message": "Ranking calculation started. It will update shortly."
    })


# ---------- Entry Point ----------

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)