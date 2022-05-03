from flask import Flask, render_template, redirect, url_for, request
from flask_login import UserMixin, login_user, logout_user
from flask_login import login_required, current_user, LoginManager
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash, check_password_hash

db_string = "postgresql://vova:123@localhost/AutoRepairShop" #адрес подключения к БД

db = create_engine(db_string) #создание класса базы данных


app = Flask( __name__ ,static_folder='static',static_url_path='/static') #определение переменной приложения

app.secret_key = 'CVN5M974M12fgXda315sczNMx778JKMnb32cv'

login__manager = LoginManager(app)
LoginManager.login_view = 'authorization'
LoginManager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
LoginManager.login_message_category = "success"

### Работа с БД #######
#Получение пользоваталея по id
def GetUser(id):
    user = db.execute(f'SELECT * FROM "Users" WHERE id = {id} LIMIT 1').fetchone()
    if not user:
        print("Пользователь не найден")
        return False

class UserLogin(UserMixin):
    def fromDB(self, user_id):
        self.__user = GetUser(user_id)
        return self

    def create(self, user):
        self.__user = user
        return self

    def get_id(self):
        return str(self.__user['id'])



########ОБРАБОТКА АДРЕСНЫХ ПУТЕЙ###########

#главная страница
@app.route('/')
@app.route('/home')
def mainpage():
    return render_template("index.html")

#### ВЫВОД КАТАЛОГА АВТОЗАПЧАСТЕЙ ####
@app.route('/catalog')
def showStampsList():
    data = db.execute('SELECT * FROM "Stamps"').fetchall()
    return render_template("catalog.html",data=data,viewmode="stamp")

@app.route('/catalog/<stampId>')
def showModelsList(stampId):
    data = db.execute(f'SELECT * FROM "Models" WHERE "stampID" = {stampId}').fetchall()
    return render_template("catalog.html",data=data,viewmode="model",stampId=stampId)

@app.route('/catalog/<stampID>/<modelID>')
def redirectToAutoPartList(stampID,modelID):
    return redirect(url_for('showAutoPartList',modelID=modelID))
    #return render_template("catalog.html", data=data, viewmode="autopart",stampId=stampId,static='static')

@app.route('/catalog-for-your-choice/<modelID>')
def showAutoPartList(modelID):
    data = db.execute(f'SELECT * FROM "Autoparts" WHERE id_model = {modelID}').fetchall()

    return render_template("catalog.html", data=data, viewmode="autopart", static='static')

@app.route('/services')
def showServiceList():
    serviceList = db.execute('SELECT * FROM "Services"')
    return render_template("services.html",services=serviceList)

@app.route('/contacts')
def showContacts():
    return render_template("contact.html")

###### СИСТЕМА АВТОРИЗАЦИИ #######
@app.route('/profile')
@login_required
def showAccountInfo():
    #buy_history
    return render_template("accountPage.html",user_data=1)


@app.route('/authorization',methods=['GET','POST'])
def authorization():
    print(request.form)
    if request.method =="POST":
        if request.form["checkForm"] == "registration":
            #получение данных из формы регистрации
            username = request.form["username"]
            password = request.form["password"]
            email = request.form["email"]
            fio = request.form["fio"]
            telephone = request.form["telephone"]

            hash_pwd = generate_password_hash(password) #кодировка пароля

            if username and password and email and fio and telephone:
                db.execute(f'INSERT INTO "Users" (login, email, fio, password, telephone) VALUES' + f"('{username}', '{email}', '{fio}','{hash_pwd}','{telephone}')")
                return redirect(request.args.get("next") or url_for("showAccountInfo"))
            else:
                print("Заполнены не все поля")
        elif request.form["checkForm"] == "login":
            login = request.form["username"]
            password = request.form["password"]
            if login and password:
                user = db.execute(f'SELECT * FROM "Users" WHERE "login" =' + f"'{login}'" +' LIMIT 1').fetchone()
                print(user)
                if user and check_password_hash(user.password, password):
                    userlogin = UserLogin().create(user)
                    #rm = True if request.form.get('remainme') else False
                    login_user(userlogin, remember=True)
                    print(f"АВТОРИЗОВАН {current_user.get_id()}")
                    return redirect(request.args.get("next") or url_for("showAccountInfo"))
                else:
                    print("ПОЛЬЗОВАТЕЛЬ НЕ СУЩЕСТВУЕТ ЛИБО ПАРОЛЬ НЕВЕРНЫЙ")
            else:
                pass #ПРОПИСАТЬ
    return render_template("authorization.html")

@login__manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id)

@login__manager.unauthorized_handler
def unauthorized():
    return redirect("authorization")

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('mainpage'))
app.run(debug=True) #запуск программы на локальном сервере
