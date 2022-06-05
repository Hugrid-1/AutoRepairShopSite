#подгрузка необходимых библиотек
import datetime
import re
from typing import Union, Any

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user, LoginManager,UserMixin, login_user, logout_user
from sqlalchemy import create_engine
from sqlalchemy.engine.mock import MockConnection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db_string = "postgresql://vova:123@localhost/AutoRepairShop" #адрес подключения к БД


app = Flask( __name__ ,static_folder='static',static_url_path='/static') #определение переменной приложения
app.config['SQLALCHEMY_DATABASE_URI'] = db_string
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'CVN5M974M12fgXda315sczNMx778JKMnb32cv'

dbEngine: Union[MockConnection, Any] = create_engine(db_string) #создание класса базы данных
dbApp = SQLAlchemy(app)

login__manager = LoginManager(app)
LoginManager.login_view = 'authorization'
LoginManager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
LoginManager.login_message_category = "success"

autopartCart = [] #список хранящий предметы в корзине


def valid_password(password): # проверка пароля на корректность
    checkStatus = False
    if password is None:
        return checkStatus
    else:
        if len(password) < 6: #Проверка длины пароля
            print("Длина пароля недостаточна")
            return False
        alphaCounter = 0 #счетчик букв
        for i in password:
            if i.isalpha() and alphaCounter <= 2:
                alphaCounter += 1 #увеличение счетчика
            elif alphaCounter >= 3:
                checkStatus = True
                return checkStatus #выход из цикла при наборе нужного количества букв
        print("Символов недостаточно")
        return checkStatus

def valid_telephone_number(inp): #проверка номера телефона на корректность
    # проверка длины телефона, длина должна быть 12 и наличие индексов 3 и 7
    # if not all(inp[x] == "-" for x in [7]) and len(inp) == 12:
    #     return False
    # return inp.replace("-", "", 3).isdigit()
    return True

def valid_fio(fio): #проверка корректности ФИО
    return re.fullmatch(r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?', fio) #проверка соответствия регулярному выражению

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
@app.route('/') # обработка 1-го варианта адресного пути
@app.route('/home') # обработка 2-го варианта адресного пути
def mainpage(): # функция
    print("[LOG] Переход на главную страницу сайта")
    return render_template("index.html")

#### ВЫВОД КАТАЛОГА АВТОЗАПЧАСТЕЙ ####
@app.route('/catalog',methods=['GET','POST'])
def showStampsList():
    data = dbEngine.execute('SELECT * FROM "Stamps"').fetchall()
    minPrice = request.form.get('minPrice')
    maxPrice = request.form.get('maxPrice')
    if request.method == "POST":
        print(minPrice,maxPrice)
        # data = db

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
    data = dbEngine.execute(f'SELECT * FROM "Autoparts" WHERE id_model = {modelID}').fetchall() #запрос на получение запчастей по модели
    if request.method == "POST":
        if request.form['action'] == "addToCart":
            autopart = get_autopart(request.form['autopart'])
            autopartCart.append(autopart)
            #print(f"[LOG] В корзину добавлена запчасть {autopart.modelName}")
            print(autopartCart)

        if request.form['action'] == "removeFromCart":
            autopart = get_autopart(request.form['autopart'])
            # print(f"[LOG] Из корзины удалена запчасть {autopart.modelName}")
            autopartCart.remove(autopart)
            print(autopartCart)

    return render_template("catalog.html", data=data, viewmode="autopart", static='static',autopartCart=autopartCart,cartLen=len(autopartCart))

def get_autopart(autopartID):
    autopart = dbEngine.execute(f'SELECT * FROM "Autoparts" WHERE id = {autopartID}').fetchone()
    return autopart

@app.route('/cart',methods=['GET','POST'])
@login_required
def cartPage():
    todayDate = datetime.date.today() #получение сегодняшней даты
    cartPrice = 0 #переменная для общей цены заказа
    for autopart in autopartCart: #формирование цены заказа
        cartPrice += autopart.price
    if request.method == "POST":
        service_date = request.form['dateService']
        user_id = current_user.get_id()
        requestStatus = "Создан"
        #добавление записи заказа
        dbEngine.execute(f'INSERT INTO "SellRequests" (create_day, event_day, user_id, status, cart_price) VALUES' + f"('{todayDate}', '{service_date}', {user_id},'{requestStatus}',{cartPrice}) RETURNING id")
        lastRow = dbEngine.execute('SELECT * FROM public."SellRequests"ORDER BY id DESC ')
        request_id = lastRow.fetchone().id # получение id только что добавленной записи

        #добавление записей в таблицу содержимого заказов
        for autopart in autopartCart:
            dbEngine.execute(f'INSERT INTO "Sell_items" (request_id,autopart_id) VALUES' + f"('{request_id}', '{autopart.id}')")

        print(f"[LOG] СОЗДАН ЗАКАЗ С ID:{request_id} , пользователем {current_user.login} id:{current_user.get_id()}")
        autopartCart.clear() #очистка корзины после создания заказа
        print("[LOG] Корзина очищена")

        return redirect(url_for('showAccountInfo')) #переадресация в профиль

    return render_template("buy.html",todayDate=todayDate,autopartCart=autopartCart,cartLen=len(autopartCart),CartPrice=cartPrice)

@app.route('/services')
def showServiceList():
    serviceList = dbEngine.execute('SELECT * FROM "Services"')
    return render_template("services.html",services=serviceList)

@app.route('/serviceRegistration/<service_id>',methods=['GET','POST'])
def addServiceRequest(service_id):
    todayDate = datetime.date.today()
    service = dbEngine.execute(f'SELECT * FROM "Services" WHERE id = {service_id}').fetchone()
    if request.method == "POST":
        print(request.form)
        service_date = request.form['dateService']
        user_id = current_user.get_id()
        type(user_id)
        if user_id is None:
            return redirect(url_for('authorization'))
        requestStatus = "Создан"
        print(service.id)
        dbEngine.execute(f'INSERT INTO "ServiceRequests" (service_id,create_day, event_day,  user_id, status)  VALUES' + f"({service.id},'{todayDate}', '{service_date}', {user_id},'{requestStatus}') RETURNING id")

        print(f"[LOG] ЗАПИСЬ НА УСЛУГУ {service.serviceName} пользователем {current_user.login} id:{current_user.get_id()}")
        return redirect(url_for('showAccountInfo'))  # переадресация в профиль
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
    return render_template("accountPage.html",userServiceRequestList=userServiceRequestList,userSellRequestList=userSellRequestList)

#Авторизация/Регистрация пользователя
@app.route('/authorization',methods=['GET','POST'])
def authorization():
    print(request.form)
    if request.method =="POST":
        if request.form["checkForm"] == "registration":
            #получение данных из формы регистрации
            username = request.form.get("username")
            password = request.form.get("password")
            retry_password = request.form.get("retry_password")
            email = request.form.get("email")
            fio = request.form.get("fio")
            telephone = request.form.get("telephone")

            hash_pwd = generate_password_hash(password) #кодировка пароля

            if username and password and email and fio and telephone:
                if password != retry_password:
                    flash('Пароли не одинаковы')
                    # return render_template("authorization.html")
                elif not valid_password(password):
                    flash('Пароль некорректен')
                    # return render_template("authorization.html")
                elif not valid_fio(fio):
                    flash('ФИО некорректно')
                    # return render_template("authorization.html")
                else:
                    dbEngine.execute(f'INSERT INTO "Users" (login, email, fio, password, telephone) VALUES' + f"('{username}', '{email}', '{fio}','{hash_pwd}','{telephone}')")
                    return redirect(request.args.get("next") or url_for("showAccountInfo"))
            else:
                flash("Заполнены не все поля")
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
                    print("[LOG ERROR] ПОЛЬЗОВАТЕЛЬ НЕ СУЩЕСТВУЕТ ЛИБО ПАРОЛЬ НЕВЕРНЫЙ")
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
    print("[LOG] ПОЛЬЗОВАТЕЛЬ ВЫШЕЛ ИЗ АККАУТНА")
    return redirect(url_for('mainpage'))

@app.errorhandler(404)
def not_found_error(error):
    print('[ОШИБКА 404]',error)
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    print('[ОШИБКА 500]',error)
    return render_template('index.html'), 500

dbApp.create_all()
app.run(debug=True) #запуск программы на локальном сервере
