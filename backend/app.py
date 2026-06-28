from flask import Flask

from backend_config import HOST, PORT, DEBUG
from routes import register_routes

app = Flask(__name__)

register_routes(app)

if __name__ == "__main__":
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG
    )
