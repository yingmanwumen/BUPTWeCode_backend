from flask import Blueprint, g, request
from flask_restful import Resource, Api, fields, marshal_with
from exts import db
from common.restful import *
from common.token import login_required, Permission
from common.image_uploader import generate_uptoken
from common.hooks import hook_cms
from common.models import Article, Comment, SubComment
from front.models import FrontUser

cms_common_bp = Blueprint("cms_common", __name__, url_prefix="/cms/common")
api = Api(cms_common_bp)


class ImageView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        if not g.login:
            return auth_error(message=g.message)

        return success(data=dict(uptoken=generate_uptoken()))


class MultiQueryView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "item": fields.Nested({
                "item_id": fields.String,
                "title": fields.String,
                "content": fields.String,
                "images": fields.List(fields.String),
                "status": fields.Integer,
                "created": fields.Integer,
            }),
            "user": fields.Nested({
                "user_id": fields.String,
                "avatar": fields.String,
                "username": fields.String,
                "signature": fields.String,
                "gender": fields.Integer,
                "created": fields.Integer,
                "status": fields.Integer
            })
        })
    }

    method_decorators = [login_required(Permission.FRONTUSER)]

    mapping = {
        "article": Article,
        "comment": Comment,
        "sub_comment": SubComment,
        "user": FrontUser
    }

    def get(self):
        item_id = request.args.get("item_id")
        if not item_id:
            return params_error(message="缺失id")
        category = request.args.get("category")
        if category not in ("article", "comment", "sub_comment", "user"):
            return params_error(message="种类错误")

        item_orm = self.mapping[category]
        item = item_orm.query.get(item_id)
        if not item:
            return source_error(message="找不到")

        if category == "user":
            return self.generate_response(item, only_user=True)
        elif category == "article":
            return self.generate_response(item)
        elif category == "comment":
            return self.generate_response(item, no_title=True)
        elif category == "sub_comment":
            return self.generate_response(item, no_title=True, no_images=True)
        return params_error(message="你到达了世界的尽头")

    @marshal_with(resource_fields)
    def generate_response(self, item, only_user=False, no_title=False, no_images=False):
        resp = Data()
        resp.user = Data()
        resp.item = Data()
        if only_user:
            resp.user.username = item.username
            resp.user.user_id = item.id
            resp.user.gender = item.gender
            resp.user.avatar = item.avatar
            resp.user.signature = item.signature
            resp.user.created = item.created.timestamp()
            resp.user.status = item.status
            return Response.success(data=resp)

        resp.item.created = item.created.timestamp()
        resp.item.status = item.status
        resp.item.content = item.content
        resp.item.item_id = item.id
        resp.item.title = item.title if not no_title else ""
        resp.item.images = []
        if not no_images and item.images:
            resp.item.images = item.images.split(",")

        resp.user.username = item.author.username
        resp.user.user_id = item.author.id
        resp.user.gender = item.author.gender
        resp.user.avatar = item.author.avatar
        resp.user.signature = item.author.signature
        resp.user.created = item.author.created.timestamp()
        resp.user.status = item.author.status
        return Response.success(data=resp)


class MultiPutView(Resource):

    method_decorators = [login_required(Permission.FRONTUSER)]

    mapping = {
        "article": Article,
        "comment": Comment,
        "sub_comment": SubComment,
        "user": FrontUser
    }

    def get(self):
        item_id = request.args.get("item_id")
        if not item_id:
            return params_error(message="缺失id")
        category = request.args.get("category")
        if category not in ("article", "comment", "sub_comment", "user"):
            return params_error(message="种类错误")

        item_orm = self.mapping[category]
        item = item_orm.query.get(item_id)
        if not item:
            return source_error(message="找不到")

        item.status = 1 - item.status
        db.session.commit()
        return success()


api.add_resource(ImageView, "/image/", endpoint="cms_common_image")
api.add_resource(MultiQueryView, "/query/", endpoint="cms_common_query")
api.add_resource(MultiPutView, "/put/", endpoint="cms_common_put")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_common_bp.before_request
def before_request():
    hook_cms()

