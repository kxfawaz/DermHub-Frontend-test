# app/models.py

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from datetime import datetime, timezone
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()
db = SQLAlchemy()


class User(db.Model):
    """
    Must match DB table public.users:
      - email UNIQUE
      - created_at (not create_at)
      - password_hashed up to 255
      - first_name/last_name nullable
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hashed = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    has_medical_history = db.Column(db.Boolean, nullable=False, default=False, server_default=db.text("false"))
    is_admin = db.Column(db.Boolean, nullable=False, default=False, server_default=db.text("false"))

    @classmethod
    def signup(cls, username: str, email: str, password: str, first_name: str | None = None, last_name: str | None = None):
        """
        Hashes password server-side for safety; returns transient user (caller commits).
        """
        hashed_pwd = bcrypt.generate_password_hash(password).decode("utf-8")
        user = cls(
            username=username,
            email=email,
            password_hashed=hashed_pwd,
            first_name=first_name,
            last_name=last_name,
        )
        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username: str, password: str):
        """
        Constant-time password check via bcrypt. Returns user or False.
        """
        user = cls.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hashed, password):
            return user
        return False


class Consultation(db.Model):
    __tablename__ = "consultations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    form_id = db.Column(db.Integer, db.ForeignKey("consult_forms.id"), nullable=False)
    primary_question_id = db.Column(db.Integer, db.ForeignKey("consult_questions.id"), nullable=False)
    status = db.Column(db.String(20), default="draft")

    user = db.relationship("User", backref="consultations")
    answers = db.relationship("ConsultAnswer", backref="consultation")
    followup_answers = db.relationship("FollowupAnswers", backref="consultation")
    primary_question = db.relationship("ConsultQuestion")


class ConsultForm(db.Model):
    __tablename__ = "consult_forms"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    questions = db.relationship("ConsultQuestion", backref="form", cascade="all, delete-orphan")


class ConsultQuestion(db.Model):
    __tablename__ = "consult_questions"
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String(255), nullable=False)
    form_id = db.Column(db.Integer, db.ForeignKey("consult_forms.id"), nullable=False)

    followups = db.relationship("FollowupQuestions", backref="parent_question")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "form_id": self.form_id,
            "followups": [f.to_dict() for f in self.followups],
        }


class FollowupQuestions(db.Model):
    __tablename__ = "followup_questions"
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String(255), nullable=False)
    parent_question_id = db.Column(db.Integer, db.ForeignKey("consult_questions.id"), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "parent_question_id": self.parent_question_id,
        }


class ConsultAnswer(db.Model):
    __tablename__ = "consult_answers"
    id = db.Column(db.Integer, primary_key=True)

    consultation_id = db.Column(db.Integer, db.ForeignKey("consultations.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    question_id = db.Column(db.Integer, db.ForeignKey("consult_questions.id"), nullable=False)
    answer_text = db.Column(db.Text, nullable=True)

    question = db.relationship("ConsultQuestion")


class FollowupAnswers(db.Model):
    __tablename__ = "followup_answers"
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey("consultations.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("followup_questions.id"), nullable=False)
    text_answer = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=True)

    question = db.relationship("FollowupQuestions")


def connect_db(app):
    """
    Initializes SQLAlchemy with the Flask app.
    """
    db.app = app
    db.init_app(app)
