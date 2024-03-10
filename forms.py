from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, StringField, SubmitField, PasswordField, URLField
from wtforms.validators import DataRequired, Length, URL

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    register_button = SubmitField("Create Account")

class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    login_button = SubmitField("Log In")

class AddBookForm(FlaskForm):
    title = StringField("Book Title", validators=[DataRequired()])
    author = StringField("Book Author", validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired()])
    price = FloatField("Price (Eur)", validators=[DataRequired()])
    price_id = StringField("Price ID", validators=[DataRequired()])
    img_url = StringField("Book Cover URL", validators=[DataRequired()])
    add_button = SubmitField("Add")