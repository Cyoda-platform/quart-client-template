#!/usr/bin/env python3
import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import List, Any

import aiohttp
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION  # use the constant for all calls
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)  # Initialize QuartSchema

# ---------- Startup ----------

@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# ---------- Workflow Functions ----------
# These functions are applied to the entity data asynchronously before persistence.

async def process_user(entity):
    # Example workflow: add a created timestamp to the user entity
    entity["created_at"] = time.time()
    return entity

async def process_lesson(entity):
    # Example workflow: mark the lesson booking time
    entity["bookedAt"] = time.time()
    return entity

async def process_review(entity):
    # Example workflow: ensure rating is within bounds and add a reviewed timestamp
    rating = entity.get("rating", 0)
    if not (0 <= rating <= 5):
        entity["rating"] = max(0, min(5, rating))
    entity["reviewedAt"] = time.time()
    return entity

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
        await asyncio.sleep(1)  # Simulate network latency
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
    # Update rating via external service
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="rating",
        entity_version=ENTITY_VERSION,
        entity={"user_id": data["user_id"], "rating": result["new_rating"]},
        meta={}
    )
    # Optionally notify user/service about rating update

# ---------- Authentication Endpoints ----------

@app.route('/api/auth/register', methods=['POST'])
@validate_request(RegisterRequest)
async def register(data: RegisterRequest):
    # Prepare user data with additional profile fields
    user = {
        "username": data.username,
        "email": data.email,
        "password": data.password,  # Plain text for prototype only. TODO: Hash passwords!
        "bio": "",
        "skills": [],
        "rating": 0.0,
        "reviews": []
    }
    # Add user to external service with workflow processing
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        entity=user,
        workflow=process_user
    )
    return jsonify({
        "message": "User registered successfully",
        "id": new_id
    })

@app.route('/api/auth/login', methods=['POST'])
@validate_request(LoginRequest)
async def login(data: LoginRequest):
    # Query external service for user matching the provided credentials
    users = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        condition={"email": data.email, "password": data.password}
    )
    if not users:
        return jsonify({"message": "Invalid credentials"}), 401
    user = users[0]
    # Generate a dummy JWT token (insecure, for prototype only)
    token = str(uuid.uuid4())
    return jsonify({
        "token": token,
        "user": {"id": user.get("id"), "username": user.get("username")}
    })

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
    # Update business logic: update bio and merge skills
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

    await entity_service.update_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        entity=profile,
        meta={}
    )
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
    await entity_service.update_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        entity=profile,
        meta={}
    )
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
            # TODO: Use verification_method and verification_data to actually verify the skill
            skill["verified"] = True
            profile["skills"] = skills
            await entity_service.update_item(
                token=cyoda_token,
                entity_model="user",
                entity_version=ENTITY_VERSION,
                entity=profile,
                meta={}
            )
            return jsonify({"message": "Skill verified successfully"})
    return jsonify({"message": "Skill not found"}), 404

# ---------- Lesson Booking Endpoints ----------

@validate_querystring(SearchLessonsQuery)
@app.route('/api/lessons/search', methods=['GET'])
async def search_lessons():
    skill = request.args.get("skill")
    # For simplicity, pass the condition to external service filtering by skill
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
        "teacher": "user123",  # TODO: Derive teacher from lesson_id mapping
        "skill": "Python",     # TODO: Get skill details from lesson data
        "price": 20,           # TODO: Derive pricing from lesson data
        "rating": 4.9,         # TODO: Calculate based on teacher's rating
        "student_id": data.student_id,
        "date": data.date
    }
    # Add lesson booking with workflow processing
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="lesson",
        entity_version=ENTITY_VERSION,
        entity=lesson,
        workflow=process_lesson
    )
    return jsonify({"message": "Lesson booked", "id": new_id})

# ---------- Reviews and Rating Endpoints ----------

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
    # Add review with workflow processing
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="review",
        entity_version=ENTITY_VERSION,
        entity=review,
        workflow=process_review
    )
    return jsonify({"message": "Review submitted", "id": new_id})

@app.route('/api/rating/calculate', methods=['POST'])
@validate_request(CalculateRatingRequest)
async def calculate_rating(data: CalculateRatingRequest):
    # Start asynchronous rating calculation via external service
    entity_job = {"status": "processing", "requestedAt": time.time()}
    asyncio.create_task(process_rating(entity_job, data.__dict__))
    return jsonify({
        "message": "Ranking calculation started. It will update shortly."
    })

# ---------- Entry Point ----------

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)