from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = 'marz-secret-key-production'

    from app.controllers.auth_controller import auth_bp
    from app.controllers.ticket_controller import ticket_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(ticket_bp)

    return app
