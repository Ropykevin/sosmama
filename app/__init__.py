from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__,template_folder='templates',static_folder='static')
    app.secret_key = "Wdg@#$%89jMfh2879mT"
    
    # Initialize database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sosmama.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    
    # Import routes
    from app.routes import bp

    from app import routes
    app.register_blueprint(bp)

    
    return app 