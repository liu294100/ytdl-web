from app import create_app
import os


flask_app = create_app()


if __name__ == "__main__":
    host = os.getenv("YTDL_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("YTDL_WEB_PORT", "8000"))
    flask_app.run(host=host, port=port, debug=False)
