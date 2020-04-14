from flask import Blueprint, request, g
from sqlalchemy import func
from flask_restful import Resource, Api, fields, marshal_with
from common.token import login_required, Permission
from common.models import Board, Article, Tag
from common.cache import like_cache, article_cache
from common.hooks import hook_front
from exts import db
from common.restful import *
from ..models import FrontUser
from ..forms import ArticleForm


article_bp = Blueprint("article", __name__, url_prefix="/api/article")
api = Api(article_bp)


class PutView(Resource):
    """
    增加文章，全部都是post
    不知道需不需要做改的功能
    """

    method_decorators = [login_required(Permission.VISITOR)]

    def post(self):
        """
        登录之后user(author)的id保存在全局变量g中，
        因此不需要再传入新的用户id
        :board_id   所属板块
        :title      文章标题
        :content    正文
        :images     图片
        :tags       标签
        """
        form = ArticleForm.from_json(request.json)
        if not form.validate():
            return params_error(message=form.get_error())

        board_id = form.board_id.data
        board = Board.query.get(board_id)
        if not board:
            return source_error(message="板块不存在")

        # 表单验证成功后，共有两步操作
        # 首先，往数据库中存储文章
        title = form.title.data
        content = form.content.data
        tags = Tag.query_tags(*form.tags.data)
        # print(form.tags.data)
        # return success()
        images = ",".join([image + g.IMAGE_PIC for image in form.images.data])
        article = Article(title=title, content=content,
                          images=images, board_id=board_id,
                          author_id=g.user.id)
        article.board = board
        article.author = g.user
        article.add_tags(*tags)

        db.session.add(article)
        db.session.commit()

        return success()


class QueryView(Resource):
    """
    这个类用来查询文章列表，全部都是get请求
    模式一：按时间进行查询
    模式二：按热度进行查询（开发中）
    """

    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "articles": fields.List(fields.Nested({
                "article_id": fields.String,            # 文章id
                "title": fields.String,                 # 标题
                "content": fields.String,               # 正文
                "images": fields.List(fields.String),   # 文章图片
                "likes": fields.Integer,                # 点赞数
                "views": fields.Integer,                # 浏览数
                "comments": fields.Integer,             # 评论数
                "liked": fields.Boolean,                # 是否喜欢文章
                "tags": fields.List(fields.Nested({
                    "tag_id": fields.String,
                    "content": fields.String
                })),                                    # 标签
                "created": fields.Integer,              # 发表时间
                "board": fields.Nested({
                    "board_id": fields.String,
                    "name": fields.String,
                    "avatar": fields.String
                }),
                "author": fields.Nested({
                    "author_id": fields.String,
                    "username": fields.String,
                    "avatar": fields.String,
                    "gender": fields.Integer
                })
            })),
            "total": fields.Integer,
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        """
        接收参数：
        :mode       查询模式
        mode=new      按时间排序
        mode=hot      按热度排序
        :board_id   板块id，当其为0时不进行板块区分
        :author_id  作者id，可不传输，有值时按该值进行查询，无值时忽略该条件
        :offset     偏移量
        :limit      查询数量
        # :status     文章状态。默认为1
        """
        mode = request.args.get("mode")
        board_id = request.args.get("board_id", 0, type=int)
        author_id = request.args.get("author_id", None)
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 20, type=int)
        # status = request.args.get("status", 1, type=int)

        if mode not in ("hot", "new"):
            return params_error(message="不存在的排序方式")

        if mode == "new":
            # 板块id不等于0->按照板块id进行查询
            if board_id:
                board = Board.query.get(board_id)
                if not board:
                    return source_error(message="板块不存在")
                # articles = Article.query.filter_by(board_id=board_id, status=status)
                articles = Article.query.filter_by(board_id=board_id, status=1)
            # 板块id等于0->查询所有的帖子
            else:
                # articles = Article.query.filter_by(status=status)
                articles = Article.query.filter_by(status=1)

            # 作者id存在->按作者id查询
            if author_id:
                author = FrontUser.query.get(author_id)
                if not author:
                    return source_error(message="用户不存在")
                articles = articles.filter_by(author_id=author_id)

            total = articles.with_entities(func.count(Article.id)).scalar()
            articles = articles.order_by(Article.created.desc())[offset: offset+limit]
            return self.generate_response(articles, total)

        # 按照热度进行排序
        elif mode == "hot":
            return deny_error(message="该功能正在开发中")

        return server_error()

    @staticmethod
    @marshal_with(resource_fields)
    def generate_response(articles, total):
        """
        生成文章列表类型的返回数据
        """
        resp = Data()
        resp.articles = []
        resp.total = total
        user_likes = g.user.get_all_appreciation(cache=like_cache, attr="likes")
        # print(user_likes)
        for article in articles:
            data = Data()
            data.article_id = article.id
            data.title = article.title
            data.created = article.created.timestamp()
            data.content = article.content

            article_properties = article.get_property_cache(article_cache)
            # print(article_properties)
            data.likes = article_properties.get("likes", -1)
            data.views = article_properties.get("views", -1)
            data.comments = article_properties.get("views", -1)

            data.liked = article.is_liked(user_likes)

            data.board = Data()
            data.board.board_id = article.board.id
            data.board.name = article.board.name
            data.board.avatar = article.board.avatar

            data.author = Data()
            data.author.author_id = article.author_id
            data.author.username = article.author.username
            data.author.avatar = article.author.avatar
            data.author.gender = article.author.gender

            if article.images:
                data.images = article.images.split(",")
            else:
                data.images = []

            data.tags = [tag.marshal(Data) for tag in article.tags]

            resp.articles.append(data)

        return Response.success(data=resp)


class DeleteView(Resource):
    """
    删除文章的接口
    get请求
    管理员权限或作者权限
    需要有权限：Poster或
    """

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        """
        :article_id     文章id
        只要知道文章的id就可以删了
        """
        article_id = request.args.get("article_id")
        article = Article.query.get(article_id)
        if not article or not article.status:
            return source_error(message="文章已经被删除或不存在")

        author = g.user
        if author.has_permission(permission=Permission.POSTER, model=article):
            article.status = 0
        else:
            return auth_error(message="对不起，您不是文章作者，无权删除该文章")

        db.session.commit()
        return success()


class LikeArticleView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        article_id = request.args.get("article_id")
        if not article_id:
            return params_error(message="缺失文章id")

        # 有想过这一段代码，如果被人恶意利用存缓存怎么办？对方传过来一个不存在的article_id
        # article = Article.query.get(article_id)
        # if not article:
        #     return source_error(message="文章不存在")

        g.user.set_one_appreciation(cache=like_cache, sub_cache=article_cache, attr="likes", attr_id=article_id)
        return success()


class PointedView(Resource):
    """
    返回指定文章信息
    article: 文章
    """

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        article_id = request.args.get("article_id")
        if not article_id:
            return params_error(message="缺失文章id")
        article = Article.query.get(article_id)
        if not article or not article.status:
            return source_error(message="文章不存在")
        res = QueryView.generate_response(total=1, articles=[article])
        res["data"]["article"] = res["data"].pop("articles")[0]
        res["data"].pop("total")
        return res


api.add_resource(PutView, "/put/", endpoint="front_article_put")
api.add_resource(QueryView, "/query/", endpoint="front_article_query")
api.add_resource(DeleteView, "/delete/", endpoint="front_article_delete")
api.add_resource(LikeArticleView, "/like/", endpoint="front_article_like")
api.add_resource(PointedView, "/pointed/", endpoint="front_article_pointed")


@article_bp.before_request
def before_request():
    hook_front()
