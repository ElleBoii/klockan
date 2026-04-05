from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

STROKES = [
    "Freestyle",
    "Backstroke",
    "Breaststroke",
    "Butterfly",
    "Medley"
]

EQUIPMENT_OPTIONS = [
    "Fenor",
    "Paddlar",
    "Paddlar & dolme",
    "Dolme",
    "Fenor & paddlar",
    "Ben",
    "Ben fenor",
    "Ingen"
]

POOL_LENGTHS = [
    "25 m",
    "50 m",
    "25 yards"
]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

class Swimmer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    results = db.relationship("KlockanResult", backref="swimmer", lazy=True)

    def __repr__(self):
        return f"<Swimmer {self.name}>"


class KlockanSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    pool_length = db.Column(db.String(20), nullable=False)
    max_rounds = db.Column(db.Integer, nullable=False)

    results = db.relationship("KlockanResult", backref="session", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<KlockanSession {self.date} {self.pool_length} {self.max_rounds} rounds>"


class KlockanResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    session_id = db.Column(db.Integer, db.ForeignKey("klockan_session.id"), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    swimmer_id = db.Column(db.Integer, db.ForeignKey("swimmer.id"), nullable=False)
    stroke = db.Column(db.String(50), nullable=False)
    equipment = db.Column(db.String(50), nullable=False)
    failed_start_time = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("session_id", "round_number", "swimmer_id", name="unique_swimmer_per_round"),
    )

    def __repr__(self):
        return (
            f"<KlockanResult session={self.session_id} round={self.round_number} "
            f"swimmer={self.swimmer_id} result={self.failed_start_time}>"
        )