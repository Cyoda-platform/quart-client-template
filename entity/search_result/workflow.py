import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

GOOGLE_PLACES_API_KEY = "YOUR_GOOGLE_PLACES_API_KEY"
GOOGLE_PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DEFAULT_PAGE_SIZE = 20

search_cache = {}

@dataclass
class Location:
    latitude: float
    longitude: float

@dataclass
class Pagination:
    page: Optional[int] = 1
    page_size: Optional[int] = DEFAULT_PAGE_SIZE

@dataclass
class Filters:
    price_range: Optional[List[int]] = field(default_factory=list)
    rating_min: Optional[float] = None
    cuisine_subtypes: Optional[List[str]] = field(default_factory=list)

@dataclass
class SearchRequest:
    location: Location
    radius: int
    filters: Optional[Filters] = field(default_factory=Filters)
    pagination: Optional[Pagination] = field(default_factory=Pagination)

async def process_fetch_restaurants(entity):
    filters_dict = entity.get("request_data", {}).get("filters", {})
    filters = Filters(
        price_range=filters_dict.get("price_range", []),
        rating_min=filters_dict.get("rating_min"),
        cuisine_subtypes=filters_dict.get("cuisine_subtypes", []),
    )
    loc = entity.get("request_data", {}).get("location")
    location = Location(latitude=loc["latitude"], longitude=loc["longitude"])
    radius = entity.get("request_data", {}).get("radius")

    params = {
        "key": GOOGLE_PLACES_API_KEY,
        "location": f"{location.latitude},{location.longitude}",
        "radius": radius,
        "keyword": "french restaurant",
        "type": "restaurant",
    }

    restaurants = []
    async with httpx.AsyncClient() as client:
        next_page_token = None
        retry_attempts = 0
        while True:
            if next_page_token:
                await asyncio.sleep(2)
                params["pagetoken"] = next_page_token
            else:
                params.pop("pagetoken", None)
            try:
                resp = await client.get(GOOGLE_PLACES_SEARCH_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.exception(f"Google Places API request failed: {e}")
                retry_attempts += 1
                if retry_attempts > 2:
                    break
                await asyncio.sleep(2)
                continue

            retry_attempts = 0
            results = data.get("results", [])
            restaurants.extend(results)

            next_page_token = data.get("next_page_token")
            if not next_page_token:
                break

            if len(restaurants) >= 60:
                break

    filtered = []
    price_range = filters.price_range if filters else None
    rating_min = filters.rating_min if filters else None
    cuisine_subtypes = filters.cuisine_subtypes if filters else []

    for r in restaurants:
        price_level = r.get("price_level", 0)
        rating = r.get("rating", 0)

        if price_range:
            if price_level == 0 or not (price_range[0] <= price_level <= price_range[1]):
                continue

        if rating_min and rating < rating_min:
            continue

        if cuisine_subtypes:
            name = r.get("name", "").lower()
            vicinity = r.get("vicinity", "").lower()
            if not any(subtype.lower() in name or subtype.lower() in vicinity for subtype in cuisine_subtypes):
                continue

        filtered.append(r)

    entity["raw_restaurants"] = filtered
    return entity

def process_paginate(entity):
    pagination_dict = entity.get("request_data", {}).get("pagination", {})
    page = pagination_dict.get("page", 1)
    page_size = pagination_dict.get("page_size", DEFAULT_PAGE_SIZE)
    if page is None or page < 1:
        page = 1
    if page_size is None or page_size < 1:
        page_size = DEFAULT_PAGE_SIZE

    all_restaurants = entity.get("formatted_restaurants", [])
    start = (page - 1) * page_size
    end = start + page_size
    entity["restaurants_page"] = all_restaurants[start:end]
    entity["current_page"] = page
    entity["page_size"] = page_size
    return entity

def process_format_restaurants(entity):
    raw_restaurants = entity.get("raw_restaurants", [])
    formatted = []
    for raw in raw_restaurants:
        formatted.append({
            "id": raw.get("place_id"),
            "name": raw.get("name"),
            "address": raw.get("vicinity"),
            "contact": "",  # Not provided by Google Places Nearby Search API
            "rating": raw.get("rating"),
            "price_level": raw.get("price_level", 0),
            "cuisine_types": ["French"],
            "location": {
                "latitude": raw.get("geometry", {}).get("location", {}).get("lat"),
                "longitude": raw.get("geometry", {}).get("location", {}).get("lng"),
            },
        })
    entity["formatted_restaurants"] = formatted
    entity["total_results"] = len(formatted)
    return entity