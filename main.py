import datetime

from flask import Flask, render_template, redirect, url_for, request
from flask_login import UserMixin, login_user, logout_user
from flask_login import login_required, current_user, LoginManager
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
db_string = "postgresql://vova:123@localhost/AutoRepairShop" #адрес подключения к БД




app = Flask( __name__ ,static_folder='static',static_url_path='/static') #определение переменной приложения
app.config['SQLALCHEMY_DATABASE_URI'] = db_string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'CVN5M974M12fgXda315sczNMx778JKMnb32cv'

dbEngine = create_engine(db_string) #создание класса базы данных
dbApp = SQLAlchemy(app)

login__manager = LoginManager(app)
LoginManager.login_view = 'authorization'
LoginManager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
LoginManager.login_message_category = "success"

autopartCart = []
### Работа с БД #######

class User(dbApp.Model,UserMixin):
    __tablename__ = 'Users'
    id = dbApp.Column(dbApp.Integer, primary_key=True)
    login = dbApp.Column(dbApp.String(25), nullable=False)
    email = dbApp.Column(dbApp.String(300), nullable=False)
    password = dbApp.Column(dbApp.String(300), nullable=False)
    fio = dbApp.Column(dbApp.String(1000), nullable=False)
    telephone = dbApp.Column(dbApp.String(15), nullable=False)


########ОБРАБОТКА АДРЕСНЫХ ПУТЕЙ###########

#главная страница
@app.route('/')
@app.route('/home')
def mainpage():
    print()
    return render_template("index.html")

#### ВЫВОД КАТАЛОГА АВТОЗАПЧАСТЕЙ ####
@app.route('/catalog')
def showStampsList():
    data = dbEngine.execute('SELECT * FROM "Stamps"').fetchall()
    return render_template("catalog.html",data=data,viewmode="stamp",autopartCart=autopartCart,cartLen=len(autopartCart))

@app.route('/catalog/<stampId>')
def showModelsList(stampId):
    data = dbEngine.execute(f'SELECT * FROM "Models" WHERE "stampID" = {stampId}').fetchall()
    return render_template("catalog.html",data=data,viewmode="model",stampId=stampId,autopartCart=autopartCart,cartLen=len(autopartCart))

@app.route('/catalog/<stampID>/<modelID>')
def redirectToAutoPartList(stampID,modelID):
    return redirect(url_for('showAutoPartList',modelID=modelID,autopartCart=autopartCart,cartLen=len(autopartCart)))
    #return render_template("catalog.html", data=data, viewmode="autopart",stampId=stampId,static='static')

@app.route('/catalog-for-your-choice/<modelID>',methods=['GET','POST'])
def showAutoPartList(modelID):
    data = dbEngine.execute(f'SELECT * FROM "Autoparts" WHERE id_model = {modelID}').fetchall()
    if request.method == "POST":
        if request.form['action'] == "addToCart":
            autopart = get_autopart(request.form['autopart'])
            autopartCart.append(autopart)
            print("В корзину добавлена запчасть")
            print(autopartCart)
        if request.form['action'] == "removeFromCart":
            autopart = get_autopart(request.form['autopart'])
            print("Из корзины удалена запчасть")
            autopartCart.remove(autopart)
            print(autopartCart)
    return render_template("catalog.html", data=data, viewmode="autopart", static='static',autopartCart=autopartCart,cartLen=len(autopartCart))


def get_autopart(autopartID):

    autopart = dbEngine.execute(f'SELECT * FROM "Autoparts" WHERE id = {autopartID}').fetchone()
    return autopart

@app.route('/cart',methods=['GET','POST'])
@login_required
def cartPage():
    todayDate = datetime.date.today()
    cartPrice = 0
    for autopart in autopartCart:
        cartPrice += autopart.price
    if request.method == "POST":
        service_date = request.form['dateService']
        user_id = current_user.get_id()
        requestStatus = "Создан"
        dbEngine.execute(f'INSERT INTO "SellRequests" (create_day, event_day, user_id, status, cart_price) VALUES' + f"('{todayDate}', '{service_date}', {user_id},'{requestStatus}',{cartPrice}) RETURNING id")
        lastRow = dbEngine.execute('SELECT * FROM public."SellRequests"ORDER BY id DESC ')
        request_id = lastRow.fetchone().id
        for autopart in autopartCart:
            dbEngine.execute(f'INSERT INTO "Sell_items" (request_id,autopart_id) VALUES' + f"('{request_id}', '{autopart.id}')")
    return render_template("buy.html",autopartCart=autopartCart,cartLen=len(autopartCart),CartPrice=cartPrice)



@app.route('/services')
def showServiceList():
    serviceList = dbEngine.execute('SELECT * FROM "Services"')
    return render_template("services.html",services=serviceList)

@app.route('/serviceRegistration/<service_id>',methods=['GET','POST'])
@login_required
def addServiceRequest(service_id):
    todayDate = datetime.date.today()
    service = dbEngine.execute(f'SELECT * FROM "Services" WHERE id = {service_id}').fetchone()
    if request.method == "POST":
        print(request.form)
        service_date = request.form['dateService']
        user_id = current_user.get_id()
        requestStatus = "Создан"
        dbEngine.execute(f'INSERT INTO "ServiceRequests" (create_day, event_day, service_id, user_id, status) VALUES' + f"('{todayDate}', '{service_date}', {service_id},{user_id},'{requestStatus}')")

    return render_template("ServiceReg.html",service=service,todayDate=todayDate)


#страница с контактами
@app.route('/contacts')
def showContacts():
    return render_template("contact.html")

###### СИСТЕМА АВТОРИЗАЦИИ #######

#страница с профилем пользователя
@app.route('/profile')
@login_required
def showAccountInfo():
    print(current_user.login,current_user.id,current_user.fio)
    userServiceRequestList = dbEngine.execute(f'SELECT * FROM "UserServiceRequests"'+f" WHERE user_id = {current_user.id} ")
    userSellRequestList =  dbEngine.execute(f'SELECT * FROM "SellRequests"'+f" WHERE user_id = {current_user.id} ")
    #buy_history
    return render_template("accountPage.html",userServiceRequestList=userServiceRequestList,userSellRequestList=userSellRequestList)

#Авторизация/Регистрация пользователя
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
                dbEngine.execute(f'INSERT INTO "Users" (login, email, fio, password, telephone) VALUES' + f"('{username}', '{email}', '{fio}','{hash_pwd}','{telephone}')")
                return redirect(request.args.get("next") or url_for("showAccountInfo"))
            else:
                print("Заполнены не все поля")
        elif request.form["checkForm"] == "login":
            login = request.form["username"]
            password = request.form["password"]
            if login and password:
                user = User.query.filter_by(login=login).first()
                print(user)
                if user and check_password_hash(user.password, password):
                    #rm = True if request.form.get('remainme') else False
                    login_user(user, remember=True)
                    print(f"АВТОРИЗОВАН {current_user.get_id()}")
                    return redirect(request.args.get("next") or url_for("showAccountInfo"))
                else:
                    print("ПОЛЬЗОВАТЕЛЬ НЕ СУЩЕСТВУЕТ ЛИБО ПАРОЛЬ НЕВЕРНЫЙ")
            else:
                pass #ПРОПИСАТЬ
    return render_template("authorization.html")

#подгрузка пользователя
@login__manager.user_loader
def load_user(user_id):
    print("load_user")
    return User.query.get(user_id)

#обработчик для перенаправления на авторизацию неавторизированного пользователя
@login__manager.unauthorized_handler
def unauthorized():
    return redirect("authorization")

#выход из аккаунта
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('mainpage'))

dbApp.create_all()
app.run(debug=True) #запуск программы на локальном сервере
