from flask_script import Manager
from app import app
from exts import db
from flask_migrate import Migrate, MigrateCommand
from cms.models import CMSUser
from common.exceptions import DIYException


manager = Manager(app)
Migrate(app, db)
manager.add_command("db", MigrateCommand)
role_mapping = dict(visitor=1, operator=15, admin=63, developer=255)


@manager.option('-u', '--username', dest='username')
@manager.option('-p', '--password', dest='password')
@manager.option('-r', '--role_name', dest="role_name")
def add_cms_user(username, password, role_name):
    """
    添加一个新的cms用户，用户的默认权限为<访问者>
    :param username:用户名
    :param password:密码
    :param role_name:权限角色
    :return:
    """
    try:
        user = CMSUser.query.filter_by(username=username).first()
        if not user:
            role_name = role_name or "visitor"
            permission = role_mapping.get(role_name)
            if not permission:
                print("不存在的角色名称")
            else:
                user = CMSUser(username=username, password=password)
                user.permission = permission
                db.session.add(user)
                db.session.commit()
                print("用户添加成功")
        else:
            raise DIYException("cms用户添加失败...用户已经存在...")
    except DIYException as e:
        print(e.message)
    except Exception as e:
        print(e)
        print("cms用户添加失败...请稍后重试...")


@manager.option('-u', '--username', dest='username')
@manager.option('-p', '--password', dest='password')
def check_cms_user(username, password):
    """
    用于校验可用的cms用户与正确的密码
    :param username: 用户名
    :param password: 密码
    :return:
    """
    try:
        user = CMSUser.query.filter_by(username=username).first()
        if user and user.validate(password):
            print('cms用户验证成功...!')
        else:
            print('cms用户验证失败...密码错误或者用户不存在')
    except Exception as e:
        print(e)
        print('cms用户验证过程中产生错误，验证失败...')


if __name__ == '__main__':
    manager.run()
