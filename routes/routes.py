@routes_bp.route("/hello", methods=["GET"])
async def hello():
    return jsonify({"message": "Hello from NBA scores app!"})