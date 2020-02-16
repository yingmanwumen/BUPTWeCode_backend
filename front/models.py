from exts import db
from datetime import datetime
import shortuuid


class FrontUser(db.Model):
    __tablename__ = "front_user"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    open_id = db.Column(db.String(50))
    username = db.Column(db.String(20), default="未命名")
    signature = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.Integer, default=0)
    avatar_url = db.Column(db.String(500))
    # phone = db.Column(db.Integer)
    union_id = db.Column(db.String(100))
    created = db.Column(db.DateTime, default=datetime.now)
