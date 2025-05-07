@routes_bp.route("/api/hello", methods=["GET"])
async def hello():
    return jsonify({"message": "Hello, world!"}), 200