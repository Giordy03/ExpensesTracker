from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
import json
import os

app = Flask(__name__)

bcrypt = Bcrypt(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "thisisasecretkey"
db = SQLAlchemy(app)        # creates database instance

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    # String(n) --> n is the max numb of character allowed
    # nullable=False --> field cannot be empty
    # unique --> field must be unique in the database (there cannot be two user with the same username)
    password = db.Column(db.String(80), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    # validators: condition inputted value must meet
    # render_kw: what the user reads
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")        # bottom to press after entering the data

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError(f"{username} already exist. Please choose a different one")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


def write_expenses_file():
    with open("expenses.json", "w") as file:
        json.dump(expenses, file)
    
    
def write_categories_file():
    with open("categories.json", "w") as file:
        json.dump(categories, file)
        
        
def read_expenses_file():
    if os.path.exists("expenses.json"):
        with open("expenses.json", "r") as file:
            return json.load(file)
    else:
        return {}
    

def read_categories_file():
    if os.path.exists("categories.json"):
        with open("categories.json", "r") as file:
            return json.load(file)
    else:
        return {}


# Initialize expenses and categories from files
expenses = read_expenses_file()
categories = read_categories_file()


class CategoryForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=50)], render_kw={"placeholder": "Category Name"})
    submit = SubmitField("Add Category")


class ExpenseForm(FlaskForm):
    amount = StringField(validators=[InputRequired()], render_kw={"placeholder": "Amount"})
    description = StringField(validators=[InputRequired(), Length(min=1, max=100)], render_kw={"placeholder": "Description"})
    category = SelectField("Category", choices=[], validators=[InputRequired()])
    submit = SubmitField("Add Expense")


@app.route("/")         # path visible in the url in the browser: page when open the link
# (ideally 127.0.0.1:5000 == localhost:5000)
def home():             # link the page to a html script (in that case homa page)
    return render_template("home.html")


@app.route("/login", methods=["get", "post"])       # login page: http command get and post
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("dashboard"))
            # if the login is successful, the page dashboard is opened
    return render_template("login.html", form=form)     # where the localhost:5000/login brings the user


@app.route("/dashboard", methods=["get", "post"])
@login_required             # this page is reserved to logged-in users
def dashboard():
    return render_template("dashboard.html")
    # return render_template("dashboard.html")


@app.route("/logout", methods=["get", "post"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@ app.route("/register", methods=["get", "post"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.commit()
        db.session.add(new_user)
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/add_category", methods=["GET", "POST"])
@login_required
def add_category():
    form = CategoryForm()
    existing_categories = categories.get(current_user.id, [])
    if form.validate_on_submit():
        if current_user.id not in categories:
            categories[current_user.id] = []
        categories[current_user.id].append(form.name.data)
        write_categories_file()
        return redirect(url_for("dashboard"))
    return render_template("add_category.html", form=form, existing_categories=existing_categories)


@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    form = ExpenseForm()
    form.category.choices = [(cat, cat) for cat in categories.get(current_user.id, [])]
    if form.validate_on_submit():
        if current_user.id not in expenses:
            expenses[current_user.id] = []
        expense_data = {
            'amount': form.amount.data,
            'description': form.description.data,
            'category': form.category.data
        }
        expenses[current_user.id].append(expense_data)
        write_expenses_file()
        return redirect(url_for("dashboard"))
    return render_template("add_expense.html", form=form)


@app.route("/expenses")
@login_required
def expenses_view():
    user_expenses = expenses.get(current_user.id, [])
    return render_template("expenses.html", expenses=user_expenses)


if __name__ == "__main__":
    app.run(debug=True)
