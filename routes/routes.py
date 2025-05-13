@routes_bp.route("/pets/<string:pet_id>", methods=["GET"])
async def pets_get(pet_id: str):
    try:
        pet = await entity_service.get_item(
            token=cyoda_auth_service,
            entity_model="pet",
            entity_version=ENTITY_VERSION,
            technical_id=pet_id,
        )
    except Exception as e:
        logger.exception(e)
        return jsonify({"error": "Pet not found"}), 404

    if not pet:
        return jsonify({"error": "Pet not found"}), 404

    pet_out = pet.copy()
    cat = pet_out.pop("category", None)
    pet_out["type"] = cat.get("name") if cat else None
    return jsonify(pet_out)