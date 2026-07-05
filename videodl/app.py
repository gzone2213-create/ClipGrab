import os
from flask import Flask, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from routes import api


def create_app():
    app = Flask(__name__)

    allowed_origins = os.environ.get("CORS_ORIGINS", "*")
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["60 per hour", "10 per minute"],
        storage_uri="memory://",
    )
    limiter.init_app(app)

    app.register_blueprint(api)

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(_):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(_):
        return {"error": "Internal server error"}, 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)