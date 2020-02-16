from exts import db
from datetime import datetime


class Board(db.Model):
    __tablename__ = 'boards'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    desc = db.Column(db.String(200), nullable=False)
    avatar_url = db.Column(db.String(200))
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    articles = db.Column(db.Integer)
