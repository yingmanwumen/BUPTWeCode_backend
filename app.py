from flask import Flask
from flask_cors import CORS

from exts import db, mail

from cms import cms_bp
from front.views import BPS
import config
import wtforms_json

app = Flask(__name__)
app.config.from_object(config)
CORS(app, supports_credentials=True)

for blueprint in BPS:
    app.register_blueprint(blueprint)
app.register_blueprint(cms_bp)


db.init_app(app)
mail.init_app(app)
wtforms_json.init()


@app.route("/")
def index():
    return "success"


if __name__ == '__main__':
    # 测试分支，不稳定，有bug请联系我
    app.run(host="0.0.0.0")
