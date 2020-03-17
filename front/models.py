from exts import db
from cms.models import Permission
from datetime import datetime
import shortuuid


class FrontUser(db.Model):
    __tablename__ = "front_user"
    # __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    open_id = db.Column(db.String(50))
    union_id = db.Column(db.String(100))

    username = db.Column(db.String(20), default="未命名", nullable=False)
    signature = db.Column(db.String(100), default="你只需默认就好，无需多言我的好", nullable=False)
    gender = db.Column(db.Integer, default=0, nullable=False)
    avatar_url = db.Column(db.String(500))
    permission = db.Column(db.Integer, default=1)

    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    articles = db.relationship("Article", backref="author", lazy="dynamic")
    comments = db.relationship("Comment", backref="author", lazy="dynamic")

    def has_permission(self, permission, model=None):
        # 通常来说，前端用户仅需要判断是否拥有三个权限，VISITOR,COMMENTER,POSTER
        # 这三个权限为传入的permission可能值
        # 后面两个分别对于，是否有权限操作评论，帖子，
        # 对于帖子楼主来说，或者是层主来说，他们需要管理当前文章的回复/楼中楼
        # 这种情况下需要用到后面两个权限，要进行额外判断，判断必须传入需要操作的帖子orm模型，或者是评论orm模型

        # 一般如果只是需要用户登陆就能调用的接口，是不会传入一个orm模型的
        # 如果一个用户不是普通角色而是运营角色，也不需要进行额外判断了
        if not model or self.permission != Permission.VISITOR:
            return self.permission & permission == permission

        # 删帖的话，必须要是用户是楼主才可以
        if permission == Permission.POSTER and model.author.id == self.id:
            return True

        # 删除评论的话，楼主可以删除所有评论（包括楼中楼），层主可以删除楼中楼评论，一般人只能删除自己的评论
        elif permission == Permission.COMMENTER:
            # 删除一个楼中楼
            if model.__tablename__ == "sub_comments":
                # 分别是：楼中楼作者，评论作者，和文章作者可以删除
                if self.id in (model.author_id, model.comment.author_id, model.comment.article.author_id):
                    return True
                return False

            # 删掉一个评论
            elif model.__tablename__ == "comments":
                # 分别是：评论作者，和文章作者
                if self.id in (model.author_id, model.article.author_id):
                    return True
                return False
        return False
