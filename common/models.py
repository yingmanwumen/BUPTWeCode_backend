from exts import db
from datetime import datetime
from flask import g
import shortuuid


article_tag_table = db.Table("article_tag_table",
                             db.Column("article_id", db.String(50), db.ForeignKey("articles.id"), primary_key=True),
                             db.Column("tag_id", db.String(50), db.ForeignKey("tags.id"), primary_key=True))


class Board(db.Model):
    __tablename__ = 'boards'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    desc = db.Column(db.Text, nullable=False)
    avatar = db.Column(db.String(255))
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    articles = db.relationship("Article", backref="board", lazy="dynamic")


class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    title = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text, default="")
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)
    views = db.Column(db.Integer, default=0)

    board_id = db.Column(db.Integer, db.ForeignKey("boards.id"))
    author_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))

    comments = db.relationship("Comment", backref="article", lazy="dynamic")
    likes = db.relationship("Like", backref="article", lazy="dynamic")
    tags = db.relationship("Tag", secondary=article_tag_table, backref=db.backref("articles"))

    def add_tags(self, *tags):
        for tag in tags:
            self.tags.append(tag)

    def is_liked(self, user_likes=None):
        """
        如果被用户喜欢，返回True和like的id，否则返回False和空值
        :param user_likes:
        :return:
        """
        like_id = None
        if user_likes:
            like_id = user_likes.get(self.id)
        else:
            like = self.likes.filter_by(user_id=g.user.id).first()
            if like:
                like_id = like.id
        liked = True if like_id else False
        return liked, like_id


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    author_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))
    article_id = db.Column(db.String(50), db.ForeignKey("articles.id"))

    sub_comments = db.relationship("SubComment", backref="comment", lazy="dynamic")
    rates = db.relationship("Rate", backref="comment", lazy="dynamic")

    def is_rated(self, user_rates=None):
        """
        如果被用户点赞了，返回True和rate_id，否则返回False和None
        :param user_rates:
        :return:
        """
        rate_id = None
        if user_rates:
            rate_id = user_rates.get(self.id)
        else:
            rate = self.rates.filter_by(user_id=g.user.id).first()
            if rate:
                rate_id = rate.id
        rated = True if rate_id else False
        return rated, rate_id


class SubComment(db.Model):
    __tablename__ = "sub_comments"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    content = db.Column(db.Text, nullable=False)
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    comment_id = db.Column(db.String(50), db.ForeignKey("comments.id"))
    author_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))
    acceptor_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))

    author = db.relationship("FrontUser", backref="sub_comments", foreign_keys=[author_id])
    acceptor = db.relationship("FrontUser", backref="sub_comments_accepted", foreign_keys=[acceptor_id])


class FeedBack(db.Model):
    __tablename__ = "feedbacks"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50), nullable=True)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text)


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    content = db.Column(db.String(20), nullable=False, index=True)
    created = db.Column(db.DateTime, default=datetime.now)

    def marshal(self, data_class):
        data = data_class()
        data.tag_id = self.id
        data.content = self.content
        return data

    @staticmethod
    def add_article(article, *tags):
        for tag in tags:
            article.tags.append(tag)

    @staticmethod
    def query_tags(*raw_tags):
        res = []
        for raw_tag in raw_tags:
            tag_content = raw_tag.get("content")
            tag = Tag.query.filter_by(content=tag_content).first()
            if not tag:
                tag = Tag(content=tag_content)
                db.session.add(tag)
            res.append(tag)
        return res
