import os
import stripe
from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Integer, Float, String, Text, ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from forms import AddBookForm, LoginForm, RegisterForm

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(32)
Bootstrap5(app)

stripe_keys = {
    "publishable_key": os.environ["STRIPE_PUBLISHABLE_TKEY"],
    "secret_key": os.environ["STRIPE_SECRET_TKEY"]
}

stripe.api_key = stripe_keys["secret_key"]


# Create database
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///bookstore.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Create a User table for all registered users
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

# Create inventory table
class Book(db.Model):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    price_id: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

# Create cart
class CartItem(db.Model):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    price_id: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

with app.app_context():
    db.create_all()


# Configure Flask login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            if current_user.id != 1:
                return abort(403)
            return f(*args, **kwargs)
        return abort(403)
    return decorated_function


@app.route("/register", methods=["GET", "POST"])
def register():
    register_form = RegisterForm()

    if register_form.validate_on_submit():
        name = register_form.name.data
        email = register_form.email.data
        password = generate_password_hash(register_form.password.data, method="pbkdf2:sha256:600000", salt_length=16)
        print(name)

        user = db.session.execute(db.select(User).where(User.email == email)).scalar()

        if user:
            return redirect("/login")
        
        new_user = User(
            name=name,
            email=email,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        login_user(user)

        return redirect("/")
        
    return render_template("register.html", form=register_form, current_user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data

        user = db.session.execute(db.select(User).where(User.email == email)).scalar()

        if user:
            if check_password_hash(user.password, password):
                login_user(user)

                return redirect("/")
            
            return render_template("login.html", form=login_form, current_user=current_user)
            
        return redirect("/register")
    
    return render_template("login.html", form=login_form, current_user=current_user)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


@app.route("/")
def home():
    return render_template("index.html", current_user=current_user)


@app.route("/books")
def show_books():
    books = db.session.execute(db.select(Book)).scalars().all()
    return render_template("books.html", current_user=current_user, books=books)


@app.route("/cart", methods=["GET", "POST"])
@login_required
def buy_books():
    if request.method == "POST":
        price_id = request.form.get("price_id")
        print(f"PRICE ID IS: {price_id}")
        book = db.session.execute(db.select(Book).where(Book.price_id == price_id)).scalar()
        print(book.title)

        new_cart_item = CartItem(
            book_id=book.id,
            title=book.title,
            author=book.author,
            description=book.description,
            price=book.price,
            price_id=book.price_id,
            img_url=book.img_url
        )

        db.session.add(new_cart_item)
        db.session.commit()

        books = db.session.execute(db.select(CartItem)).scalars().all()

        line_items = []
        for item in books:
            line_items.append({
                "price": item.price_id,
                "quantity": 1
            })

        session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=url_for("thanks", _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=url_for("buy_books", _external=True)
        )

        return render_template(
            "cart.html", 
            checkout_session_id=session["id"], 
            checkout_public_key=stripe_keys["publishable_key"],
            current_user=current_user, books=books)
    
    books = db.session.execute(db.select(CartItem)).scalars().all()
    return render_template("cart.html", books=books)


@app.route("/thanks")
@login_required
def thanks():
    return render_template("thanks.html")


@app.route("/add_books", methods=["GET", "POST"])
@admin_only
def add_books():
    add_book_form = AddBookForm()

    if add_book_form.validate_on_submit():
        title = add_book_form.title.data
        author = add_book_form.author.data
        description = add_book_form.description.data
        price = add_book_form.price.data
        price_id = add_book_form.price_id.data
        img_url = add_book_form.img_url.data

        book = db.session.execute(db.select(Book).where(Book.title == title)).scalar()

        if book:
            return redirect("/show_books")

        new_book = Book(
            title=title,
            author=author,
            description=description,
            price=price,
            price_id=price_id,
            img_url=img_url
        )

        db.session.add(new_book)
        db.session.commit()

        return redirect (url_for("show_books"))
    
    return render_template("add_books.html", form=add_book_form, current_user=current_user)


if __name__ == "__main__":
    app.run(debug=True)