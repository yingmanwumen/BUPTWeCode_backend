from exts import db
from datetime import datetime
import shortuuid


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
    images = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)

    board_id = db.Column(db.Integer, db.ForeignKey("boards.id"))
    author_id = db.Column(db.String(50), db.ForeignKey("front_user.id"))

    comments = db.relationship("Comment", backref="article", lazy="dynamic")


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
