from flask import Flask
from flask_cors import CORS

from exts import db

from cms import cms_bp
from front.views import wx_bp, common_bp, article_bp
import config

app = Flask(__name__)
app.config.from_object(config)
CORS(app, supports_credentials=True)

app.register_blueprint(cms_bp)
app.register_blueprint(wx_bp)
app.register_blueprint(common_bp)
app.register_blueprint(article_bp)

db.init_app(app)


@app.route("/")
def index():
    return "success"


if __name__ == '__main__':
    # app.run(host="0.0.0.0")

    def test():
        with app.app_context():
            from common.models import Article, Comment, SubComment
            from front.models import FrontUser
            from common.token import Permission

            article_user = FrontUser.query.get("4GGG2xk5PQowVA6gXucowB")
            user = FrontUser.query.get("VPmfQdH4otRpWe8zfCmSbk")
            article = Article.query.get("aaa")
            comment = Comment.query.get("tdsBnYHz7P9SpZ5Mwavc3T")
            sub_comment_article = SubComment.query.get("kNfa9d3YxjYWDx3yz7SWqM")
            sub_comment_user = SubComment.query.get("bbb")
            print(user.has_permission(Permission.COMMENTER, sub_comment_article))

    test()
