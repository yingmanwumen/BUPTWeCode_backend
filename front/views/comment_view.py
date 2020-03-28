from flask import Blueprint, request, g
from sqlalchemy import func
from flask_restful import Resource, Api, fields, marshal_with
from common.restful import *
from common.hooks import hook_front
from common.token import login_required, Permission
from common.models import Article, Comment
from ..forms import CommentForm
from exts import db

comment_bp = Blueprint("comment", __name__, url_prefix="/api/comment")
api = Api(comment_bp)


class CommentPutView(Resource):
    """
    添加评论视图
    content: 评论内容
    images: 评论图片
    article_id: 评论对应文章
    """

    method_decorators = [login_required(Permission.VISITOR)]

    def post(self):
        form = CommentForm.from_json(request.json)
        if not form.validate():
            return params_error(message=form.get_error())
        article_id = form.article_id.data
        article = Article.query.get(article_id)
        if not article:
            return source_error(message="文章不存在")

        content = form.content.data
        images = ",".join([image + g.IMAGE_PIC for image in form.images.data])

        comment = Comment(content=content, images=images)
        comment.author = g.user
        comment.article = article
        db.session.add(comment)
        db.session.commit()


class CommentDeleteView(Resource):
    """
    删除评论视图
    comment_id: 评论id
    """
    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        comment_id = request.args.get("comment_id")
        if not comment_id:
            return params_error(message="缺失评论id")

        comment = Comment.query.get(comment_id)
        if not comment or comment.status == 1:
            return source_error(message="评论不存在")

        if not g.user.has_permission(Permission.COMMENTER, model=comment):
            return auth_error(message="您没有权限")

        comment.status = 0
        db.session.commit()
        return success()


class CommentQueryView(Resource):
    """
    评论查询视图
    article_id: 文章id
    offset: 起始位置
    limit: 返回评论数量
    """
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "comments": fields.List(fields.Nested({
                "author": fields.Nested({
                    "author_id": fields.String,
                    "username": fields.String,
                    "avatar": fields.String,
                    "gender": fields.Integer,
                }),
                "content": fields.String,
                "images": fields.List(fields.String),
                "created": fields.Integer
            })),
            "total": fields.Integer
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        article_id = request.args.get("article_id")
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 20, type=int)

        if not article_id:
            return params_error(message="缺失文章id")

        article = Article.query.get(article_id)
        if not article:
            return source_error(message="文章不存在")

        comments = article.comments.query.filter_by(status=1)
        total = comments.with_entities(func.count(Comment.id)).scalar()
        comments = comments.order_by(Comment.created.desc())[offset:offset+limit]
        return self._generate_response(comments, total)

    @marshal_with(resource_fields)
    def _generate_response(self, comments, total):
        """
        返回评论类响应
        :param comments:
        :param total:
        :return:
        """
        resp = Data()
        resp.total = total
        resp.comments = []
        for comment in comments:
            data = Data()
            data.content = comment.content
            data.created = comment.created.timestamp()

            data.author = Data()
            data.author.author_id = comment.author_id
            data.author.username = comment.author.username
            data.author.avatar = comment.author.avatar
            data.author.gender = comment.author.gender

            if comment.images:
                data.images = comment.images.split(",")
            else:
                data.images = []
            resp.comments.append(data)
        return Response.success(data=resp)


api.add_resource(CommentPutView, "/add/", endpoint="front_comment_add")
api.add_resource(CommentQueryView, "/query/", endpoint="front_comment_query")
api.add_resource(CommentDeleteView, "/delete/", endpoint="front_comment_delete")


@comment_bp.before_request
def before_request():
    hook_front(no_user_msg="登陆状态已过期", no_token_msg="未授权")
