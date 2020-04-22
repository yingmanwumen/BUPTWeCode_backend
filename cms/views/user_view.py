from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from exts import db
from common.restful import *
from common.token import login_required, Permission, generate_token
from common.hooks import hook_cms
from ..models import CMSUser
from ..forms import LoginForm, ProfileForm

cms_user_bp = Blueprint("cms_user", __name__, url_prefix="/cms/user")
api = Api(cms_user_bp)


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
                "role": fields.String,              # 角色权限
                "username": fields.String,          # 用户名
                "display_name": fields.String,      # 昵称, 可以为空
                "desc": fields.String,              # 个人描述
                "created": fields.Integer           # 创建时间
            })
        })
    }

    role_mapping = {
        Permission.VISITOR: "VISITOR",
        Permission.OPERATOR: "OPERATOR",
        Permission.ADMIN: "ADMIN",
        Permission.ALL_PERMISSION: "DEVELOPER"
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

        resp.user.role = self.role_mapping[user.permission]
        resp.user.created = user.created.timestamp()
        resp.user.display_name = user.display_name
        resp.user.username = user.username
        resp.user.desc = user.desc

        return Response.success(data=resp)


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
        display_name = form.display_name.data

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


api.add_resource(LoginView, "/login/", endpoint="cms_user_login")
api.add_resource(ProfileView, "/profile/", endpoint="cms_user_profile")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_user_bp.before_request
def before_request():
    hook_cms()
