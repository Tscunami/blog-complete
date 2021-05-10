from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from typing import Callable
import os
from functools import wraps
from flask import abort
import smtplib
# from static.data import *
from dotenv import load_dotenv
from pathlib import Path


dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)


# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# Initialize CKEditor - text editor with a lot of features
ckeditor = CKEditor(app)

# Initialize flask_bootstrap required for WTForms
Bootstrap(app)

# Initialize Gravatar - used for profile pictures on users
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False,
                    base_url=None)

# CONNECT TO DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Class prevents errors when using Column, String, Integer, Float and Boolean in our initialization of the table
class MySQLAlchemy(SQLAlchemy):
    Column: Callable
    String: Callable
    Integer: Callable
    Float: Callable
    Boolean: Callable
    Text: Callable


db = MySQLAlchemy(app)


# Table users
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")

    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


# Table blog_posts
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the table name of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_post")


# Table comments
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # "users.id" The users refers to the tablename of the Users class.
    # "comments" refers to the comments property in the User class.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    # ***************Child Relationship*************#
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


db.create_all()

# Create file with our DB and tables
# if not os.path.isfile("blog.db"):
#     db.create_all()


# Configure Flask app to use Flask_Login
login_manager = LoginManager()
login_manager.init_app(app)


# User_loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def home():
    # Select all posts from db and renders it at home page
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():

        # Search if there's already user with that email
        if User.query.filter(User.email == form.email.data).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()

        # Log in and authenticate user after adding details to database.
        login_user(new_user)
        return redirect(url_for("home"))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        email = form.email.data
        password = form.password.data

        user = User.query.filter(User.email == email).first()

        # Email doesn't exists
        if not user:
            flash("That email does not exists, please try again.")
            return redirect(url_for('login'))

        # Password incorrect
        elif not check_password_hash(pwhash=user.password, password=password):
            flash("Password incorrect, please try again.")
            return redirect(url_for("login"))

        # Email exists and password correct
        else:
            login_user(user)
            return redirect(url_for("home"))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/post/<int:post_id>", methods=['POST', 'GET'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=requested_post.id))

    return render_template("post.html", post=requested_post, current_user=current_user, form=form)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    # if request.method == 'POST':
    #     form_data = request.form
    #     username = form_data['username']
    #     email = form_data['email']
    #     phone = form_data['phone']
    #     message = form_data['message']
    #
    #     # Send Email
    #     subject = f"Subject:New Blog Message from {username}\n\n"
    #     recipient = os.getenv("TO_EMAIL")
    #     text = f" Name: {username}\n Email: {email}\n Phone: {phone}\n Message: {message}"
    #     message = f"{subject}{text}"
    #
    #     with smtplib.SMTP("smtp.mail.yahoo.com", port=587) as connection:
    #         connection.starttls()
    #         connection.login(user=os.getenv("FROM_EMAIL"), password=os.getenv("PASSWORD"))
    #         connection.sendmail(
    #             from_addr=os.getenv("FROM_EMAIL"),
    #             to_addrs=recipient,
    #             msg=message
    #         )

        # return render_template("contact.html", message="Successfully sent your message")
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/delete-comment/<int:post_id>/<int:comment_id>", methods=["GET", "POST"])
@login_required
def delete_comment(post_id, comment_id):
    comment_to_delete = Comment.query.get(comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id))


if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)
