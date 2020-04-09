from flask import request, g
from .token import TokenValidator
from .cache import cms_cache, front_cache
from cms.models import CMSUser
from front.models import FrontUser
from config import IMAGE_ICON, IMAGE_PIC


cms_token_validator = TokenValidator(CMSUser)
front_token_validator = TokenValidator(FrontUser)


def hook_cms():
    base_hook(cms_token_validator, cms_cache)


def hook_front():
    base_hook(front_token_validator, front_cache)


def base_hook(token_validator, cache):
    # 从header中获取token值，并且将缓存加入上下文变量g中
    token = request.headers.get("Z-Token")
    g.IMAGE_ICON = IMAGE_ICON
    g.IMAGE_PIC = IMAGE_PIC
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
            g.message = user
    else:
        # 没有token，直接将g.login置为假
        g.login = False
        g.message = "没有token"
