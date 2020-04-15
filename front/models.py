from exts import db, mail
from flask_mail import Message
from cms.models import Permission
from datetime import datetime
from sqlalchemy import func
import shortuuid
import json


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    status = db.Column(db.Integer, default=1)
    created = db.Column(db.DateTime, default=datetime.now)

    article_id = db.Column(db.String(50), db.ForeignKey("articles.id"))
    user_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))


class Rate(db.Model):
    __tablename__ = "rates"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    status = db.Column(db.Integer, default=1)
    created = db.Column(db.DateTime, default=datetime.now)

    comment_id = db.Column(db.String(50), db.ForeignKey("comments.id"))
    user_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))


class Follow(db.Model):
    __tablename__ = "follows"
    follower_id = db.Column(db.String(50), db.ForeignKey("front_user.id"), primary_key=True)
    followed_id = db.Column(db.String(50), db.ForeignKey("front_user.id"), primary_key=True)
    created = db.Column(db.DateTime, default=datetime.now)


class Notification(db.Model):
    """
    category类型
    1.文章获赞             0b0001 = 1
    2.评论获赞             0b0010 = 2
    3.文章获得评论          0b0100 = 4
    4.评论下获得楼中楼回复   0b1000 = 8
    """
    __tablename__ = "notifications"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    category = db.Column(db.Integer)
    sender_content = db.Column(db.Text)
    acceptor_content = db.Column(db.Text)
    link_id = db.Column(db.String(50))

    visited = db.Column(db.Integer, default=0)
    status = db.Column(db.Integer, default=1)
    created = db.Column(db.DateTime, default=datetime.now)

    sender_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))
    acceptor_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))

    sender = db.relationship("FrontUser", backref="broadcasts", foreign_keys=[sender_id])
    acceptor = db.relationship("FrontUser", backref="notifications", foreign_keys=[acceptor_id])


class Report(db.Model):
    """
    1.举报用户   0b0001 = 1
    2.举报帖子   0b0010 = 2
    3.举报评论   0b0100 = 4
    4.举报楼中楼  0b1000 = 8
    """
    __tablename__ = "reports"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    category = db.Column(db.String(50))
    reason = db.Column(db.Text)
    link_id = db.Column(db.String(50))

    user_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))


class FeedBack(db.Model):
    __tablename__ = "feedbacks"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=True)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)

    def send_mail(self, subject, recipients, body):
        """
        发送邮件
        """
        if not isinstance(recipients, list):
            recipients = list(recipients)
        message = Message(subject=subject, recipients=recipients, body=body)
        mail.send(message)


class FrontUser(db.Model):
    __tablename__ = "front_user"
    # __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    open_id = db.Column(db.String(50))
    union_id = db.Column(db.String(100))

    username = db.Column(db.String(20), default="未命名", nullable=False)
    signature = db.Column(db.String(100), default="你只需默认就好，无需多言我的好", nullable=False)
    gender = db.Column(db.Integer, default=0, nullable=False)
    avatar = db.Column(db.String(500))
    permission = db.Column(db.Integer, default=1)

    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    articles = db.relationship("Article", backref="author", lazy="dynamic")
    comments = db.relationship("Comment", backref="author", lazy="dynamic")
    likes = db.relationship("Like", backref="user", lazy="dynamic")
    rates = db.relationship("Rate", backref="user", lazy="dynamic")
    reports = db.relationship("Report", backref="user", lazy="dynamic")

    followed = db.relationship("Follow", foreign_keys=[Follow.follower_id], lazy="dynamic",
                               backref=db.backref("follower", lazy="joined"), cascade="all, delete-orphan")
    followers = db.relationship("Follow", foreign_keys=[Follow.followed_id], lazy="dynamic",
                                backref=db.backref("followed", lazy="joined"), cascade="all, delete-orphan")

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

    def get_all_appreciation(self, cache, attr):
        """
        从缓存中获取用户所有点的数据，如果缓存中获取不到，把数据库中的内容更新到缓存中
        如果是对文章操作，attr的值应该为likes
        如果是对评论操作，attr的值应该为rates
        """
        user_data = cache.get(self.id, json=True)
        if not user_data:
            user_data = self.set_all_appreciation(cache, attr)
        return user_data

    def set_all_appreciation(self, cache, attr):
        """
        用于将用户的点赞请求缓存到数据库中
        """
        user_data = {}
        foreign_key = "article_id" if attr == "likes" else "comment_id"
        with cache.redis.pipeline(transaction=False) as pipeline:
            for attr_item in getattr(self, attr).all():             # for item in self.likes.all()
                if attr_item.status:
                    foreign_id = getattr(attr_item, foreign_key)    # article_id = item.article_id
                    attr_value = {
                        "id": attr_item.id,                         # attr_value["id"] = item.id
                        "status": 1,
                        "created": attr_item.created.timestamp()
                    }
                    user_data[foreign_id] = attr_value              # user_data["article_id"] = item_value
                    attr_value = json.dumps(attr_value)             # json.loads
                    pipeline.hset(self.id, foreign_id, attr_value)  # hset(user_id, article_id, item_value)
            pipeline.expire(self.id, 3600)
            pipeline.execute()
        return user_data

    def set_one_appreciation(self, cache, sub_cache, attr, attr_id):
        """
        用于用户对单个文章/评论进行赞操作
        """
        # 首先去查询是否有用户的赞过的文章/评论的缓存,如果没有就把他添加到缓存中
        if not cache.exists(self.id):
            self.set_all_appreciation(cache, attr)

        # 从缓存中获取用户对某一文章/评论的点赞情况
        attr_value = cache.get_pointed(self.id, attr_id, json=True)[0]

        # 获取现在的时间
        cur_timestamp = int(datetime.now().timestamp())

        # 如果获取不到，说明这是一个新的点赞请求，用户以前没有对该文章/评论点过赞，于是新建一个赞
        if not attr_value:
            attr_value = {
                "id": shortuuid.uuid(),
                "status": 0,
            }

        # 将点赞情况中的status置为其反面, 并将其储存进缓存中
        attr_value["status"] = 1 - attr_value["status"]
        attr_value["created"] = cur_timestamp
        cache.set_pointed(self.id, attr_id, attr_value, json=True)

        # 更新子缓存数据
        amount = 1 if attr_value["status"] else -1
        sub_cache.hincrby(attr_id, attr, amount)

        # 状态变化过的点赞要记录在一个队列中，用于后期数据库统一更新点赞情况
        new_attr_value = {
            "id": attr_id,
            "user_id": self.id,
            "status": attr_value["status"],
            "created": cur_timestamp
        }
        cache.set_pointed(name="queue", key=attr_value["id"], value=new_attr_value, json=True)

    def follow(self, user):
        follow = self.followed.filter_by(followed_id=user.id).first()
        if not follow:
            follow = Follow(follower=self, followed=user)
            db.session.add(follow)

    def unfollow(self, user):
        follow = self.followed.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def set_new_notifications_count(self, cache):
        notifications = Notification.query.filter_by(acceptor_id=self.id, visited=0)
        count = notifications.with_entities(func.count(Notification.id)).scalar()
        res = dict(new=count)
        cache.set(self.id, res)
        return count

    def get_new_notifications_count(self, cache):
        if not cache.exists(self.id):
            return self.set_new_notifications_count(cache)
        return cache.get_pointed(self.id, "new")[0]

    def notification_increase(self, cache, amount=1):
        if not cache.exists(self.id):
            self.set_new_notifications_count(cache)
        else:
            cache.hincrby(self.id, "new", amount)
