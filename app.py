from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

from models import db, User

from routes.customer import customer_bp
from routes.admin import admin_bp
from routes.auth import auth_bp

from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
