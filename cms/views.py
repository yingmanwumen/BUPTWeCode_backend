from flask import Blueprint, request, g
from exts import db
from flask_restful import Resource, Api, fields, marshal_with
from sqlalchemy import func
from common.restful import *
from .models import CMSUser, Permission
from .forms import LoginForm, ProfileForm, BoardForm
from common.token import login_required, generate_token
from common.cache import MyRedis
from common.models import Board
from common.image_uploader import generate_uptoken
from common.hooks import hook_cms

cms_bp = Blueprint("cms", __name__, url_prefix="/cms")
api = Api(cms_bp)


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

    def get(self):
        """
        cms前台每次初始化的时候，会用get请求来从服务器检查登陆的信息以及最新的用户数据
        :return:
        """
        if not g.login:
            return token_error(message=g.message)

        # 将uid与token缓存到数据库中
        res = g.cache.set_pointed(g.token, "uid", g.user.id)

        # 如果res < 0 说明缓存发生了错误
        if res < 0:
            return server_error(message="缓存过程中发生错误")

        return self._generate_response(g.token, g.user)

    def post(self):
        """
        负责处理每次的登陆请求
        :return:
        """
        form = LoginForm(request.form)
        data = Data()
        if not form.validate():
            return params_error(message=form.get_error())
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
                return server_error(message="数据缓存过程中发生错误")

            # 返回正常的数据
            return self._generate_response(token, user)
        else:
            # 没有这个用户，或者密码错误
            return source_error(message="密码错误或者用户不存在", data=data)

    @marshal_with(resource_fields)
    def _generate_response(self, token, user):
        # 用于返回一个格式化的user数据对象
        resp = Data()
        resp.token = token
        resp.user = Data()

        resp.user.role = user.role.name
        resp.user.created = user.created.timestamp()
        resp.user.display_name = user.display_name
        resp.user.username = user.username
        resp.user.desc = user.desc

        return Response.success(data=resp)


class LogOutView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

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

    method_decorators = [login_required(Permission.VISITOR)]

    def post(self):
        form = ProfileForm(request.form)
        if not form.validate():
            return params_error(message=form.get_error())

        # 表单验证通过, 获取用户信息
        user = g.user
        display_name = form.displayName.data

        # 检查表单中的新姓名是否在数据库中有重复部分
        search_user = CMSUser.query.filter_by(display_name=display_name).first()
        if search_user:
            # 重复了
            return deny_error(message="该昵称已存在")

        # 没有重复，则修改用户的姓名与描述，并且提交至数据库
        user.display_name = display_name
        user.desc = form.desc.data
        db.session.commit()

        # 返回一个user数据对象
        return success()


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
        data = Data()

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

    @marshal_with(resource_fields)
    def _generate_response(self, boards, total):
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


class ImageView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "uptoken": fields.String
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    def get(self):
        if not g.login:
            return auth_error(message=g.message)

        return success(data=dict(uptoken=generate_uptoken()))


class TestView(Resource):

    method_decorators = [login_required(Permission.VISITOR)]

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
    hook_cms(no_user_msg="未登录", no_token_msg="没有token值")

