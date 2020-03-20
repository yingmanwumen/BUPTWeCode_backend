from flask import Blueprint, request, g
from sqlalchemy import func
from flask_restful import Resource, Api, fields, marshal_with
from front.forms.article_form import ArticleForm
from common.token import login_required, Permission
from common.models import Board, Article
from common.cache import MyRedis
from common.hooks import hook_front
from exts import db
from common.restful import *

article_bp = Blueprint("article", __name__, url_prefix="/api/article")
# 长过期时间改为一个月
article_cache = MyRedis(db=1, default_expire=3600, long_expire=86400 * 30)
api = Api(article_bp)


class CacheArticle(object):
    """
    这个类封装了一些与文章缓存有关的函数
    """

    @staticmethod
    def score_list(article, score=0):
        """
        维护存放文章id的有序集合
        文章缓存不存在：新增缓存
        文章缓存存在：更新位置
        """
        # 将字段的值和score组装为一个dict存入
        mapping = {article.id: score}
        article_cache.sorted_add("SCORE_LIST", mapping)

    @staticmethod
    def set_entry(article):
        """
        设置存放文章不必要信息的哈希表
        """
        # 因为redis里面主键是唯一的，文章id在有序集合中已经使用
        # 加上sub避免产生键名覆盖
        article_id = "sub" + article.id
        val = {
            "view": 0,
            "like": 0,
            "comment": 0,
            "collected": 0,
            "tag": ""
        }

        if not article_cache.exists(article_id):
            return article_cache.set(article_id, val, permanent=True)

    @staticmethod
    def del_entry(article):
        """
        删除哈希表中的有关文章信息
        返回删除的数量
        """
        article_id = "sub" + article.id
        return article_cache.delete(article_id)

    @staticmethod
    def del_score(article):
        """
        删除排名表中的有关信息
        """
        return article_cache.delete(article.id)

    @staticmethod
    def set_val(article, key, val):
        """
        设置保存文章有关信息的哈希表中
        有关的键的域的值
        参数key为字符串类型
        """
        article_id = "sub" + article.id
        return article_cache.set_pointed(article_id, key, val, permanent=True)

    @staticmethod
    def incrby(article, key, amount=1):
        """
        将哈希表中的某个键的值加一
        这个键的值必须能被int()转化为数字
        参数key为字符串类型
        """
        article_id = "sub" + article.id
        return article_cache.incrby(article_id, key, amount)

    @staticmethod
    def get_val(article, key):
        """
        获取哈希表中某个键的值
        参数key为字符串类型
        """
        article_id = "sub" + article.id
        return article_cache.get_pointed(article_id, key)[0]


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
        :imageList  图片
        """
        form = ArticleForm(request.form)
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
        images = form.imageList.data
        article = Article(title=title, content=content,
                          images=images, board_id=board_id,
                          author_id=g.user.id)
        article.board = board
        article.author = g.user

        db.session.add(article)
        db.session.commit()

        # 接下来，维护缓存中的两张表
        # 一个有序集合：存储id与score
        # 一个hash表，存储文章的主要信息
        # 为了便于使用，在外面封装有关操作的函数
        CacheArticle.score_list(article)
        CacheArticle.set_entry(article)

        return success()


class QueryView(Resource):
    """
    这个类用来查询文章列表，全部都是get请求
    有两大查询方式，
    方式一：列表查询
    方式二：文章正文查询
    当使用列表查询时，有2种查询模式
    模式一：按时间进行查询
    模式二：按热度进行查询（开发中）
    """

    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "articles": fields.List(fields.Nested({
                "id": fields.String,  # 文章id
                "title": fields.String,  # 标题
                "content": fields.String,  # 正文，当使用列表查询时返回""
                "imageList": fields.String,  # 图像列表，当使用列表查询时返回""
                "like": fields.Integer,  # 点赞数
                "view": fields.Integer,  # 浏览数
                "comment": fields.Integer,  # 评论数
                "collected": fields.Integer,  # 收藏数
                "tag": fields.String,  # 标签
                "created": fields.Integer,  # 发表时间
                "board_id": fields.Integer,  # 所属板块id
                "author_id": fields.String,  # 作者id
            })),
            "total": fields.Integer,
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        """
        :method     查询方式
        method=1    列表查询
        method=2    文章正文查询
        默认值为1
        """
        method = request.args.get("method", 1, type=int)

        if method == 1:
            res = self.get_list()
        else:
            res = self.get_content()
        return res

    @marshal_with(resource_fields)
    def get_list(self):
        """
        接收参数：
        :mode       查询模式
        mode=1      按时间排序
        mode=2      按热度排序
        :board_id   板块id，当其为0时不进行板块区分
        :author_id  作者id，可不传输，有值时按该值进行查询，无值时忽略该条件
        :offset     偏移量
        :limit      查询数量
        :status     文章状态。默认为1
        """
        mode = request.args.get("mode", 1, type=int)
        board_id = request.args.get("board_id", 0, type=int)
        author_id = request.args.get("author_id", None)
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 20, type=int)
        status = request.args.get("status", 1, type=int)

        # 板块id不等于0->按照板块id进行查询
        if board_id:
            articles = Article.query.filter_by(board_id=board_id, status=status)
        # 板块id等于0->查询所有的帖子
        else:
            articles = Article.query.filter_by(status=status)

        # 作者id存在->按作者id查询
        if author_id:
            articles = articles.filter_by(author_id=author_id)

        # 按照时间排序
        if mode == 1:
            lists = articles.order_by(Article.created.desc())
        # 按照热度进行排序
        elif mode == 2:
            return Response.deny_error(message="该功能正在开发中")
        else:
            return Response.params_error(message="不存在这种排序方式")

        data = Data()
        data.articles = []
        for article in lists.slice(offset, offset + limit):
            data.articles.append(self._generate_article(article, method=0))
        data.total = articles.with_entities(func.count(Article.id)).scalar()

        # 如果没有找到文章
        if len(data.articles) == 0:
            return Response.source_error(message="这里什么都没有。。")

        return Response.success(data=data)

    @marshal_with(resource_fields)
    def get_content(self):
        """
        获取文章正文
        article_id
        status
        """
        article_id = request.args.get("article_id", None)
        status = request.args.get("status", 1, type=int)

        if not article_id:
            return Response.params_error(message="请输入文章id！！")

        article = Article.query.filter_by(id=article_id, status=status).first()
        if not article:
            return Response.source_error(message="文章找不到了。。")

        # 有查看正文的请求时浏览数+1
        # 后续可能会增加判断条件，比如一个用户只算一次浏览
        CacheArticle.incrby(article, "view")
        data = Data()
        data.articles = [self._generate_article(article, method=2)]
        data.total = 1
        return Response.success(data=data)

    @staticmethod
    def _generate_article(article, method=1):
        """
        生成文章列表类型的返回数据
        """
        data = Data()
        data.id = article.id
        data.title = article.title
        data.like = CacheArticle.get_val(article, "like")
        data.view = CacheArticle.get_val(article, "view")
        data.comment = CacheArticle.get_val(article, "comment")
        data.collected = CacheArticle.get_val(article, "collected")
        data.tag = CacheArticle.get_val(article, "tag") or ""
        data.created = article.created.timestamp()
        data.board_id = article.board_id
        data.author_id = article.author_id

        if method:
            data.content = article.content
            data.imageList = article.images
        else:
            data.content = ""
            data.imageList = ""
        return data


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
        if not article or article.status == 0:
            return source_error("文章已经被删除或不存在")

        author = g.user
        if author.has_permission(permission=Permission.POSTER, model=article):
            # 删除操作：先将缓存中的数据移除，再将数据库中status置为0
            CacheArticle.del_entry(article)
            CacheArticle.del_score(article)
            article.status = 0
        else:
            return auth_error(message="对不起，您不是文章作者，无权删除该文章")

        db.session.commit()
        return success()


api.add_resource(PutView, "/put/", endpoint="put")
api.add_resource(QueryView, "/query/", endpoint="query")
api.add_resource(DeleteView, "/delete/", endpoint="delete")


@article_bp.before_request
def before_request():
    hook_front(no_user_msg="登陆状态已过期", no_token_msg="未授权")
