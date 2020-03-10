from flask import request, g


def hook_before(token_validator, cache=None, no_user_msg="", no_token_msg=""):
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
