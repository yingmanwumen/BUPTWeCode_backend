from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from front.forms.article_form import ArticleForm
from ..models import FrontUser
from common.restful import Response
from common.models import Board, Article
from common.token import TokenValidator
from common.cache import MyRedis
from common.hooks import hook_before
from .wx_view import cache
from exts import db


article_bp = Blueprint("article", __name__, url_prefix="/api/article")
token_validator = TokenValidator(FrontUser)
article_cache = MyRedis(db=1, default_expire=3600, long_expire=86400)
api = Api(article_bp)


class ArticleView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "articles": fields.List(fields.Nested({
                "id": fields.String,
                "title": fields.String,
                "content": fields.String,
                "images": fields.List(fields.String),
                "author": fields.Nested({
                    "id": fields.String,
                    "avatarUrl": fields.String,
                    "username": fields.String,
                    "gender": fields.Integer
                }),
            }))
        })
    }

    @marshal_with(resource_fields)
    def post(self):
        if not g.login:
            return Response.auth_error(message=g.message)

        form = ArticleForm(request.form)
        if not form.validate():
            return Response.params_error(message=form.get_error())

        board_id = form.board_id.data
        board = Board.query.get(board_id)
        if not board:
            return Response.source_error(message="板块不存在")

        title = form.title.data
        content = form.content.data
        images = form.imageList.data
        article = Article(title=title, content=content, images=images)
        article.board = board
        article.author = g.user
        db.session.add(article)
        db.session.commit()
        return Response.success()


api.add_resource(ArticleView, "/operate/", endpoint="article_operate")


@article_bp.before_request
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
