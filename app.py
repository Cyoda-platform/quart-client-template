from common.grpc_client.grpc_client import grpc_stream
import asyncio
import time
from dataclasses import dataclass
from typing import List, Any

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

import bcrypt
import jwt
import datetime

from common.config.config import ENTITY_VERSION  # constant for entity version
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

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
    skills: List[Any]  # You can refine the structure if needed

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
    reviews: List[Any] = None  # Refine the review structure if needed
    verified_skills: List[Any] = None  # Refine skill structure if needed

@dataclass
class SearchLessonsQuery:
    skill: str
    location: str = ""

# ---------- Helper Functions ----------

async def external_rating_calculation(data):
    try:
        async with aiohttp.ClientSession():
            await asyncio.sleep(1)
            ratings = [review["rating"] for review in data.get("reviews", []) if "rating" in review]
            if ratings:
                new_rating = sum(ratings) / len(ratings)
            else:
                new_rating = 0.0
            return {"new_rating": round(new_rating, 1)}
    except Exception:
        return {"new_rating": 0.0}

async def process_rating(entity_job, data):
    result = await external_rating_calculation(data)
    entity_job["status"] = "completed"
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="rating",
            entity_version=ENTITY_VERSION,
            entity={"user_id": data["user_id"], "rating": result["new_rating"]},
            meta={}
        )
    except Exception:
        entity_job["status"] = "failed"
    return

SECRET_KEY = "your_secret_key"

def create_access_token(user):
    payload = {
        "user_id": user.get("id"),
        "username": user.get("username"),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

# ---------- Application Startup ----------

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)
    app.background_task = asyncio.create_task(grpc_stream(cyoda_token))

@app.after_serving
async def shutdown():
    app.background_task.cancel()
    await app.background_task

# ---------- Authentication Endpoints ----------

@app.route('/api/auth/register', methods=['POST'])
@validate_request(RegisterRequest)
async def register(data: RegisterRequest):
    hashed_password = bcrypt.hashpw(data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = {
        "username": data.username,
        "email": data.email,
        "hashed_password": hashed_password,
        "bio": "",
        "skills": [],
        "rating": 0.0,
        "reviews": []
    }
    try:
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=user,
        )
    except Exception as e:
        return jsonify({"message": "Error registering user", "error": str(e)}), 500
    return jsonify({"message": "User registered successfully", "id": new_id})

@app.route('/api/auth/login', methods=['POST'])
@validate_request(LoginRequest)
async def login(data: LoginRequest):
    users = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        condition={"email": data.email}
    )
    if not users:
        return jsonify({"message": "Invalid credentials"}), 401
    user = users[0]
    stored_hashed_password = user.get("hashed_password")
    if not stored_hashed_password or not bcrypt.checkpw(data.password.encode('utf-8'), stored_hashed_password.encode('utf-8')):
        return jsonify({"message": "Invalid credentials"}), 401
    token = create_access_token(user)
    return jsonify({"token": token, "user": {"id": user.get("id"), "username": user.get("username")}})

# ---------- User Profile Endpoints ----------

@app.route('/api/users/<int:user_id>', methods=['GET'])
async def get_profile(user_id):
    profile = await entity_service.get_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        technical_id=user_id
    )
    if not profile:
        return jsonify({"message": "User not found"}), 404
    return jsonify(profile)

@app.route('/api/users/<int:user_id>', methods=['PATCH'])
@validate_request(UpdateProfileRequest)
async def update_profile(data: UpdateProfileRequest, user_id):
    profile = await entity_service.get_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        technical_id=user_id
    )
    if not profile:
        return jsonify({"message": "User not found"}), 404
    profile["bio"] = data.bio
    updated_skills = profile.get("skills", [])
    if data.skills:
        for updated_skill in data.skills:
            skill_found = False
            for skill in updated_skills:
                if skill.get("name") == updated_skill.get("name"):
                    skill["experience_years"] = updated_skill.get("experience_years")
                    skill_found = True
                    break
            if not skill_found:
                updated_skills.append({
                    "name": updated_skill.get("name"),
                    "experience_years": updated_skill.get("experience_years"),
                    "verified": False
                })
    profile["skills"] = updated_skills
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=profile,
            meta={}
        )
    except Exception as e:
        return jsonify({"message": "Error updating profile", "error": str(e)}), 500
    return jsonify({"message": "Profile updated"})

# ---------- Skill Management Endpoints ----------

@app.route('/api/skills/add', methods=['POST'])
@validate_request(AddSkillRequest)
async def add_skill(data: AddSkillRequest):
    profile = await entity_service.get_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        technical_id=data.user_id
    )
    if not profile:
        return jsonify({"message": "User not found"}), 404
    skills = profile.get("skills", [])
    skills.append({
        "name": data.skill,
        "experience_years": data.experience_years,
        "verified": False
    })
    profile["skills"] = skills
    try:
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="user",
            entity_version=ENTITY_VERSION,
            entity=profile,
            meta={}
        )
    except Exception as e:
        return jsonify({"message": "Error adding skill", "error": str(e)}), 500
    return jsonify({"message": "Skill added"})

@app.route('/api/skills/verify', methods=['POST'])
@validate_request(VerifySkillRequest)
async def verify_skill(data: VerifySkillRequest):
    profile = await entity_service.get_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        technical_id=data.user_id
    )
    if not profile:
        return jsonify({"message": "User not found"}), 404
    skills = profile.get("skills", [])
    for skill in skills:
        if skill.get("name") == data.skill:
            skill["verified"] = True
            profile["skills"] = skills
            try:
                await entity_service.update_item(
                    token=cyoda_token,
                    entity_model="user",
                    entity_version=ENTITY_VERSION,
                    entity=profile,
                    meta={}
                )
            except Exception as e:
                return jsonify({"message": "Error verifying skill", "error": str(e)}), 500
            return jsonify({"message": "Skill verified successfully"})
    return jsonify({"message": "Skill not found"}), 404

@validate_querystring(SearchLessonsQuery)
@app.route('/api/lessons/search', methods=['GET'])
async def search_lessons():
    skill = request.args.get("skill")
    lessons = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="lesson",
        entity_version=ENTITY_VERSION,
        condition={"skill": skill}
    )
    return jsonify(lessons)

@app.route('/api/lessons/book', methods=['POST'])
@validate_request(BookLessonRequest)
async def book_lesson(data: BookLessonRequest):
    lesson = {
        "teacher": "user123",
        "skill": "Python",
        "price": 20,
        "rating": 4.9,
        "student_id": data.student_id,
        "date": data.date
    }
    try:
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="lesson",
            entity_version=ENTITY_VERSION,
            entity=lesson,
        )
    except Exception as e:
        return jsonify({"message": "Error booking lesson", "error": str(e)}), 500
    return jsonify({"message": "Lesson booked", "id": new_id})

@app.route('/api/reviews', methods=['POST'])
@validate_request(SubmitReviewRequest)
async def submit_review(data: SubmitReviewRequest):
    review = {
        "from": f"user{data.from_user}",
        "to": data.to_user,
        "lesson_id": data.lesson_id,
        "rating": data.rating,
        "comment": data.comment
    }
    try:
        new_id = await entity_service.add_item(
            token=cyoda_token,
            entity_model="review",
            entity_version=ENTITY_VERSION,
            entity=review,
        )
    except Exception as e:
        return jsonify({"message": "Error submitting review", "error": str(e)}), 500
    return jsonify({"message": "Review submitted", "id": new_id})

@app.route('/api/rating/calculate', methods=['POST'])
@validate_request(CalculateRatingRequest)
async def calculate_rating(data: CalculateRatingRequest):
    entity_job = {"status": "processing", "requested_at": time.time()}
    asyncio.create_task(process_rating(entity_job, data.__dict__))
    return jsonify({"message": "Ranking calculation started. It will update shortly."})

# ---------- Entry Point ----------

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
