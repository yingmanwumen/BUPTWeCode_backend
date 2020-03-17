from flask import request, g
from .token import TokenValidator
from .cache import MyRedis
from cms.models import CMSUser
from front.models import FrontUser


cms_token_validator = TokenValidator(CMSUser)
cms_cache = MyRedis(db=15, default_expire=3600, long_expire=86400)

front_cache = MyRedis(db=0, default_expire=3600, long_expire=86400)
front_token_validator = TokenValidator(FrontUser)


def hook_cms(no_user_msg="", no_token_msg=""):
    base_hook(cms_token_validator, cms_cache, no_user_msg, no_token_msg)


def hook_front(no_user_msg="", no_token_msg=""):
    base_hook(front_token_validator, front_cache, no_user_msg, no_token_msg)


def base_hook(token_validator, cache, no_user_msg="", no_token_msg=""):
    # 从header中获取token值，并且将缓存加入上下文变量g中
    token = request.headers.get("Z-Token")
    if cache:
        g.cache = cache
    if token:
        # 如果有token，尝试从数据库中获取用户
        res, user = token_validator.validate(token)
        if res and user:
            # 获取用户成功的话，g.login置为真，将user与token也绑定到上下文变量g
            g.login = True
            g.user = user
            g.token = token
        else:
            # 获取失败，说明token的值有问题
            g.login = False
            g.message = no_user_msg or user
    else:
        # 没有token，直接将g.login置为假
        g.login = False
        g.message = no_token_msg