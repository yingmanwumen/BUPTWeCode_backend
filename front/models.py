from exts import db
from datetime import datetime
import shortuuid


class FrontUser(db.Model):
    __tablename__ = "front_user"
    # __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    open_id = db.Column(db.String(50))
    username = db.Column(db.String(20), default="未命名", nullable=False)
    signature = db.Column(db.String(100), default="你只需默认就好，无需多言我的好", nullable=False)
    gender = db.Column(db.Integer, default=0, nullable=False)
    avatar_url = db.Column(db.String(500))
    # phone = db.Column(db.Integer)
    union_id = db.Column(db.String(100))
    created = db.Column(db.DateTime, default=datetime.now)

    articles = db.relationship("Article", backref="author", lazy="dynamic")
