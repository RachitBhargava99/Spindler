from backend import db
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask_login import UserMixin
from flask import current_app
from datetime import datetime


class Fav(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    res_id = db.Column(db.Integer, db.ForeignKey('result.id'), nullable=False)

    def __repr__(self):
        return f"Favorite Relationship ID {self.id}"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(127), nullable=False)
    email = db.Column(db.String(63), unique=True, nullable=False)
    password = db.Column(db.String(63), unique=False, nullable=False)
    isAdmin = db.Column(db.Boolean, nullable=False, default=False)

    def get_auth_token(self, expires_seconds=86400):
        s = Serializer(current_app.config['SECRET_KEY'], expires_seconds)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def get_reset_token(self, expires_seconds=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_seconds)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User ID {self.id}"


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1023), nullable=True)
    center = db.Column(db.String(127), nullable=True)
    last_updated = db.Column(db.DateTime, nullable=True, default=datetime.now())
    thumb_img = db.Column(db.String(1023), nullable=False)
    description = db.Column(db.String(16383), nullable=True)
    nasa_id = db.Column(db.String(1023), nullable=False, unique=True)

    def __repr__(self):
        return f"Result ID {self.id}"


class SearchStream(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    q = db.Column(db.String(1023), nullable=False, default="")
    center = db.Column(db.String(127), nullable=False, default="")
    location = db.Column(db.String(1023))
    media_type = db.Column(db.String(63))
    nasa_id = db.Column(db.String(1023))
    photographer = db.Column(db.String(127))


class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class SearchKeywordRel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ss_id = db.Column(db.Integer, db.ForeignKey('searchstream.id'), nullable=False)
    kw_id = db.Column(db.Integer, db.ForeignKey('keyword.id'), nullable=False)
