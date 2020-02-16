from exts import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


class CMSPermission(object):
    VISITOR        = 0b00000001  # 访问者权限
    COMMENTER      = 0b00000010  # 管理评论权限
    POSTER         = 0b00000100  # 管理帖子权限
    FRONTUSER      = 0b00001000  # 管理板块权限
    BOADER         = 0b00010000  # 管理前台用户的角色
    CMSUSER        = 0b00100000  # 管理后台用户的角色
    ROOTER         = 0b01000000  # 超级管理员

    OPERATOR = VISITOR | COMMENTER | POSTER | FRONTUSER                     # 运营角色
    ADMIN = VISITOR | COMMENTER | POSTER | FRONTUSER | BOADER | CMSUSER     # 管理员角色
    ALL_PERMISSION = 0b11111111                                             # 开发者用


class CMSRole(db.Model):
    __tablename__ = 'cms_role'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), nullable=False)
    display_name = db.Column(db.String(20), nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)
    permission = db.Column(db.Integer, default=CMSPermission.VISITOR)

    users = db.relationship("CMSUser", backref="role", lazy="dynamic")


class CMSUser(db.Model):
    __tablename__ = 'cms_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), nullable=False)
    display_name = db.Column(db.String(20), nullable=True)
    _password = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    created = db.Column(db.DateTime, default=datetime.now)
    role_id = db.Column(db.Integer, db.ForeignKey("cms_role.id"))

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
        return self.role.permission or CMSPermission.VISITOR

    def has_permission(self, permission):
        return self.permission & permission == permission

    @property
    def is_developer(self):
        return self.has_permission(CMSPermission.ALL_PERMISSION)
