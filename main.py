import flask
from flask import Flask, render_template, redirect, url_for, request
from werkzeug.utils import secure_filename
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired
from dotenv import load_dotenv
import psycopg2
import os
import stripe

load_dotenv()

stripe.api_key = os.environ.get('API_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('APPKEY')
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
Bootstrap5(app)
if os.environ.get('LOCAL') == 'True':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///items.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_URL')
db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(Users, user_id)


the_item = None


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(250), nullable=False, unique=True)
    Name = db.Column(db.String(250), nullable=False)
    Password = db.Column(db.String(250), nullable=False)


class stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String, nullable=False)
    img_url = db.Column(db.String, nullable=False)
    img_url_2 = db.Column(db.String, nullable=True)
    img_url_3 = db.Column(db.String, nullable=True)
    img_url_4 = db.Column(db.String, nullable=True)
    img_url_5 = db.Column(db.String, nullable=True)
    description = db.Column(db.String(5000), nullable=False)
    price = db.Column(db.Float, nullable=False)
    product_id = db.Column(db.String, nullable=False, unique=True)
    price_id = db.Column(db.String, nullable=False)
    qty = db.Column(db.Integer, nullable=False)


class Login(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("login")


# with app.app_context():
#     db.create_all()
    # try:
    #     admin = Users(Email='admin@gmail.com', Name='admin', Password='123456')
    #     db.session.add(admin)
    #     db.session.commit()
    # except:
    #     pass


@app.route('/')
def home():
    items = db.session.execute(db.select(stock).order_by(stock.id)).scalars()
    return render_template('index.html', items=items, logged_in=current_user.is_authenticated)


@app.route('/login', methods=['GET', 'POST'])
def login():
    id = 1
    form = Login()
    if form.validate_on_submit():
        admin_login = db.get_or_404(Users, id)
        if form.name.data == admin_login.Name and form.password.data == admin_login.Password:
            login_user(admin_login)
            db.session.close()
            return redirect(url_for('home'))
        else:
            return '<h1>Wrong entry try to login again!</h1>'
    return render_template('login.html', form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        file = request.files["picture"]
        file.save(os.path.join('static/images/', secure_filename(file.filename)))
        try:
            file1 = request.files["picture1"]
            file1.save(os.path.join('static/images/', secure_filename(file1.filename)))
        except PermissionError:
            pass
        try:
            file2 = request.files["picture2"]
            file2.save(os.path.join('static/images/', secure_filename(file2.filename)))
        except PermissionError:
            pass
        try:
            file3 = request.files["picture3"]
            file3.save(os.path.join('static/images/', secure_filename(file3.filename)))
        except PermissionError:
            pass
        try:
            file4 = request.files["picture4"]
            file4.save(os.path.join('static/images/', secure_filename(file4.filename)))
        except PermissionError:
            pass
        # print(file.filename)
        # print(os.listdir('static/images'))
        the_product = stripe.Product.create(name=f"{request.form.get('product')}")
        prix = stripe.Price.create(
            product=the_product['id'],
            unit_amount=int(float(request.form.get("price")) * 100),
            currency="usd",
        )
        new_entry = stock(name=request.form.get('product'), img_url=f'/images/{file.filename}',
                          img_url_2=f'/images/{file1.filename}', img_url_3=f'/images/{file2.filename}',
                          img_url_4=f'/images/{file3.filename}', img_url_5=f'/images/{file4.filename}',
                          price=float(request.form.get("price")), price_id=prix['id'], product_id=the_product['id'],
                          qty=request.form.get("stock"), author=request.form.get('author'),
                          description=request.form.get('description'))
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('elements.html', logged_in=current_user.is_authenticated)


@app.route("/delete/<int:id>")
@login_required
def delete(id):
    book_to_delete = db.get_or_404(stock, id)
    db.session.delete(book_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/view/<int:id>', methods=['GET', 'POST'])
def view(id):
    global the_item
    the_item = db.get_or_404(stock, id)
    images = [the_item.img_url, the_item.img_url_2, the_item.img_url_3, the_item.img_url_4, the_item.img_url_5]
    return render_template('generic.html', image=images, name=the_item.name, price=the_item.price,
                           author=the_item.author, description=the_item.description, the_id=id,
                           logged_in=current_user.is_authenticated)


@app.route('/success')
def success():
    return render_template('success.html', logged_in=current_user.is_authenticated)


@app.route('/buy')
def buy():
    checkout = stripe.checkout.Session.create(
        success_url=url_for('success', _external=True),
        line_items=[{"price": f"{the_item.price_id}", "quantity": 1}],
        mode="payment",
    )
    return redirect(checkout['url'])


if __name__ == "__main__":
    app.run(debug=True)
