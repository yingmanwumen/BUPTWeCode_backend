from flask import Blueprint, request, g
from sqlalchemy import func
from flask_restful import Resource, Api, fields, marshal_with
from common.restful import *
from common.hooks import hook_front
from common.token import login_required, Permission
from common.models import Article, Comment, SubComment
from common.cache import article_cache, rate_cache, comment_cache
from ..forms import CommentForm, SubCommentForm
from ..models import FrontUser
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
        if not article or not article.status:
            return source_error(message="文章不存在")

        content = form.content.data
        images = ",".join([image + g.IMAGE_PIC for image in form.images.data])

        comment = Comment(content=content, images=images)
        comment.author = g.user
        comment.article = article
        db.session.add(comment)
        db.session.commit()
        article.cache_increase(article_cache, field="comments")
        return success()


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
        if not comment or not comment.status:
            return source_error(message="评论不存在")

        if not g.user.has_permission(Permission.COMMENTER, model=comment):
            return auth_error(message="您没有权限")

        comment.status = 0
        db.session.commit()
        comment.article.cache_increase(article_cache, field="comments", amount=-1)
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
                "created": fields.Integer,
                "comment_id": fields.String,
                "sub_comments": fields.Integer,
                "rates": fields.Integer,
                "rated": fields.Boolean
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

        comments = article.comments.filter_by(status=1)
        total = comments.with_entities(func.count(Comment.id)).scalar()
        comments = comments.order_by(Comment.created.asc())[offset:offset+limit]

        if not offset:
            article.cache_increase(article_cache, field="views")

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
        user_rates = g.user.get_all_appreciation(cache=rate_cache, attr="rates")
        for comment in comments:
            data = Data()
            data.content = comment.content
            data.created = comment.created.timestamp()
            data.comment_id = comment.id
            data.rated = comment.is_rated(user_rates)

            comment_properties = comment.get_property_cache(comment_cache)
            data.rates = comment_properties["rates"]
            data.sub_comments = comment_properties["sub_comments"]

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


class SubCommentPutView(Resource):
    """
    添加楼中楼视图
    comment_id: 对应评论id
    acceptor_id: 对应接受者uid
    content: 楼中楼内容
    """
    method_decorators = [login_required(Permission.VISITOR)]

    def post(self):
        form = SubCommentForm(request.form)
        if not form.validate():
            return params_error(message=form.get_error())

        comment_id = form.comment_id.data
        acceptor_id = form.acceptor_id.data

        comment = Comment.query.get(comment_id)
        if not comment or not comment.status:
            return source_error(message="评论不存在")

        acceptor = FrontUser.query.get(acceptor_id)
        if not acceptor:
            return source_error(message="该用户不存在")

        content = form.content.data
        sub_comment = SubComment(content=content)
        sub_comment.acceptor = acceptor
        sub_comment.author = g.user
        sub_comment.comment = comment

        db.session.add(sub_comment)
        db.session.commit()
        comment.cache_increase(comment_cache, field="sub_comments")
        return success()


class SubCommentDeleteView(Resource):
    """
    删除楼中楼视图
    sub_comment_id: 楼中楼id
    """
    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        sub_comment_id = request.args.get("sub_comment_id")
        if not sub_comment_id:
            return params_error(message="缺失楼中楼id")

        sub_comment = SubComment.query.get(sub_comment_id)
        if not sub_comment or not sub_comment.status:
            return source_error(message="楼中楼不存在")

        if not g.user.has_permission(Permission.COMMENTER, sub_comment):
            return auth_error(message="您没有权限")

        sub_comment.status = 0
        db.session.commit()
        sub_comment.comment.cache_increase(comment_cache, field="sub_comments", amount=-1)
        return success()


class SubCommentQueryView(Resource):
    """
    查询楼中楼视图
    comment_id: 评论id
    offset: 起始位置
    limit: 返回数量
    """
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "sub_comments": fields.List(fields.Nested({
                "author": fields.Nested({
                    "author_id": fields.String,
                    "username": fields.String,
                    "avatar": fields.String,
                    "gender": fields.Integer,
                }),
                "acceptor": fields.Nested({
                    "acceptor_id": fields.String,
                    "username": fields.String,
                    "avatar": fields.String,
                    "gender": fields.Integer,
                }),
                "content": fields.String,
                "created": fields.Integer,
                "sub_comment_id": fields.String
            })),
            "total": fields.Integer
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        comment_id = request.args.get("comment_id")
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 20, type=int)

        if not comment_id:
            return params_error(message="缺失评论id")

        comment = Comment.query.get(comment_id)
        if not comment or not comment.status:
            return source_error(message="评论不存在")

        sub_comments = comment.sub_comments.filter_by(status=1)
        total = sub_comments.with_entities(func.count(SubComment.id)).scalar()
        sub_comments = sub_comments.order_by(SubComment.created.asc())[offset:offset + limit]
        return self._generate_response(sub_comments, total)

    @marshal_with(resource_fields)
    def _generate_response(self, sub_comments, total):
        resp = Data()
        resp.total = total
        resp.sub_comments = []
        for sub_comment in sub_comments:
            data = Data()
            data.content = sub_comment.content
            data.created = sub_comment.created.timestamp()
            data.sub_comment_id = sub_comment.id

            data.author = Data()
            data.author.author_id = sub_comment.author_id
            data.author.username = sub_comment.author.username
            data.author.avatar = sub_comment.author.avatar
            data.author.gender = sub_comment.author.gender

            data.acceptor = Data()
            data.acceptor.acceptor_id = sub_comment.acceptor_id
            data.acceptor.username = sub_comment.acceptor.username
            data.acceptor.avatar = sub_comment.acceptor.avatar
            data.acceptor.gender = sub_comment.acceptor.gender

            resp.sub_comments.append(data)
        return Response.success(data=resp)


class RateCommentView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        comment_id = request.args.get("comment_id")
        if not comment_id:
            return params_error(message="缺失评论id")

        # 有想过这一段代码，如果被人恶意利用存缓存怎么办？对方传过来一个不存在的comment_id
        # comment = Comment.query.get(comment_id)
        # if not comment:
        #     return source_error(message="评论不存在")

        g.user.set_one_appreciation(cache=rate_cache, sub_cache=comment_cache, attr="rates", attr_id=comment_id)
        return success()


api.add_resource(CommentPutView, "/add/", endpoint="front_comment_add")
api.add_resource(CommentQueryView, "/query/", endpoint="front_comment_query")
api.add_resource(CommentDeleteView, "/delete/", endpoint="front_comment_delete")
api.add_resource(RateCommentView, "/rate/", endpoint="front_comment_rate")

api.add_resource(SubCommentPutView, "/sub/add/", endpoint="front_sub_comment_add")
api.add_resource(SubCommentQueryView, "/sub/query/", endpoint="front_sub_comment_query")
api.add_resource(SubCommentDeleteView, "/sub/delete/", endpoint="front_sub_comment_delete")


@comment_bp.before_request
def before_request():
    hook_front()
