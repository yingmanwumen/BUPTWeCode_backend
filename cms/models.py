from exts import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from common.token import Permission


class Role(db.Model):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), nullable=False)
    display_name = db.Column(db.String(20), nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)
    permission = db.Column(db.Integer, default=Permission.VISITOR)

    cms_users = db.relationship("CMSUser", backref="role", lazy="dynamic")


class CMSUser(db.Model):
    __tablename__ = 'cms_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), nullable=False)
    display_name = db.Column(db.String(20), nullable=True)
    _password = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self):
        return "<CMSUser uid={} username={}>".format(CMSUser.id, CMSUser.username)

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, raw_password):
        self._password = generate_password_hash(raw_password)

    def validate(self, raw_password):
        res = check_password_hash(self.password, raw_password)
        return res

    @property
    def permission(self):
        return self.role.permission or Permission.VISITOR

    def has_permission(self, permission):
        return self.permission & permission == permission

    @property
    def is_developer(self):
        return self.has_permission(Permission.ALL_PERMISSION)
