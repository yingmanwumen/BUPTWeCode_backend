from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from common.token import TokenValidator
from common.restful import Response, Data
from common.image_uploader import generate_uptoken
from common.hooks import hook_before
from ..models import FrontUser
from .wx_view import cache


common_bp = Blueprint("common", __name__, url_prefix="/api/common")
api = Api(common_bp)
token_validator = TokenValidator(FrontUser)


class ImageView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "uptoken": fields.String
        })
    }

    @marshal_with(resource_fields)
    def get(self):
        if not g.login:
            return Response.auth_error(message=g.message)

        data = Data()
        data.uptoken = generate_uptoken()
        return Response.success(data=data)


api.add_resource(ImageView, "/image/", endpoint="front_image")


@common_bp.before_request
def before_request():
    hook_before(token_validator, cache, no_user_msg="登陆状态已过期", no_token_msg="未授权")
    # """
    # 若没有携带token，说明是未授权，直接跳过下属步骤
    # 1。先从缓存中通过token的值来获取uid，进而获取用户的信息
    # 2。如果缓存中没有，通过token解析获取uid，进而获取用户的信息
    # 3。如果获取用户信息成功，说明是老用户
    # 4。如果获取用户信息失败，说明老用户的登陆状态已经过期
    # :return:
    # """
    # token = request.headers.get("Z-Token")
    # g.cache = cache
    # if token:
    #     res, user = token_validator.validate(token)
    #     if res and user:
    #         g.login = True
    #         g.user = user
    #         g.token = token
    #     else:
    #         g.login = False
    #         g.message = "登陆状态已经过期"
    # else:
    #     g.login = False
    #     g.message = "未授权"
