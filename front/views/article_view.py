from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from front.forms.article_form import ArticleForm
from common.restful import Response
from common.models import Board, Article
from common.hooks import hook_front
from exts import db


article_bp = Blueprint("article", __name__, url_prefix="/api/article")
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
    hook_front(no_user_msg="登陆状态已过期", no_token_msg="未授权")

