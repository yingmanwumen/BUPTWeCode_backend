from config import SECRET_KEY, DEFAULT_EXPIRE_TIME_FOR_TOKEN, LONG_EXPIRE_TIME_FOR_TOKEN
from flask import g
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired, BadSignature
import common.restful as restful
import functools


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

