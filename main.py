from flask import Flask, request, render_template, redirect, url_for, flash, session, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_,or_
import time
import os

app = Flask(__name__)

limiter = Limiter(
    app,
    key_func=get_remote_address,   #根据访问者的IP记录访问次数
    default_limits=["200 per day", "50 per hour"]  #默认限制，一天最多访问200次，一小时最多访问50次
)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'     #内存数据库
# app.config['SQLALCHEMY_DATABASE_URI'] = 'r"sqlite:///C:\path\to\foo.db"'    #绝对路径
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'     #相对路径

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
#app.secret_key = '\xc9ixnRb\xe40\xd4\xa5\x7f\x03\xd0y6\x01\x1f\x96\xeao+\x8a\x9f\xe4'
app.secret_key = os.urandom(24)
db = SQLAlchemy(app)


############################################
# 数据库
############################################

# 定义ORM
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    password = db.Column(db.String(80))
    email = db.Column(db.String(120))
    create_time = db.Column(db.String(80))
    del_time = db.Column(db.String(80))
    isdel = db.Column(db.Boolean)

    def __repr__(self):
        return '<User %r>' % self.username

class PWD(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pwdname = db.Column(db.String(80))
    account = db.Column(db.String(80))
    pwd = db.Column(db.String(80))
    other = db.Column(db.Text(300))
    father = db.Column(db.Integer)
    create_time = db.Column(db.String(80))
    del_time = db.Column(db.String(80))
    isdel = db.Column(db.Boolean)

    def __repr__(self):
        return '<Password %r>' % self.pwdname

# 创建表格、插入数据
@app.before_first_request
def create_db():
    db.drop_all()  # 每次运行，先删除再创建
    db.create_all()

    admin = User(username='admin', password='root', email='admin@example.com', isdel=0)
    db.session.add(admin)

    guestes = [User(username='guest1', password='guest1', email='guest1@example.com', isdel=0),
               User(username='guest2', password='guest2', email='guest2@example.com', isdel=0),
               User(username='guest3', password='guest3', email='guest3@example.com', isdel=0),
               User(username='guest4', password='guest4', email='guest4@example.com', isdel=0)]
    db.session.add_all(guestes)

    pwds = [PWD(pwdname='pwdd1',account='tom1',pwd='pwd1',other='备注1',father=1,isdel=0),
           PWD(pwdname='pwdd1', account='tom2', pwd='pwd2', other='备注2', father=2, isdel=0),
           PWD(pwdname='pwdd2', account='tom3', pwd='pwd1', other='备注3', father=1, isdel=0),
           PWD(pwdname='pwdd2', account='tom4', pwd='pwd2', other='备注4', father=4, isdel=0),
           PWD(pwdname='pwdd2', account='tom5', pwd='pwd3', other='备注5', father=1, isdel=0)
    ]
    db.session.add_all(pwds)
    db.session.commit()


############################################
# 辅助函数、装饰器
############################################

# 登录检验（用户名、密码验证）
def valid_login(username, password):
    user = User.query.filter(and_(User.username == username, User.password == password, User.isdel == 0)).first()
    if user:
        return True
    else:
        return False


# 注册检验（用户名、邮箱验证）
def valid_regist(username, email):
    user = User.query.filter(or_(and_(User.username == username,User.isdel==0), and_(User.email == email,User.isdel==0))).first()
    if user:
        return False
    else:
        return True


# 登录
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # if g.user:
        if session.get('username'):
            return func(*args, **kwargs)
        else:
            return redirect(url_for('login', next=request.url))  #

    return wrapper


############################################
# 路由
############################################

# 1.主页
@app.route('/')
@limiter.exempt                               # 取消默认限制器
def home():
    return render_template('home.html', username=session.get('username'))


# 2.登录
@app.route('/login', methods=['GET', 'POST'])
# 自定义限制器覆盖了默认限制器
@limiter.limit("100/day;60/hour;10/minute")
def login():
    error = None
    if request.method == 'POST':
        if valid_login(request.form['username'], request.form['password']):
            flash("成功登录！")
            session['username'] = request.form.get('username')
            return redirect(url_for('home'))
        else:
            error = '错误的用户名或密码！'

    return render_template('login.html', error=error)


# 3.注销
@app.route('/logout')
# 自定义限制器覆盖了默认限制器
#@limiter.limit("100/day;10/hour;3/minute")
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


# 4.注册
@app.route('/regist', methods=['GET', 'POST'])
# 自定义限制器覆盖了默认限制器
#@limiter.limit("100/day;10/hour;3/minute")
def regist():
    error = None
    if request.method == 'POST':
        if request.form['password1'] != request.form['password2']:
            error = '两次密码不相同！'
        elif valid_regist(request.form['username'], request.form['email']):
            user = User(username=request.form['username'], password=request.form['password1'],
                        email=request.form['email'],create_time=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),isdel=0)
            db.session.add(user)
            db.session.commit()

            flash("成功注册！")
            return redirect(url_for('login'))
        else:
            error = '该用户名或邮箱已被注册！'

    return render_template('regist.html', error=error)


# 5.个人中心
@app.route('/panel')
@login_required
# 自定义限制器覆盖了默认限制器
#@limiter.limit("100/day;10/hour;3/minute")
def panel():
    username = session.get('username')
    user = User.query.filter(and_(User.username == username,User.isdel==0)).first()
    pwds = PWD.query.filter(and_(PWD.father == user.id,PWD.isdel == 0)).all()
    return render_template("panel.html", user=user,pwds=pwds)


#添加密码
@app.route('/addpwd', methods=['GET', 'POST'])
@login_required
def addpwd():
    error = None
    if request.method == 'POST':
        username = session.get('username')
        user = User.query.filter(User.username == username).first()
        pwd = PWD(pwdname=request.form['pwdname'],account=request.form['account'],pwd=request.form['pwd'],other=request.form['other'],father=user.id,create_time=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime()),isdel=0)
        db.session.add(pwd)
        db.session.commit()
        return redirect(url_for('panel'))
    else:
        return render_template('addpwd.html', error=error)


#密码信息设置
@app.route('/set/<pwdid>', methods=['GET', 'POST'])
def setting(pwdid):
    pwds = PWD.query.filter(and_(PWD.id == pwdid,PWD.isdel == 0)).first()
    if request.method == 'POST':
        pwds.pwdname = request.form['pwdname']
        pwds.account = request.form['account']
        pwds.pwd = request.form['pwd']
        pwds.other = request.form['other']
        db.session.commit()
        return redirect(url_for('panel'))
    return render_template('reset.html',pwds = pwds)


#用户信息设置
@app.route('/setuser/<userid>', methods=['GET', 'POST'])
def setuser(userid):
    user = User.query.filter(and_(User.id==userid,User.isdel==0)).first()
    if request.method == 'POST':
        user.password = request.form['password']
        user.email = request.form['email']
        db.session.commit()
        return redirect(url_for('panel'))
    return render_template('resetuser.html',user=user)

#删除密码
@app.route('/del/<pwdid>')
def delete(pwdid):
    pwds = PWD.query.filter(and_(PWD.id == pwdid,PWD.isdel == 0)).first()
    pwds.isdel = 1
    pwds.del_time = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    db.session.commit()
    return redirect(url_for('panel'))


#删除用户
@app.route('/deluser/<userid>')
def deleteuser(userid):
    user = User.query.filter(and_(User.id==userid,User.isdel==0)).first()
    user.isdel = 1
    user.del_time = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    db.session.commit()
    session.pop('username', None)
    return redirect(url_for('home'))

#网站头像
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.before_request
def pp():
    print(os.path.join(app.root_path, 'static'))

if __name__ == '__main__':
    # app.run(host="0.0.0.0", port=80, debug = True)
    # app.run(host="192.168.0.103", port=80, debug = True)
    app.run(host="127.0.0.1", port=80, debug=True)