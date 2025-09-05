import uuid

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _str_uuid():
    return str(uuid.uuid4())


# pylint: disable=too-few-public-methods
class User(db.Model):  # type: ignore
    """A user in the database"""

    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(40), default=_str_uuid, unique=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"
