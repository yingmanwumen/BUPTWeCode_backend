from flask import Blueprint, request, g
from exts import db
from flask_restful import Resource, Api, fields, marshal_with
from sqlalchemy import func
from common.restful import *
from ..forms import FeedbackForm
from common.token import login_required, Permission
from common.models import Board, Article
from common.hooks import hook_cms
from common.cache import article_cache
from front.models import FrontUser, FeedBack, Report

cms_block_bp = Blueprint("cms_block", __name__, url_prefix="/cms/block")
api = Api(cms_block_bp)


class ReportView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "reports": fields.List(fields.Nested({
                "report_id": fields.String,
                "category": fields.String,
                "link_id": fields.String,
                "created": fields.Integer,
                "status": fields.Integer,
                "reason": fields.String,
                "reporter": fields.Nested({
                    "uid": fields.String,
                    "username": fields.String,
                    "avatar": fields.String,
                    "gender": fields.Integer
                })
            })),
            "total": fields.Integer
        })
    }

    method_decorators = [login_required(Permission.FRONTUSER)]

    category_mapping = {
        1: "user",
        2: "article",
        4: "comment",
        8: "sub_comment"
    }

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        reports = Report.query
        total = reports.with_entities(func.count(Report.id)).scalar()
        reports = reports.order_by(Report.status.desc(), Report.created.desc())[offset:offset + limit]
        return self.generate_response(total, reports)

    def post(self):
        report_id = request.form.get("report_id")
        if not report_id:
            return params_error(message="缺失举报id")
        report = Report.query.get(report_id)
        if not report:
            return source_error(message="举报不存在")
        report.status = 0
        db.session.commit()
        return success()

    @staticmethod
    @marshal_with(resource_fields)
    def generate_response(total, reports):
        resp = Data()
        resp.total = total
        resp.reports = []
        for report in reports:
            data = Data()
            data.report_id = report.id
            data.reason = report.reason
            data.created = report.created.timestamp()
            data.category = ReportView.category_mapping[report.category]
            data.status = report.status
            data.link_id = report.link_id
            data.reporter = Data()
            data.reporter.username = report.user.username
            data.reporter.avatar = report.user.avatar
            data.reporter.uid = report.user_id
            data.reporter.gender = report.user.gender
            resp.reports.append(data)
        return Response.success(data=resp)


class FeedbackView(Resource):
    resource_fields = {
        "code": fields.Integer,
        "message": fields.String,
        "data": fields.Nested({
            "feedbacks": fields.List(fields.Nested({
                "feedback_id": fields.String,
                "category": fields.String,
                "content": fields.String,
                "email": fields.String,
                "status": fields.Integer,
                "images": fields.List(fields.String),
                "user": fields.Nested({
                    "user_id": fields.String,
                    "username": fields.String,
                    "avatar": fields.String,
                    "gender": fields.Integer
                })
            })),
            "total": fields.Integer
        })
    }

    method_decorators = [login_required(Permission.FRONTUSER)]

    feedback_mapping = {
        "useFeedback": "功能异常",
        "adviceFeedback": "产品建议",
        "accountFeedback": "账号异常"
    }

    def get(self):
        offset = request.args.get("offset", 0, type=int)
        limit = request.args.get("limit", 10, type=int)
        feedbacks = FeedBack.query
        total = feedbacks.with_entities(func.count(FeedBack.id)).scalar()
        feedbacks = feedbacks.order_by(FeedBack.status.desc(), FeedBack.created.desc())[offset:offset+limit]
        return self.generate_response(total, feedbacks)

    def post(self):
        form = FeedbackForm(request.form)
        if not form.validate():
            return params_error(message=form.get_error())

        feedback = FeedBack.query.get(form.feedback_id.data)
        if not feedback:
            return source_error(message="反馈不存在")
        feedback.send_mail(body=form.content.data)
        feedback.status = 0
        db.session.commit()
        return success()

    @staticmethod
    @marshal_with(resource_fields)
    def generate_response(total, feedbacks):
        resp = Data()
        resp.total = total
        resp.feedbacks = []
        for feedback in feedbacks:
            data = Data()
            data.feedback_id = feedback.id
            data.created = feedback.created.timestamp()
            data.content = feedback.content
            data.email = feedback.email
            data.category = FeedbackView.feedback_mapping[feedback.category]
            data.status = feedback.status
            data.images = feedback.images.split(",") if feedback.images else []
            data.user = Data()
            data.user.user_id = feedback.user.id
            data.user.username = feedback.user.username
            data.user.gender = feedback.user.gender
            data.user.avatar = feedback.user.avatar
            resp.feedbacks.append(data)
        return Response.success(data=resp)


api.add_resource(ReportView, "/report/", endpoint="cms_block_report")
api.add_resource(FeedbackView, "/feedback/", endpoint="cms_block_feedback")


# hooks 用来在上下文中储存cms_user信息，防止重复写token认证语句
@cms_block_bp.before_request
def before_request():
    hook_cms()
