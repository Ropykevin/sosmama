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

    
    # Register blueprint
    from app.routes import bp
    app.register_blueprint(bp)

    
    return app 