from flask import Blueprint, request, g
from flask_restful import Resource, Api, fields, marshal_with
from sqlalchemy import func
from common.models import Board
from common.token import login_required, Permission
from common.restful import Response, Data
from common.hooks import hook_front

board_bp = Blueprint("board", __name__, url_prefix="/api/board")
api = Api(board_bp)


class BoardView(Resource):
    """
    和板块视图相关的类视图
    get请求可处理的业务: 获取boards数据
    """
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "boards": fields.List(fields.Nested({
                "board_id": fields.Integer,     # 板块唯一标识
                "name": fields.String,          # 板块名称
                "desc": fields.String,          # 板块描述
                "avatar": fields.String,        # 板块头像
            })),
            "total": fields.Integer             # 板块总数
        })
    }

    method_decorators = [login_required(Permission.VISITOR)]

    @marshal_with(resource_fields)
    def get(self):
        """
        负责返回板块的查询
        :return:
        """
        data = Data()

        # status的值用于筛选对应status值的boards，1为可见，0为不可见
        boards = Board.query.filter_by(status=1)
        # 用切片筛选结果
        res = boards.all()

        # 优化后的sql count函数
        total = boards.with_entities(func.count(Board.id)).scalar()
        data.total = total
        data.boards = []
        for board in res:
            data.boards.append(self.generate_board(board))
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
        return data


api.add_resource(BoardView, '/', endpoint="front_board")


@board_bp.before_request
def before_request():
    hook_front(no_user_msg="登陆状态已过期", no_token_msg="未授权")