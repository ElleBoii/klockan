from werkzeug.security import generate_password_hash
from app import app
from models import db, User

USERNAME = "admin123"
PASSWORD = "KlockanAdmin123"

with app.app_context():
    db.create_all()

    existing_user = User.query.filter_by(username=USERNAME).first()

    if existing_user:
        print("User already exists.")
    else:
        new_user = User(
            username=USERNAME,
            password_hash=generate_password_hash(PASSWORD)
        )
        db.session.add(new_user)
        db.session.commit()
        print("Admin user created successfully.")