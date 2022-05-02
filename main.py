from flask import Flask,render_template, request, flash, redirect, url_for, send_from_directory
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import create_engine


db_string = "postgresql://vova:123@localhost/AutoRepairShop" #адрес подключения к БД

db = create_engine(db_string) #создание класса базы данных

app = Flask( __name__ ) #определение переменной приложения


########ОБРАБОТКА АДРЕСНЫХ ПУТЕЙ###########

#главная страница
@app.route('/')
@app.route('/home')
def mainpage():
    return render_template("index.html")

@app.route('/catalog')
def showStampsList():
    data = db.execute('SELECT * FROM "Stamps"').fetchall()
    return render_template("catalog.html",data=data,viewmode="stamp")
@app.route('/catalog/<stampId>')
def showModelsList(stampId):
    data = db.execute(f'SELECT * FROM "Models" WHERE "stampID" = {stampId}').fetchall()
    return render_template("catalog.html",data=data,viewmode="model",stampId=stampId)

@app.route('/catalog/<stampId>/<modelID>')
def showAutoPartList(stampId,modelID):
    data = db.execute(f'SELECT * FROM "Autoparts" WHERE id_model = {modelID}').fetchall()
    return render_template("catalog.html", data=data, viewmode="autopart")

@app.route('/services')
def showServiceList():
    serviceList = db.execute('SELECT * FROM "Services"')
    return render_template("services.html",services=serviceList)

@app.route('/contacts')
def showContacts():
    return render_template("contact.html")
@login_required
@app.route('/accountPage')
def showAccountInfo():
    return 0

app.run(debug=True) #запуск программы на локальном сервере
