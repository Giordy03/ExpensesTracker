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
SHARED_EXPENSES_FILE = "shared_expenses.json"
INCOME_FILE = "income.json"

possible_currency = ["¥", "€", "£", "$"]


# Functions to read/write from/to JSON files
def write_to_file(filepath, data):
    with open(filepath, "w") as file:
        json.dump(data, file)


def read_from_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            return json.load(file)
    return dict()


# define the data readen from the files
expenses = read_from_file(EXPENSES_FILE)
categories = read_from_file(CATEGORIES_FILE)
budgets = read_from_file(BUDGET_FILE)
shared_expenses = read_from_file(SHARED_EXPENSES_FILE)
income = read_from_file(INCOME_FILE)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, unique=True)
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
    submit = SubmitField("Add category")


class ExpenseForm(FlaskForm):
    amount = StringField(validators=[InputRequired()], render_kw={"placeholder": "Amount"})
    description = StringField(validators=[InputRequired(), Length(min=1, max=100)],
                              render_kw={"placeholder": "Description"})
    currency = SelectField("Currency", choices=list(), validators=[InputRequired()], render_kw={"placeholder": "Currency"})
    date = DateField("Date", format="%Y-%m-%d", validators=[InputRequired()])
    category = SelectField("category", choices=list(), validators=[InputRequired()])
    submit = SubmitField("Add expense")


class BudgetForm(FlaskForm):
    budget = StringField(validators=[InputRequired()], render_kw={"placeholder": "Budget"})
    submit = SubmitField("Set budget")
    
    
class FilterForm(FlaskForm):
    category = SelectField("Category", choices=[("None", "None")], validators=[Optional()])
    start_date = DateField("Start date", format="%Y-%m-%d", validators=[Optional()])
    end_date = DateField("End date", format="%Y-%m-%d", validators=[Optional()])
    submit = SubmitField("Filter")
    
    
class SharedExpensesFriendForm(FlaskForm):
    friends = StringField("Friend", validators=[InputRequired()], render_kw={"placeholder": "Friend"})
    submit = SubmitField("Add friend")


class SharedExpenseForm(FlaskForm):
    amount = StringField(validators=[InputRequired()], render_kw={"placeholder": "Amount"})
    currency = SelectField("Currency", choices=list(), validators=[InputRequired()], render_kw={"placeholder": "Currency"})
    date = DateField("Date", format="%Y-%m-%d", validators=[InputRequired()])
    category = SelectField("category", choices=list(), validators=[InputRequired()])
    paid_by = SelectField("Paid by", choices=list(), validators=[InputRequired()], render_kw={"placeholder": "Paid by"})
    submit = SubmitField("Add expense")
    
    
class IncomeForm(FlaskForm):
    amount = StringField(validators=[InputRequired()], render_kw={"placeholder": "Amount"})
    description = StringField(validators=[InputRequired(), Length(min=1, max=100)],
                              render_kw={"placeholder": "Description"})
    currency = SelectField("Currency", choices=list(), validators=[InputRequired()],
                           render_kw={"placeholder": "Currency"})
    date = DateField("Date", format="%Y-%m-%d", validators=[InputRequired()])
    submit = SubmitField("Add income")
    
    
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
    user_id = str(current_user.id)
    monthly_expenses, remaining_budget, average_expense_remaining_days = calculate_monthly_expenses(user_id)
    current_month = f"{datetime.now().month}-{datetime.now().year}"
    current_month_income = datetime.now().strftime("%Y-%m")
   
    if current_month in remaining_budget.keys():
        print("1")
        remaining_budget = remaining_budget[current_month]
        monthly_expenses = monthly_expenses[current_month]
    elif user_id in budgets.keys():
        print("2")
        remaining_budget = budgets[user_id]
        monthly_expenses = 0
    else:
        print("3")
        remaining_budget = 0
        monthly_expenses = monthly_expenses[current_month]
    today = datetime.now()
    last_day_of_month = monthrange(today.year, today.month)[1]
    days_remaining = last_day_of_month - today.day + 1
    average_expense_remaining_days = remaining_budget / days_remaining
    
    if user_id in income.keys():
        print(f"incomes: {income.get(user_id, list())}")
        user_income = sum([float(inc["amount"]) for inc in income.get(user_id, list())
                           if inc["date"].startswith(current_month_income)])
        print(f"Calculated user income for current month: {user_income}")
    else:
        user_income = 0
    
    user_expenses = sum([float(exp["amount"]) for exp in expenses.get(user_id, list())
                         if exp["date"].startswith(current_month)])
    if user_id in budgets.keys():
        user_budget = budgets.get(user_id, 0)
    else:
        user_budget = 0
    
    return render_template("dashboard.html", user_income=user_income, user_expenses=user_expenses,
                           user_budget=user_budget, monthly_expenses=monthly_expenses,
                           remaining_budget=remaining_budget,
                           average_expense_remaining_days=average_expense_remaining_days)


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
    form_category = CategoryForm()
    existing_categories = categories.get(str(current_user.id), list())
    if form_category.validate_on_submit():
        new_category = form_category.name.data
        if str(current_user.id) not in categories:
            categories[str(current_user.id)] = list()
        categories[str(current_user.id)].append(new_category)
        write_to_file(CATEGORIES_FILE, categories)
        flash(f"Category '{new_category}' added successfully!")
        return redirect(url_for("add_expense"))
    if request.method == "POST" and "delete" in request.form:
        category_to_delete = request.form.get("delete")
        if category_to_delete in existing_categories:
            existing_categories.remove(category_to_delete)
            categories[str(current_user.id)] = existing_categories
            write_to_file(CATEGORIES_FILE, categories)
            flash(f"Category {category_to_delete} has been deleted successfully")
    return redirect(url_for("add_expense"))


@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    form_category = CategoryForm()
    existing_categories = categories.get(str(current_user.id), list())
    form = ExpenseForm()
    form.currency.choices = [(curr, curr) for curr in possible_currency]
    form.category.choices = [(cat, cat) for cat in categories.get(str(current_user.id), list())]
    if form_category.validate_on_submit():
        new_category = form_category.name.data
        if str(current_user.id) not in categories:
            categories[str(current_user.id)] = list()
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
        return render_template("add_expense.html", form=form, form_cat=form_category, categories=existing_categories)
    
    if form.validate_on_submit():
        if str(current_user.id) not in expenses:
            expenses[str(current_user.id)] = list()
        expense_data = {
            "id": len(expenses[str(current_user.id)]) + 1,
            "amount": form.amount.data,
            "currency": form.currency.data,
            "description": form.description.data,
            "date": form.date.data.strftime("%Y-%m-%d"),
            "category": form.category.data
        }
        expenses[str(current_user.id)].append(expense_data)
        write_to_file(EXPENSES_FILE, expenses)
        return redirect(url_for("dashboard"))
    return render_template("add_expense.html", form=form, form_cat=form_category, categories=existing_categories)


@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses_view():
    form = FilterForm()
    form.category.choices = [("None", "None")] + [(cat, cat) for cat in categories.get(str(current_user.id), list())]
    user_expenses = expenses.get(str(current_user.id), list())
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


@app.route("/income", methods=["GET", "POST"])
@login_required
def income_manager():
    form = IncomeForm()
    form.currency.choices = [(curr, curr) for curr in possible_currency]
    if form.validate_on_submit():
        if str(current_user.id) not in income:
            income[str(current_user.id)] = list()
        income_data = {
            "amount": form.amount.data,
            "currency": form.currency.data,
            "description": form.description.data,
            "date": form.date.data.strftime("%Y-%m-%d")
        }
        income[str(current_user.id)].append(income_data)
        write_to_file(INCOME_FILE, income)
        return redirect(url_for("dashboard"))
    else:
        print(form.errors)
        user_income = income.get(str(current_user.id), list())
        return render_template("income.html", form=form, income=user_income)


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
        average_daily_expense = dict()
        for date, expense in monthly_expenses.items():
            month, year = map(int, date.split("-"))
            if date != current_date:
                days_in_month = monthrange(year, month)[1]
            else:
                days_in_month = datetime.now().day
            average_daily_expense[date] = expense / days_in_month
        return render_template("budget.html", form=form, user_budget=user_budget, monthly_expenses=monthly_expenses,
                               remaining_budget=remaining_budget, expense_remaining_days=average_expense_remaining_days,
                               current_month=current_date, average_daily_expense=average_daily_expense)
    
    
def calculate_monthly_expenses(user_id):
    monthly_expenses = dict()
    user_expenses = expenses.get(user_id, list())
    if user_id in budgets.keys():
        user_budget = budgets.get(str(user_id), 0)
    else:
        user_budget = 0
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
    total_remaining_budget = remaining_budget.get(f"{datetime.now().month}-{datetime.now().year}", 0)
    average_expense_per_day = total_remaining_budget / days_remaining if days_remaining > 0 else 0
    return monthly_expenses, remaining_budget, average_expense_per_day


@app.route("/shared", methods=["GET", "POST"])
@login_required
def shared_expenses_manager():
    form_friends = SharedExpensesFriendForm()
    form_expenses = SharedExpenseForm()

    user_shared_expenses = shared_expenses.get(str(current_user.id), list())
    friends = [item["friend"] for item in user_shared_expenses if "friend" in item]

    form_expenses.category.choices = [(cat, cat) for cat in categories.get(str(current_user.id), list())]
    form_expenses.currency.choices = [(curr, curr) for curr in possible_currency]
    form_expenses.paid_by.choices = [(friend, friend) for friend in friends]
    
    if form_friends.validate_on_submit():
        new_friend = form_friends.friends.data
        if str(current_user.id) not in shared_expenses:
            shared_expenses[str(current_user.id)] = list()
        shared_expenses[str(current_user.id)].append({"friend": new_friend})
        write_to_file(SHARED_EXPENSES_FILE, shared_expenses)
        flash(f"New friend: {new_friend} added successfully")
        return redirect(url_for("shared_expenses_manager"))

    if form_expenses.validate_on_submit():
        expense_data = {
            "amount": form_expenses.amount.data,
            "currency": form_expenses.currency.data,
            "paid_by": form_expenses.paid_by.data,
            "date": form_expenses.date.data.strftime("%Y-%m-%d"),
            "category": form_expenses.category.data
        }
        shared_expenses[str(current_user.id)].append(expense_data)
        write_to_file(SHARED_EXPENSES_FILE, shared_expenses)
        flash("Shared expense added successfully")
        return redirect(url_for("shared_expenses_manager"))
    
    friend_total = calculate_total_expenses(user_shared_expenses)
    balance = split_expense(friend_total)
    transactions = calculate_settlements(balance)
    return render_template("shared_expenses.html", form_friends=form_friends, form_expenses=form_expenses,
                           friends=friends, shared_expenses=user_shared_expenses, friend_total=friend_total,
                           balance=balance, transactions=transactions)


@app.route("/clear_shared", methods=["GET", "POST"])
@login_required
def clear_shared_expenses():
    user_id = str(current_user.id)
    if user_id in shared_expenses:
        shared_expenses[user_id] = list()
        write_to_file(SHARED_EXPENSES_FILE, shared_expenses)
        flash("All friends and expenses have been cleared")
    return redirect(url_for("shared_expenses_manager"))


def calculate_total_expenses(shared_expense):
    print(f"shared expense: {shared_expense}")
    friend_total = dict()
    for expense in shared_expense:
        if "friend" in expense and "friend" not in friend_total:
            friend_total[expense["friend"]] = 0
        else:
            paid_by = expense["paid_by"]
            amount = float(expense["amount"])
            if paid_by in friend_total:
                friend_total[paid_by] += amount
            else:
                friend_total[paid_by] = amount
    return friend_total
    
    
def split_expense(friend_total):
    gran_total = 0
    for friend, total in friend_total.items():
        gran_total += total
    numb_friends = len(friend_total)
    if numb_friends != 0:
        spent_each_friend = gran_total / numb_friends
    to_receive_to_send = dict()
    for friend, total in friend_total.items():
        to_receive_to_send[friend] = spent_each_friend - total
    return to_receive_to_send


def calculate_settlements(to_receive_to_send):
    payments = list()
    positive_balances = list()
    negative_balances = list()
    for friend, balance in to_receive_to_send.items():
        if balance > 0:
            positive_balances.append((friend, balance))
        elif balance < 0:
            negative_balances.append((friend, -balance))
    while positive_balances and negative_balances:
        payee, amount_to_receive = positive_balances.pop()
        payer, amount_to_pay = negative_balances.pop()
        
        amount = min(amount_to_receive, amount_to_pay)
        payments.append((payer, payee, amount))
        amount_to_receive -= amount
        amount_to_pay -= amount
        if amount_to_receive > 0:
            positive_balances.append((payee, amount_to_receive))
        if amount_to_pay > 0:
            negative_balances.append((payer, amount_to_pay))
    return payments


@app.template_filter("absolute")
def absolute(value):
    return abs(float(value))


if __name__ == "__main__":
    app.run(debug=True)
