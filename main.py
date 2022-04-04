from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_gravatar import Gravatar

from sqlalchemy.orm import relationship
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

# -------------------------------------------- Make flask App ----------------------------------------------------- #

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'

ckeditor = CKEditor(app)
Bootstrap(app)

# -------------------------------------------- Make Gravatar -------------------------------------------------------- #

gravatar = Gravatar(app, size=100, rating="g", default="retro",
                    force_default=False, force_lower=False, use_ssl=False, base_url=None)

# -------------------------------------------- Make Database ------------------------------------------------------ #

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    author = relationship("User", back_populates='post')
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    comments = relationship("Comment", back_populates='parent_post')

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True)
    name = db.Column(db.String(250))
    password = db.Column(db.String(250))

    post = relationship("BlogPost", back_populates='author')
    comments = relationship("Comment", back_populates='comment_author')


class Comment(UserMixin, db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)

    comment_author = relationship("User", back_populates='comments')
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    parent_post = relationship("BlogPost", back_populates='comments')
    parent_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    text = db.Column(db.Text, nullable=False)


db.create_all()

# -------------------------------------------- Set Login Manager ---------------------------------------------------- #

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------------------- Make Decorator ------------------------------------------------------- #
def admin_only(f):
    @wraps(f)
    def decorator_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(404)
        return f(*args, **kwargs)
    return decorator_function

# --------------------------------------------- all Flask Route ----------------------------------------------------- #
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        if User.query.filter_by(email=register_form.email.data).first():
            flash("this email already sign up, login instead!")
            return redirect(url_for("login"))
        else:
            # Create salted password.
            salted_hashed_password = generate_password_hash(password=register_form.password.data,
                                                            method="pbkdf2:sha256",
                                                            salt_length=8)
            # Create new user.
            new_user = User(
                email=register_form.email.data,
                name=register_form.name.data,
                password=salted_hashed_password,
            )
            # Add new user to database.
            db.session.add(new_user)
            db.session.commit()
            # login new user after added new user to database.
            login_user(new_user)
            return redirect(url_for("get_all_posts", current_user=current_user))
    return render_template("register.html", form=register_form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        # Get data from form by create variable.
        email = login_form.email.data
        password = login_form.password.data
        # find email in database.
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("This Email doesn't exist, please try again!")
            return redirect(url_for("login"))
        elif not check_password_hash(pwhash=user.password, password=password):
            flash("Password is not correct, please try again!")
            return redirect(url_for("login"))
        else:
            login_user(user)
            return redirect(url_for("get_all_posts", current_user=current_user))
    return render_template("login.html", form=login_form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts', current_user=current_user))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    form = CommentForm()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        # Create new comment.
        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post,
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=form, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    print(f"now user name is: {current_user.name}")
    print(f"user id is: {current_user.id}")
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
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
@admin_only
def edit_post(post_id):
    # Find blog post from id.
    post = BlogPost.query.get(post_id)
    # Create edit form by old post.
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
