from flask import Blueprint, g
from flask_restful import Resource, Api
from common.restful import *
from common.token import login_required, Permission
from common.image_uploader import generate_uptoken
from common.hooks import hook_cms

cms_common_bp = Blueprint("cms_common", __name__, url_prefix="/cms/common")
api = Api(cms_common_bp)


class ImageView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        if not g.login:
            return auth_error(message=g.message)

        return success(data=dict(uptoken=generate_uptoken()))


api.add_resource(ImageView, "/image/", endpoint="cms_common_image")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_common_bp.before_request
def before_request():
    hook_cms()

