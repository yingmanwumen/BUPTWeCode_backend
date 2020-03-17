from flask_script import Manager
from app import app
from exts import db
from flask_migrate import Migrate, MigrateCommand
import cms.models as cms_models
from common.exceptions import DIYException


manager = Manager(app)
Migrate(app, db)
manager.add_command("db", MigrateCommand)


@manager.option('-u', '--username', dest='username')
@manager.option('-p', '--password', dest='password')
@manager.option('-r', '--rolename', dest="rolename")
def add_cms_user(username, password, rolename):
    """
    添加一个新的cms用户，用户的默认权限为<访问者>
    :param username:用户名
    :param password:密码
    :param rolename:权限角色
    :return:
    """
    try:
        user = cms_models.CMSUser.query.filter_by(username=username).first()
        if not user:
            user = cms_models.CMSUser(username=username, password=password)
            rolename = rolename or "VISITOR"
            role = cms_models.Role.query.filter_by(name=rolename).first()
            if role:
                user.role = role
                db.session.add(user)
                db.session.commit()
                print("cms用户添加成功! 用户名为:{} 密码为:{}".format(username, password))
            else:
                raise DIYException("cms用户添加失败...角色表中没有这个用户")
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
        user = cms_models.CMSUser.query.filter_by(username=username).first()
        if user and user.validate(password):
            print('cms用户验证成功...!')
        else:
            print('cms用户验证失败...密码错误或者用户不存在')
    except Exception as e:
        print(e)
        print('cms用户验证过程中产生错误，验证失败...')


@manager.command
def init_role():
    """
    初始化角色信息与角色权限
    :return:
    """
    try:
        # 1.访问者，可以修改个人信息
        visitor = cms_models.Role(name="VISITOR", display_name="访问者", desc="仅支持数据的访问。")
        visitor.permission = cms_models.Permission.VISITOR

        # 2.运营角色，可以管理帖子，评论与前台用户
        operator = cms_models.Role(name="OPERATOR", display_name="运营", desc="管理帖子，评论，以及前台用户。")
        operator.permission = cms_models.Permission.OPERATOR

        # 3.管理员, 可以管理板块与运营
        admin = cms_models.Role(name="ADMIN", display_name="管理员", desc="你现在可以为所欲为了")
        admin.permission = cms_models.Permission.ADMIN

        # 4.开发者
        developer = cms_models.Role(name="DEVELOPER", display_name="开发者", desc="开发人员专属角色")
        developer.permission = cms_models.Permission.ALL_PERMISSION

        db.session.add_all([visitor, operator, admin, developer])
        db.session.commit()
        print("初始化用户角色成功...")
    except Exception as e:
        print(e)
        print("初始化过程中发生错误，请稍后重试...")


@manager.option("-u", "--username", dest="username")
@manager.option("-r", "--rolename", dest="rolename")
def change_user_role(username, rolename):
    try:
        user = cms_models.CMSUser.query.filter_by(username=username).first()
        if user:
            if rolename == user.role.name:
                print("用户<{}>已经拥有<{}>的角色身份了..".format(username, rolename))
            else:
                role = cms_models.Role.query.filter_by(name=rolename).first()
                if role:
                    user.role = role
                    db.session.commit()
                    print("用户<{}>添加<{}>角色成功...".format(username, rolename))
                else:
                    print("角色表中没有<{}>这个角色".format(role))
        else:
            print("用户<{}>不存在".format(username))
    except Exception as e:
        print(e)
        print("运行过程中发生错误，请稍后再试...")


@manager.option("-u", "--username", dest="username")
def test_permission(username):
    """
    返回指定用户的权限
    :param username: 用户名
    :return:
    """
    try:
        user = cms_models.CMSUser.query.filter_by(username=username).first()
        print(user.role.name)
    except Exception as e:
        print(e)
        print("运行过程中发生错误，请稍后再试...")


if __name__ == '__main__':
    manager.run()
