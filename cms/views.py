from flask import Blueprint, request, g
from exts import db
from flask_restful import Resource, Api, fields, marshal_with
from sqlalchemy import func
from common.restful import *
from .models import CMSUser, CMSPermission
from .forms import LoginForm, ProfileForm, BoardForm
from common.token import login_required, generate_token, TokenValidator
from common.cache import MyRedis
from common.models import Board
from common.image_uploader import generate_uptoken
from common.hooks import hook_before

cms_bp = Blueprint("cms", __name__, url_prefix="/cms")
api = Api(cms_bp)

token_validator = TokenValidator(CMSUser)
cache = MyRedis(db=15, default_expire=3600, long_expire=86400)


class LoginView(Resource):
    """
    get负责验证登陆状态是否有效
    post负责登陆
    接收username与password两个参数
    """
    resource_fields = {
        "code": fields.Integer,         # 状态码
        "message": fields.String,       # 状态描述
        "data": fields.Nested({
            "token": fields.String,     # token值
            "user": fields.Nested({                 # 用户信息
                "role": fields.String,              # 角色
                "username": fields.String,          # 用户名
                "display_name": fields.String,      # 昵称, 可以为空
                "desc": fields.String,              # 个人描述
                "created": fields.Integer           # 创建时间
            })
        })
    }

    @marshal_with(resource_fields)
    def get(self):
        """
        cms前台每次初始化的时候，会用get请求来从服务器检查登陆的信息以及最新的用户数据
        :return:
        """
        data = Data()
        if not g.login:
            return Response.params_error(message=g.message)
        # 如果请求带了token，返回最新的用户数据
        data.token = g.token
        data.user = self.generate_user(g.user)

        # 将uid与token缓存到数据库中
        res = g.cache.set_pointed(g.token, "uid", g.user.id)

        # 如果res < 0 说明缓存发生了错误
        if res < 0:
            return Response.server_error(message="缓存过程中发生错误")

        return Response.success(data=data)

    @marshal_with(resource_fields)
    def post(self):
        """
        负责处理每次的登陆请求
        :return:
        """
        form = LoginForm(request.form)
        data = Data()
        if not form.validate():
            return Response.params_error(message=form.get_error())
        # 如果表单格式正确
        username = form.username.data
        password = form.password.data
        remember = form.remember.data

        # 从数据库中搜索这个用户名
        user = CMSUser.query.filter_by(username=username).first()
        if user and user.validate(raw_password=password):
            # 如果用户存在且密码正确, 生成新的token，并将其缓存起来
            token = generate_token(user.id, permanent=remember)
            res = g.cache.set_pointed(token, "uid", user.id, permanent=remember)

            # 如果缓存错误
            if res < 0:
                return Response.server_error(message="数据缓存过程中发生错误")

            # 返回正常的数据
            data.token = token
            data.user = self.generate_user(user)        # data.user = user
            return Response.success(data=data)
        else:
            # 没有这个用户，或者密码错误
            return Response.source_error(message="密码错误或者用户不存在", data=data)

    @staticmethod
    def generate_user(user):
        # 用于返回一个格式化的user数据对象
        res = Data()
        res.role = user.role.name
        res.created = user.created.timestamp()
        res.display_name = user.display_name
        res.username = user.username
        res.desc = user.desc
        return res


class LogOutView(Resource):

    method_decorators = [login_required(CMSPermission.VISITOR)]

    # 用户注销的时候会请求这个接口，负责将其对应的token从缓存中删除
    def get(self):
        res = g.cache.delete(g.token)
        print(res)
        if res > 0:
            return success(data={})
        return server_error(message="缓存中不存在这个token")


class ProfileView(Resource):
    """
    修改用户昵称与用户描述接口
    """
    resource_fields = {
        "code": fields.Integer,                  # 状态码
        "message": fields.String,                # 状态描述
        "data": fields.Nested({
            "user": fields.Nested({              # 用户信息
                "role": fields.String,           # 角色
                "username": fields.String,       # 用户名
                "display_name": fields.String,   # 昵称, 可以为空
                "desc": fields.String,           # 个人描述
                "created": fields.Integer        # 创建时间
            })
        })
    }

    method_decorators = [login_required(CMSPermission.VISITOR)]

    @marshal_with(resource_fields)
    def post(self):
        form = ProfileForm(request.form)
        data = Data()
        if not form.validate():
            return Response.params_error(message=form.get_error())
            # 表单验证通过, 获取用户信息
        user = g.user
        display_name = form.displayName.data

        # 检查表单中的新姓名是否在数据库中有重复部分
        search_user = CMSUser.query.filter_by(display_name=display_name).first()
        if search_user:
            # 重复了
            return Response.deny_error(message="该昵称已存在")
        else:
            # 没有重复，则修改用户的姓名与描述，并且提交至数据库
            user.display_name = display_name
            user.desc = form.desc.data
            db.session.commit()

            # 返回一个user数据对象
            data.user = LoginView.generate_user(user)
            return Response.success(data=data)


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

    method_decorators = [login_required(CMSPermission.BOADER)]

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
        data = Data()

        # status的值用于筛选对应status值的boards，1为可见，0为不可见
        boards = Board.query.filter_by(status=status)
        # 用切片筛选结果
        res = boards[offset:offset+limit]

        # 优化后的sql count函数
        total = boards.with_entities(func.count(Board.id)).scalar()
        data.total = total
        data.boards = []
        for board in res:
            data.boards.append(self.generate_board(board))
        return Response.success(data=data)

    @marshal_with(resource_fields)
    def post(self):
        form = BoardForm(request.form)
        if not form.validate():
            return Response.params_error(message=form.get_error())
            # 表单验证通过，先获取表单的值
        name = form.name.data
        desc = form.desc.data
        avatar = form.avatar.data
        board_id = form.board_id.data
        status = form.status.data

        data = Data()

        if board_id:
            # 如果表单的board_id不为0，说明这是一个编辑的请求，并获取相应的board
            board = Board.query.filter_by(id=board_id).first()
            if not board:
                return Response.source_error(message="数据库中找不到该板块")

            # 存在该板块，设为对应编辑的值
            board.name = name
            board.desc = desc
            board.avatar = avatar
            board.status = status

            # 提交至数据库
            db.session.commit()

        else:
            # 如果表单的board_id为0，说明这是一个新建板块请求
            # 新建一个板块，并提交到数据库
            board = Board(name=name, desc=desc, avatar=avatar)
            db.session.add(board)
            db.session.commit()

        data.boards = [self.generate_board(board)]
        data.total = 1
        return Response.success(data=data)

    @staticmethod
    def generate_board(board):
        """
        返回一个格式化的board数据对象
        :param board:
        :return:
        """
        data = Data()
        data.name = board.name
        data.board_id = board.id
        data.desc = board.desc
        data.avatar = board.avatar
        data.created = board.created.timestamp()
        data.articles = len(board.articles.all())
        return data


class ImageView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "uptoken": fields.String
        })
    }

    method_decorators = [login_required(CMSPermission.VISITOR)]

    @marshal_with(resource_fields)
    def get(self):
        if not g.login:
            return Response.auth_error(message=g.message)

        data = Data()
        data.uptoken = generate_uptoken()
        return Response.success(data=data)


class TestView(Resource):

    method_decorators = [login_required(CMSPermission.VISITOR)]

    @marshal_with(LoginView.resource_fields)
    def get(self):
        user = g.user
        data = Data()
        data.token = request.headers.get("Z-Token")
        data.user = LoginView.generate_user(user)
        return Response.success(data=data)


api.add_resource(LoginView, "/login/", endpoint="login")
api.add_resource(LogOutView, "/logout/", endpoint="logout")
api.add_resource(ProfileView, "/api/profile/", endpoint="set_profile")
api.add_resource(BoardView, "/api/board/", endpoint="board")

api.add_resource(ImageView, "/api/image/", endpoint="backend_image")
api.add_resource(TestView, "/api/test/token/", endpoint="test")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_bp.before_request
def before_request():
    hook_before(token_validator, cache, no_token_msg="没有token值")
    # # 从header中获取token值，并且将缓存加入上下文变量g中
    # token = request.headers.get("Z-Token")
    # g.cache = cache
    # if token:
    #     # 如果有token，尝试从数据库中获取用户
    #     res, user = token_validator.validate(token)
    #     if res and user:
    #         # 获取用户成功的话，g.login置为真，将user与token也绑定到上下文变量g
    #         g.login = True
    #         g.user = user
    #         g.token = token
    #     else:
    #         # 获取失败，说明token的值有问题
    #         g.login = False
    #         g.message = user
    # else:
    #     # 没有token，直接将g.login置为假
    #     g.login = False
    #     g.message = "没有token值"
