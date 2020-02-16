from flask import Blueprint, request, g
from exts import db
from flask_restful import Resource, Api, fields, marshal_with
from common.restful import Response, Data, success, server_error
from .models import CMSUser, CMSPermission
from .forms import LoginForm, ProfileForm, BoardForm
from common.token import login_required, generate_token, TokenValidator
from common.cache import MyRedis
from common.models import Board

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
        if g.login:
            # 如果请求带了token，返回最新的用户数据
            data.token = g.token
            data.user = self.generate_user(g.user)

            # 将uid与token缓存到数据库中
            res = g.cache.set_pointed(g.token, "uid", g.user.id)

            # 如果res < 0 说明缓存发生了错误
            if res < 0:
                return Response.server_error(message="缓存过程中发生错误")

            return Response.success(data=data)
        else:
            # 如果没有带token，返回token重定向响应
            return Response.token_error(message=g.message)

    @marshal_with(resource_fields)
    def post(self):
        """
        负责处理每次的登陆请求
        :return:
        """
        form = LoginForm(request.form)
        data = Data()
        if form.validate():
            # 如果表单格式正确
            username = form.username.data
            password = form.password.data
            remember = form.remember.data
            print(remember)

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
                data.user = self.generate_user(user)
                return Response.success(data=data)
            else:
                # 没有这个用户，或者密码错误
                return Response.source_error(message="密码错误或者用户不存在", data=data)
        else:
            return Response.params_error(message=form.get_error(), data=data)

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
        if form.validate():
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
        else:
            return Response.params_error(message=form.get_error(), data=data)


class BoardView(Resource):
    """
    和板块视图相关的类视图
    get请求可处理的业务: 获取boards数据，删除指定board
    post请求可处理的业务: 新增board, 修改已有board
    """
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.List(fields.Nested({
            "board_id": fields.Integer,     # 板块唯一标识
            "name": fields.String,          # 板块名称
            "desc": fields.String,          # 板块描述
            "created": fields.Integer,      # 板块创建时间
            "avatar_url": fields.String,    # 板块头像
            "articles": fields.Integer      # 板块下所含文章数量
        }))
    }

    method_decorators = [login_required(CMSPermission.BOADER)]

    @marshal_with(resource_fields)
    def get(self):
        data = []

        # 先判断是否是删除视图的业务
        delete_id = self.parse_args(request.args.get("delete", False))
        if delete_id:
            # 进入删除视图业务，获取对应删除板块
            board = Board.query.filter_by(id=delete_id).first()
            if board:
                # 如果获取板块成功，设置板块的状态为0，表示不可见
                board.status = 0
                db.session.commit()
                data.append(self.generate_board(board))
                return Response.success(data=data)
            else:
                # 获取板块失败
                return Response.server_error(message="数据库中找不到该板块")

        # 如果不是删除视图的业务，获取status的值，即使get请求不含status，给status一个默认值1
        status = self.parse_args(request.args.get("status", False)) or 1

        # status的值用于筛选对应status值的boards，1为可见，0为不可见
        boards = Board.query.filter_by(status=status).all()
        for board in boards:
            data.append(self.generate_board(board))
        return Response.success(data=data)

    @marshal_with(resource_fields)
    def post(self):
        form = BoardForm(request.form)
        if form.validate():
            # 表单验证通过，先获取表单的值
            name = form.name.data
            desc = form.desc.data
            avatar_url = form.avatar_url.data
            board_id = form.board_id.data

            if board_id:
                # 如果表单的board_id不为0，说明这是一个编辑的请求，并获取相应的board
                board = Board.query.filter_by(id=board_id).first()
                if board:
                    # 存在该板块，设为对应编辑的值
                    board.name = name
                    board.desc = desc
                    board.avatar_url = avatar_url

                    # 提交至数据库，并返回编辑后的新值
                    db.session.commit()
                    data = [self.generate_board(board)]
                    return Response.success(data=data)
                else:
                    # 不存在该板块，返回错误
                    return Response.server_error(message="数据库中找不到该板块")
            else:
                # 如果表单的board_id为0，说明这是一个新建板块请求
                # 新建一个板块，并提交到数据库
                board = Board(name=name, desc=desc, avatar_url=avatar_url)
                db.session.add(board)
                db.session.commit()

                # 返回新建的板块的值
                data = [self.generate_board(board)]
                return Response.success(data=data)
        else:
            # 表单验证失败，返回参数错误
            return Response.params_error(message=form.get_error())

    def parse_args(self, arg):
        # 将传入的参数转化为int类型，如果不能，就返回false
        if arg and arg.isnumeric():
            return int(arg)
        return False

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
        data.avatar_url = board.avatar_url
        data.created = board.created.timestamp()
        data.articles = 0
        return data


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

api.add_resource(TestView, "/api/test/token/", endpoint="test")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_bp.before_request
def before_request():
    # 从header中获取token值，并且将缓存加入上下文变量g中
    token = request.headers.get("Z-Token")
    g.cache = cache
    if token:
        # 如果有token，尝试从数据库中获取用户
        res, user = token_validator.validate(token)
        if res and user:
            # 获取用户成功的话，g.login置为真，将user与token也绑定到上下文变量g
            g.login = True
            g.user = user
            g.token = token
        else:
            # 获取失败，说明token的值有问题
            g.login = False
            g.message = user
    else:
        # 没有token，直接将g.login置为假
        g.login = False
        g.message = "没有token值"
