from flask import Blueprint, request, g
from exts import db
from flask_restful import Resource, Api, fields, marshal_with
from sqlalchemy import func
from common.restful import *
from ..forms import BoardForm
from common.token import login_required, Permission
from common.models import Board, Article
from common.hooks import hook_cms
from common.cache import article_cache
from front.models import FrontUser
from ..models import CMSUser

cms_manager_bp = Blueprint("cms_manage", __name__, url_prefix="/cms/manage")
api = Api(cms_manager_bp)


class BoardView(Resource):
    """
    和板块视图相关的类视图
    get请求可处理的业务: 获取boards数据
    post请求可处理的业务: 新增board, 修改已有board，删除board
    """
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "boards": fields.List(fields.Nested({
                "board_id": fields.Integer,     # 板块唯一标识
                "name": fields.String,          # 板块名称
                "desc": fields.String,          # 板块描述
                "created": fields.Integer,      # 板块创建时间
                "avatar": fields.String,    # 板块头像
                "articles": fields.Integer      # 板块下所含文章数量
            })),
            "total": fields.Integer             # 板块总数
        })
    }

    method_decorators = [login_required(Permission.BOADER)]

    @marshal_with(resource_fields)
    def get(self):
        """
        负责返回板块的查询，接受三个参数
        offset: 偏移，默认为0
        limit: 数量，默认为10
        status: 板块状态，默认查询状态status为1的板块
        :return:
        """
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        status = request.args.get("status", 1, type=int)

        # status的值用于筛选对应status值的boards，1为可见，0为不可见
        boards = Board.query.filter_by(status=status)
        # 优化后的sql count函数
        total = boards.with_entities(func.count(Board.id)).scalar()
        # 用切片筛选结果
        boards = boards[offset:offset+limit]

        return self._generate_response(boards, total)

    def post(self):
        form = BoardForm(request.form)
        if not form.validate():
            return params_error(message=form.get_error())
            # 表单验证通过，先获取表单的值
        name = form.name.data
        desc = form.desc.data
        avatar = form.avatar.data.split("?imageView2")[0]
        board_id = form.board_id.data
        status = form.status.data

        if board_id:
            # 如果表单的board_id不为0，说明这是一个编辑的请求，并获取相应的board
            board = Board.query.filter_by(id=board_id).first()
            if not board:
                return source_error(message="数据库中找不到该板块")

            # 存在该板块，设为对应编辑的值
            board.name = name
            board.desc = desc
            board.avatar = avatar + g.IMAGE_ICON
            board.status = status

            # 提交至数据库
            db.session.commit()

        else:
            # 如果表单的board_id为0，说明这是一个新建板块请求
            # 新建一个板块，并提交到数据库
            board = Board(name=name, desc=desc, avatar=avatar)
            db.session.add(board)
            db.session.commit()

        return success()

    @staticmethod
    @marshal_with(resource_fields)
    def _generate_response(boards, total):
        """
        返回一个格式化的board数据对象
        """
        resp = Data()
        resp.boards = []
        for board in boards:
            data = Data()
            data.name = board.name
            data.board_id = board.id
            data.desc = board.desc
            data.avatar = board.avatar
            data.created = board.created.timestamp()
            data.articles = board.articles.count()
            resp.boards.append(data)
        resp.total = total
        return Response.success(data=resp)


class OperatorView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "total": fields.Integer,
            "users": fields.List(fields.Nested({
                "uid": fields.String,
                "username": fields.String,
                "created": fields.Integer,
                "avatar": fields.String,
                "signature": fields.String,
                "status": fields.Integer
            }))
        })
    }

    method_decorators = [login_required(Permission.CMSUSER)]

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        users = FrontUser.query.filter(FrontUser.permission > 1)
        total = users.with_entities(func.count(FrontUser.id)).scalar()
        users = users[offset:offset + limit]
        return self.generate_response(total, users)

    def post(self):
        mode = request.form.get("mode")
        if mode not in ("add", "sub"):
            return params_error(message="mode错误")

        uid = request.form.get("uid")
        if not uid:
            return params_error(message="缺失用户id")
        user = FrontUser.query.get(uid)
        if not user:
            return source_error(message="用户不存在")

        is_operator = user.permission > 1
        if mode == "add":
            if is_operator:
                return params_error(message="该用户已经是运营了")
            user.permission = Permission.OPERATOR
        elif mode == "sub":
            if not is_operator:
                return params_error(message="该用户并不是运营")
            user.permission = Permission.VISITOR
        db.session.commit()
        return success()

    @staticmethod
    @marshal_with(resource_fields)
    def generate_response(total, users):
        resp = Data()
        resp.users = []
        resp.total = total
        for user in users:
            data = Data()
            data.username = user.username
            data.signature = user.signature
            data.avatar = user.avatar
            data.uid = user.id
            data.created = user.created.timestamp()
            data.status = user.status
            resp.users.append(data)
        return Response.success(data=resp)


class FrontUserView(Resource):

    method_decorators = [login_required(Permission.FRONTUSER)]

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        status = request.args.get("status", 1, type=int)
        users = FrontUser.query.filter_by(status=status)
        total = users.with_entities(func.count(FrontUser.id)).scalar()
        users = users[offset:offset + limit]
        return OperatorView.generate_response(total, users)

    def post(self):
        mode = request.form.get("mode")
        if mode not in ("add", "sub"):
            return params_error(message="不存在的模式")

        uid = request.form.get("uid")
        if not uid:
            return params_error(message="缺失用户id")

        user = FrontUser.query.get(uid)
        if not user:
            return source_error(message="用户不存在")

        is_blocked = user.status == 0
        if mode == "add":
            if is_blocked:
                return params_error(message="该用户已经被封禁了")
            user.status = 0
        elif mode == "sub":
            if not is_blocked:
                return params_error(message="该用户没有被封禁")
            user.status = 1
        db.session.commit()
        return success()


class ArticleView(Resource):
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
                "quality": fields.Integer,              # 是否精品
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

    method_decorators = [login_required(Permission.POSTER)]

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 20, type=int)
        status = request.args.get("status", 1, type=int)

        articles = Article.query.filter_by(status=status)
        total = articles.with_entities(func.count(Article.id)).scalar()
        articles = articles.order_by(Article.created.desc())[offset: offset + limit]
        return self.generate_response(articles, total)

    def post(self):
        mode = request.form.get("mode")
        if mode not in ("sub", "add"):
            return params_error(message="不存在的模式")

        article_id = request.form.get("article_id")
        if not article_id:
            return params_error(message="缺失文章id")

        article = Article.query.get(article_id)
        if not article:
            return source_error(message="文章不存在")

        is_deleted = article.status == 0
        if mode == "add":
            if is_deleted:
                return params_error(message="文章已经是删除状态的了")
            article.status = 0

        elif mode == "sub":
            if not is_deleted:
                return params_error(message="文章状态正常")
            article.status = 1

        db.session.commit()
        return success()

    @staticmethod
    @marshal_with(resource_fields)
    def generate_response(articles, total):
        resp = Data()
        resp.total = total
        resp.articles = []
        for article in articles:
            data = Data()
            data.article_id = article.id
            data.title = article.title
            data.created = article.created.timestamp()
            data.content = article.content
            data.quality = article.quality

            article_properties = article.get_property_cache(article_cache)
            data.likes = article_properties.get("likes", -1)
            data.views = article_properties.get("views", -1)
            data.comments = article_properties.get("comments", -1)

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


class CMSUserView(Resource):
    resource_fields = {
        "code": fields.Integer,  # 状态码
        "message": fields.String,  # 状态描述
        "data": fields.Nested({
            "users": fields.List(fields.Nested({  # 用户信息
                "uid": fields.String,
                "role": fields.String,  # 角色
                "username": fields.String,  # 用户名
                "display_name": fields.String,  # 昵称, 可以为空
                "desc": fields.String,  # 个人描述
                "created": fields.Integer  # 创建时间
            })),
            "total": fields.Integer
        })
    }

    method_decorators = [login_required(Permission.ROOTER)]

    role_mapping = {
        Permission.VISITOR: "VISITOR",
        Permission.OPERATOR: "OPERATOR",
        Permission.ADMIN: "ADMIN",
        Permission.ALL_PERMISSION: "DEVELOPER",
        "VISITOR": Permission.VISITOR,
        "OPERATOR": Permission.OPERATOR,
        "ADMIN": Permission.ADMIN,
        "DEVELOPER": Permission.ALL_PERMISSION
    }

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        users = CMSUser.query.filter(CMSUser.id != g.user.id)
        total = users.with_entities(func.count(CMSUser.id)).scalar()
        users = users[offset:offset + limit]
        return self.generate_response(total, users)

    def post(self):
        role = request.form.get("role")
        if role not in ("VISITOR", "OPERATOR", "ADMIN"):
            return params_error(message="role错误")
        permission = self.role_mapping.get(role, 1)

        uid = request.form.get("uid")
        if not uid:
            return params_error(message="缺失用户id")
        user = CMSUser.query.get(uid)
        if not user:
            return source_error(message="用户不存在")

        user.permission = permission
        db.session.commit()
        return success()

    @staticmethod
    @marshal_with(resource_fields)
    def generate_response(total, users):
        resp = Data()
        resp.total = total
        resp.users = []
        for user in users:
            data = Data()
            data.uid = user.id
            data.role = CMSUserView.role_mapping[user.permission]
            data.created = user.created.timestamp()
            data.display_name = user.display_name
            data.username = user.username
            data.desc = user.desc
            resp.users.append(data)
        return Response.success(data=resp)


api.add_resource(BoardView, "/board/", endpoint="board")
api.add_resource(OperatorView, "/operator/", endpoint="cms_manage_operate")
api.add_resource(FrontUserView, "/front_user/", endpoint="cms_manage_front_user")
api.add_resource(ArticleView, "/article/", endpoint="cms_manage_article")
api.add_resource(CMSUserView, "/cms_user/", endpoint="cms_manage_cms_user")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_manager_bp.before_request
def before_request():
    hook_cms()

