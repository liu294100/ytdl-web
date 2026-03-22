from flask import Flask

from app.config import Config
from app.repositories.settings_repository import SettingsRepository
from app.routes.api import api_bp
from app.routes.web import web_bp


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    settings_repo = SettingsRepository(app.config["SQLITE_DB_PATH"])
    settings_repo.init_db()
    app.config["SETTINGS_REPO"] = settings_repo
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    return app
