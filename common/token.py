from config import SECRET_KEY, DEFAULT_EXPIRE_TIME_FOR_TOKEN, LONG_EXPIRE_TIME_FOR_TOKEN
from flask import g
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired, BadSignature
import common.restful as restful
import functools


class Permission(object):
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


def generate_token(uid, permanent=False):
    # 第一个参数为session用的密匙，第二个参数是token的有效期，单位为秒
    expire_time = LONG_EXPIRE_TIME_FOR_TOKEN if permanent else DEFAULT_EXPIRE_TIME_FOR_TOKEN
    s = Serializer(SECRET_KEY, expires_in=expire_time)
    token = s.dumps({"uid": uid}).decode("ascii")
    return token


class TokenValidator(object):
    def __init__(self, model):
        self.model = model
        self.s = Serializer(SECRET_KEY)

    def validate(self, token):
        try:
            # 转化为字典
            if hasattr(g, "cache") and g.cache.get_pointed(token, "uid")[0]:
                uid = g.cache.get_pointed(token, "uid")[0]
                print('cache', uid)
            else:
                data_dict = self.s.loads(token)
                uid = data_dict.get("uid")
                print('dict', uid)
        except SignatureExpired:
            # 签名已经过期
            return False, "签名已经过期"
        except BadSignature:
            # 签名值错误
            return False, "签名值错误"
        user = self.model.query.get(uid)
        if not user:
            return False, "该用户不存在"
        return True, user


class login_required(object):
    def __init__(self, permission):
        self.permission = permission
        self.s = Serializer(SECRET_KEY)

    def __call__(self, view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if not g.login:
                return restful.token_error(message=g.message)
            if g.user.has_permission(permission=self.permission):
                return view(*args, **kwargs)
            return restful.auth_error(message="您没有权限访问")        # restful.Response.auth_error
        return wrapper

