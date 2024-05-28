from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField
from wtforms.validators import InputRequired, Length, ValidationError, Optional
from flask_bcrypt import Bcrypt
import json
import os
from datetime import datetime
from calendar import monthrange

app = Flask(__name__)

bcrypt = Bcrypt(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "thisisasecretkey"
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

EXPENSES_FILE = "expenses.json"
CATEGORIES_FILE = "categories.json"
BUDGET_FILE = "budget.json"


# Functions to read/write from/to JSON files
def write_to_file(filepath, data):
    with open(filepath, "w") as file:
        json.dump(data, file)


def read_from_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            return json.load(file)
    return {}


expenses = read_from_file(EXPENSES_FILE)
categories = read_from_file(CATEGORIES_FILE)
budgets = read_from_file(BUDGET_FILE)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(username=username.data).first()
        if existing_user_username:
            raise ValidationError(f"{username} already exists. Please choose a different one")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


class CategoryForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=20)], render_kw={"placeholder": "Category Name"})
    submit = SubmitField("Add Category")


class ExpenseForm(FlaskForm):
    amount = StringField(validators=[InputRequired()], render_kw={"placeholder": "Amount"})
    description = StringField(validators=[InputRequired(), Length(min=1, max=100)],
                              render_kw={"placeholder": "Description"})
    date = DateField("Date", format="%Y-%m-%d", validators=[InputRequired()])
    category = SelectField("category", choices=[], validators=[InputRequired()])
    submit = SubmitField("Add Expense")


class BudgetForm(FlaskForm):
    budget = StringField(validators=[InputRequired()], render_kw={"placeholder": "Budget"})
    submit = SubmitField("Set budget")
    
    
class FilterForm(FlaskForm):
    category = SelectField("Category", choices=[("None", "None")], validators=[Optional()])
    start_date = DateField("Start date", format="%Y-%m-%d", validators=[Optional()])
    end_date = DateField("End date", format="%Y-%m-%d", validators=[Optional()])
    submit = SubmitField("Filter")

    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("dashboard"))
    return render_template("login.html", form=form)


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/add_category", methods=["GET", "POST"])
@login_required
def add_category():
    form = CategoryForm()
    existing_categories = categories.get(str(current_user.id), [])
    if form.validate_on_submit():
        new_category = form.name.data
        if str(current_user.id) not in categories:
            categories[str(current_user.id)] = []
        categories[str(current_user.id)].append(new_category)
        write_to_file(CATEGORIES_FILE, categories)
        flash(f"Category '{new_category}' added successfully!")
        return redirect(url_for("add_category"))
    
    if request.method == "POST" and "delete" in request.form:
        category_to_delete = request.form.get("delete")
        if category_to_delete in existing_categories:
            existing_categories.remove(category_to_delete)
            categories[str(current_user.id)] = existing_categories
            write_to_file(CATEGORIES_FILE, categories)
            flash(f"Category {category_to_delete} has been deleted successfully")
            
    return render_template("add_category.html", form=form, categories=existing_categories)


@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    form = ExpenseForm()
    form.category.choices = [(cat, cat) for cat in categories.get(str(current_user.id), [])]
    if form.validate_on_submit():
        if str(current_user.id) not in expenses:
            expenses[str(current_user.id)] = []
        expense_data = {
            "id": len(expenses[str(current_user.id)]) + 1,
            "amount": form.amount.data,
            "description": form.description.data,
            "date": form.date.data.strftime("%Y-%m-%d"),
            "category": form.category.data
        }
        expenses[str(current_user.id)].append(expense_data)
        write_to_file(EXPENSES_FILE, expenses)
        return redirect(url_for("dashboard"))
    return render_template("add_expense.html", form=form)


@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses_view():
    form = FilterForm()
    form.category.choices = [("None", "None")] + [(cat, cat) for cat in categories.get(str(current_user.id), [])]
    user_expenses = expenses.get(str(current_user.id), [])
    if form.validate_on_submit():
        filer_category = form.category.data
        filter_start_date = form.start_date.data
        filter_end_date = form.end_date.data
        if filer_category and filer_category != "None":
            user_expenses = [expense for expense in user_expenses if expense["category"] == filer_category]
        if filter_start_date:
            user_expenses = [expense for expense in user_expenses
                             if datetime.strptime(expense["date"], "%Y-%m-%d").date() >= filter_start_date]
        if filter_end_date:
            user_expenses = [expense for expense in user_expenses
                             if datetime.strptime(expense["date"], "%Y-%m-%d").date() <= filter_end_date]
    if request.method == "POST" and "delete" in request.form:
        expense_id_to_delete = int(request.form.get("delete"))
        user_expenses = [expense for expense in user_expenses if expense[id] != expense_id_to_delete]
        expenses[str(current_user.id)] = user_expenses
        write_to_file(EXPENSES_FILE, user_expenses)
        flash(f"The expense has been deleted successfully")
    return render_template("expenses.html", form=form, expenses=user_expenses)


@app.route("/budget", methods=["GET", "POST"])
@login_required
def manage_budget():
    form = BudgetForm()
    if form.validate_on_submit():
        new_budget = float(request.form.get("budget"))
        budgets[str(current_user.id)] = new_budget
        write_to_file(BUDGET_FILE, budgets)
        flash(f"Budget set to {new_budget}")
        return redirect(url_for("manage_budget"))
    else:
        user_budget = budgets.get(str(current_user.id), 0)
        monthly_expenses, remaining_budget, average_expense_remaining_days = \
            calculate_monthly_expenses(str(current_user.id))
        current_date = f"{datetime.now().month}-{datetime.now().year}"
        print(f"current month: {current_date}")
        return render_template("budget.html", form=form, user_budget=user_budget, monthly_expenses=monthly_expenses,
                               remaining_budget=remaining_budget, expense_remaining_days=average_expense_remaining_days,
                               current_month=current_date)
    
    
def calculate_monthly_expenses(user_id):
    monthly_expenses = dict()
    user_expenses = expenses.get(user_id, [])
    user_budget = budgets.get(str(user_id), 0)
    for expense in user_expenses:
        expense_date = datetime.strptime(expense["date"], "%Y-%m-%d")
        month = expense_date.month
        year = expense_date.year
        key = f"{month}-{year}"
        if key not in monthly_expenses:
            monthly_expenses[key] = 0
        monthly_expenses[key] += float(expense["amount"])
    remaining_budget = {key: user_budget - total for key, total in monthly_expenses.items()}
    today = datetime.now()
    last_day_of_month = monthrange(today.year, today.month)[1]
    days_remaining = last_day_of_month - today.day + 1
    print(f"remaining days: {days_remaining}")
    total_remaining_budget = remaining_budget.get(f"{datetime.now().month}-{datetime.now().year}", 0)
    average_expense_per_day = total_remaining_budget / days_remaining if days_remaining > 0 else 0
    return monthly_expenses, remaining_budget, average_expense_per_day


@app.template_filter("absolute")
def absolute(value):
    return abs(float(value))


if __name__ == "__main__":
    app.run(debug=True)
