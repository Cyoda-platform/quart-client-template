@routes_bp.route("/api/goodbye", methods=["GET"])
async def goodbye():
    return jsonify({"message": "Goodbye, world!"}), 200