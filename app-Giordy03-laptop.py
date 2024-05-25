from flask import Flask, render_template, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt


app = Flask(__name__)

bcrypt = Bcrypt(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "thisisasecretkey"
db = SQLAlchemy(app)        # creates database instance

login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# db. specifies what the database is going to be
    # we can set primary and foreign key
        # if primary key is not specified, it will be automatically set
    # Model specifies what we are saving into the database
    # columns are an attribute of the model
    # default='' specifies the value if nullable=False and not specified
    # we must specify what each column is going to contain (integers, strings...)
    # between Model of databases, there can be relationships (db.relationship('', backref='', lazy=True)
        # run a query, non an actual column in the database structure
    
    # in terminal:
        # db.create_all()   create the structure of the database itself
        # db.drop_all()     delete the contents and the structure of the database
        

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    # String(n) --> n is the max numb of character allowed
    # nullable=False --> field cannot be empty
    # unique --> field must be unique in the database (there cannot be two user with the same username)
    password = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"User: {self.username}"


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    # validators: condition inputted value must meet
    # render_kw: what the user reads
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")        # bottom to press after entering the data

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError(f"{username} already exist. Please choose a different one")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


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
            flash("Username and password doesn't match: try again", "error")
            return render_template("login.html", form=form)
        else:
            flash("Username not valid: try again", "error")
    return render_template("login.html", form=form)
    # where the localhost:5000/login brings the user


@app.route("/dashboard", methods=["get", "post"])
@login_required             # this page is reserved to logged in users
def dashboard():
    return render_template("expenses.html")


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
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


if __name__ == "__main__":
    app.run(debug=True)
