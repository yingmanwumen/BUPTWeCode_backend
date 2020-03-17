from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from common.restful import Response, Data
from common.image_uploader import generate_uptoken
from common.hooks import hook_front
from common.token import login_required, Permission


common_bp = Blueprint("common", __name__, url_prefix="/api/common")
api = Api(common_bp)


class ImageView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "uptoken": fields.String
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    @marshal_with(resource_fields)
    def get(self):
        data = Data()
        data.uptoken = generate_uptoken()
        return Response.success(data=data)


api.add_resource(ImageView, "/image/", endpoint="front_image")


@common_bp.before_request
def before_request():
    hook_front(no_user_msg="登陆状态已过期", no_token_msg="未授权")

