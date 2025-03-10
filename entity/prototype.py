import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import List, Any

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

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


# ---------- Dataclasses for Request Validation ----------

@dataclass
class RegisterRequest:
    username: str
    email: str
    password: str

@dataclass
class LoginRequest:
    email: str
    password: str

@dataclass
class UpdateProfileRequest:
    bio: str
    skills: List[Any]  # TODO: refine structure of skills if needed

@dataclass
class AddSkillRequest:
    user_id: int
    skill: str
    experience_years: int

@dataclass
class VerifySkillRequest:
    user_id: int
    skill: str
    verification_method: str
    verification_data: str

@dataclass
class BookLessonRequest:
    student_id: int
    lesson_id: int
    date: str

@dataclass
class SubmitReviewRequest:
    from_user: int
    to_user: int
    lesson_id: int
    rating: int
    comment: str

@dataclass
class CalculateRatingRequest:
    user_id: int
    reviews: List[Any] = None  # TODO: refine review structure if needed
    verified_skills: List[Any] = None  # TODO: refine skill structure if needed

@dataclass
class SearchLessonsQuery:
    skill: str
    location: str = ""


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
@validate_request(RegisterRequest)  # For POST, route decorator comes first, then validate_request (workaround for quart-schema issue)
async def register(data: RegisterRequest):
    global user_counter
    async with counter_lock:
        user_id = user_counter
        user_counter += 1

    user = {
        "id": user_id,
        "username": data.username,
        "email": data.email,
        # Password stored in plain text for prototype only. TODO: Hash passwords!
        "password": data.password
    }
    users[user_id] = user
    profiles[user_id] = {
        "id": user_id,
        "username": data.username,
        "bio": "",
        "skills": [],
        "rating": 0.0,
        "reviews": []
    }
    return jsonify({
        "message": "User registered successfully",
        "user": {"id": user_id, "username": data.username}
    })


@app.route('/api/auth/login', methods=['POST'])
@validate_request(LoginRequest)
async def login(data: LoginRequest):
    for user in users.values():
        if user["email"] == data.email and user["password"] == data.password:
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
@validate_request(UpdateProfileRequest)  # For POST/PUT/PATCH, route first then validate_request
async def update_profile(data: UpdateProfileRequest, user_id):
    profile = profiles.get(user_id)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    profile["bio"] = data.bio
    if data.skills:
        for updated_skill in data.skills:
            skill_found = False
            for skill in profile["skills"]:
                if skill["name"] == updated_skill.get("name"):
                    skill["experience_years"] = updated_skill.get("experience_years")
                    skill_found = True
                    break
            if not skill_found:
                profile["skills"].append({
                    "name": updated_skill.get("name"),
                    "experience_years": updated_skill.get("experience_years"),
                    "verified": False
                })
    return jsonify({"message": "Profile updated"})


# ---------- Skill Management Endpoints ----------

@app.route('/api/skills/add', methods=['POST'])
@validate_request(AddSkillRequest)
async def add_skill(data: AddSkillRequest):
    profile = profiles.get(data.user_id)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    profile["skills"].append({
        "name": data.skill,
        "experience_years": data.experience_years,
        "verified": False
    })
    return jsonify({"message": "Skill added"})


@app.route('/api/skills/verify', methods=['POST'])
@validate_request(VerifySkillRequest)
async def verify_skill(data: VerifySkillRequest):
    profile = profiles.get(data.user_id)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    for skill in profile["skills"]:
        if skill["name"] == data.skill:
            # TODO: Use verification_method and verification_data to actually verify the skill
            skill["verified"] = True
            return jsonify({"message": "Skill verified successfully"})
    return jsonify({"message": "Skill not found"}), 404


# ---------- Lesson Booking Endpoints ----------

@validate_querystring(SearchLessonsQuery)  # For GET endpoints with query string, validation decorator goes first (workaround for quart-schema issue)
@app.route('/api/lessons/search', methods=['GET'])
async def search_lessons():
    # Use standard approach to access query parameters
    skill = request.args.get("skill")
    location = request.args.get("location")  # Not used in prototype, but could be filtered later
    # TODO: Improve filtering logic based on location/other factors
    result = []
    for lesson in lessons.values():
        if lesson["skill"].lower() == skill.lower():
            result.append(lesson)
    return jsonify(result)


@app.route('/api/lessons/book', methods=['POST'])
@validate_request(BookLessonRequest)
async def book_lesson(data: BookLessonRequest):
    global lesson_counter
    async with counter_lock:
        booking_id = lesson_counter
        lesson_counter += 1

    lessons[booking_id] = {
        "lesson_id": booking_id,
        "teacher": "user123",  # TODO: Derive teacher from lesson_id mapping
        "skill": "Python",     # TODO: Get skill details from lesson data
        "price": 20,           # TODO: Derive pricing from lesson data
        "rating": 4.9,         # TODO: Calculate based on teacher's rating
        "student_id": data.student_id,
        "date": data.date
    }
    return jsonify({"message": "Lesson booked"})


# ---------- Reviews and Rating Endpoints ----------

@app.route('/api/reviews', methods=['POST'])
@validate_request(SubmitReviewRequest)
async def submit_review(data: SubmitReviewRequest):
    profile = profiles.get(data.to_user)
    if not profile:
        return jsonify({"message": "User not found"}), 404

    review = {"from": f"user{data.from_user}", "rating": data.rating, "comment": data.comment}
    profile["reviews"].append(review)
    reviews_db.setdefault(data.to_user, []).append({"rating": data.rating})
    return jsonify({"message": "Review submitted"})


@app.route('/api/rating/calculate', methods=['POST'])
@validate_request(CalculateRatingRequest)
async def calculate_rating(data: CalculateRatingRequest):
    # Business logic could use reviews and verified skills to calculate average rating,
    # but here we simulate an external call.
    entity_job = {"status": "processing", "requestedAt": time.time()}
    # Fire and forget the processing task.
    asyncio.create_task(process_rating(entity_job, data.__dict__))
    return jsonify({
        "message": "Ranking calculation started. It will update shortly."
    })


# ---------- Entry Point ----------

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)