from exts import db
from datetime import datetime
from flask import g
from sqlalchemy import func
from front.models import Like, Rate
from jieba.analyse.analyzer import ChineseAnalyzer
import shortuuid
import json
import math


article_tag_table = db.Table("article_tag_table",
                             db.Column("article_id", db.String(50), db.ForeignKey("articles.id"), primary_key=True),
                             db.Column("tag_id", db.String(50), db.ForeignKey("tags.id"), primary_key=True))


class Board(db.Model):
    __tablename__ = "boards"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    desc = db.Column(db.Text, nullable=False)
    avatar = db.Column(db.String(255))
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    articles = db.relationship("Article", backref="board", lazy="dynamic")


class Article(db.Model):
    __tablename__ = "articles"
    __searchable__ = ["title", "content"]
    __analyzer__ = ChineseAnalyzer()

    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    title = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text, default="")
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)
    quality = db.Column(db.Integer, default=0)
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
        如果被用户喜欢，返回True，否则返回False
        """
        if user_likes:
            value = user_likes.get(self.id)
            if not value:
                return False
            if isinstance(value, str):
                value = json.loads(value)
            return value["status"] == 1
        like = self.likes.filter_by(user_id=g.user.id).first()
        return like is not None

    def set_property_cache(self, cache):
        views = self.views
        likes = self.likes.filter_by(status=1).with_entities(func.count(Like.id)).scalar()
        comments = self.comments.filter_by(status=1).with_entities(func.count(Comment.id)).scalar()
        res = dict(likes=likes, comments=comments, views=views)
        cache.set(self.id, res)
        return res

    def get_property_cache(self, cache):
        pro = cache.get(self.id)
        if not pro:
            pro = self.set_property_cache(cache)
        return pro

    def cache_increase(self, cache, field, amount=1):
        if not cache.exists(self.id):
            self.set_property_cache(cache)
        cache.hincrby(self.id, field, amount)
        if field == "views":
            cache.hincrby("views", self.id)

    def calculate_score(self, date):
        """
        计算文章的score
        :param date:
        :return:
        """
        td = date - self.created
        epoch_hours = td.days * 24 + td.seconds / 3600 + 1     # 文章发布的小时数
        views = self.views
        comments = self.comments.filter_by(status=1).with_entities(func.count(Comment.id)).scalar()
        likes = self.likes.filter_by(status=1).with_entities(func.count(Like.id)).scalar()
        numerator = math.log(views + 1, math.e) * 4 + comments * likes / 5
        return round((numerator / epoch_hours) * 100, 7)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.String(50), primary_key=True, default=shortuuid.uuid)
    content = db.Column(db.Text)
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
        """
        if user_rates:
            value = user_rates.get(self.id)
            if not value:
                return False
            if isinstance(value, str):
                value = json.loads(value)
            return value["status"] == 1
        rate = self.rates.filter_by(user_id=g.user.id).first()
        return rate is not None

    def set_property_cache(self, cache):
        rates = self.rates.filter_by(status=1).with_entities(func.count(Rate.id)).scalar()
        sub_comments = self.sub_comments.filter_by(status=1).with_entities(func.count(SubComment.id)).scalar()
        res = dict(rates=rates, sub_comments=sub_comments)
        cache.set(self.id, res)
        return res

    def get_property_cache(self, cache):
        pro = cache.get(self.id)
        if not pro:
            pro = self.set_property_cache(cache)
        return pro

    def cache_increase(self, cache, field, amount=1):
        if not cache.exists(self.id):
            self.set_property_cache(cache)
        cache.hincrby(self.id, field, amount)


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
        for tag_content in set(raw_tags):
            print(tag_content)
            tag = Tag.query.filter_by(content=tag_content).first()
            if not tag:
                tag = Tag(content=tag_content)
                db.session.add(tag)
            res.append(tag)
        return res
