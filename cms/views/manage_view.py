from flask import Blueprint, request, g
from exts import db
from flask_restful import Resource, Api, fields, marshal_with
from sqlalchemy import func
from common.restful import *
from ..forms import BoardForm
from common.token import login_required, Permission
from common.models import Board
from common.hooks import hook_cms
from front.models import FrontUser

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

    @marshal_with(resource_fields)
    def generate_response(self, total, users):
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


api.add_resource(BoardView, "/board/", endpoint="board")
api.add_resource(OperatorView, "/operator/", endpoint="cms_manage_operate")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_manager_bp.before_request
def before_request():
    hook_cms()

