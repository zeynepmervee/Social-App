from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from models import db, User, Post, Like, Comment
from forms import LoginForm, RegistrationForm, UpdateProfileForm, PostForm
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    post_form = PostForm()
    if request.method == 'POST' and post_form.validate_on_submit():
        post = Post(content=post_form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!', 'success')
        return redirect(url_for('home'))
    
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('home.html', posts=posts, post_form=post_form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    update_form = UpdateProfileForm(obj=current_user)
    post_form = PostForm()
    
    if request.method == 'POST':
        if 'submit' in request.form:  # Profile update form submitted
            if update_form.validate_on_submit():
                current_user.name = update_form.name.data
                current_user.email = update_form.email.data
                db.session.commit()
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('profile'))
        else:  # Post form submitted
            if post_form.validate_on_submit():
                post = Post(content=post_form.content.data, author=current_user)
                db.session.add(post)
                db.session.commit()
                flash('Post created successfully!', 'success')
                return redirect(url_for('home'))
    
    posts = Post.query.filter_by(author=current_user).order_by(Post.created_at.desc()).all()
    return render_template('profile.html', update_form=update_form, post_form=post_form, posts=posts)

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You cannot edit this post!', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        post.content = request.form.get('content')
        post.edited = True
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('home'))
    return render_template('edit_post.html', post=post)

@app.route('/post/<int:post_id>/delete')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        flash('You cannot delete this post!', 'danger')
        return redirect(url_for('home'))
    
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        
        if like:
            db.session.delete(like)
            db.session.commit()
            return jsonify({'status': 'unliked', 'likes_count': post.likes_count})
        else:
            like = Like(user_id=current_user.id, post_id=post_id)
            db.session.add(like)
            db.session.commit()
            return jsonify({'status': 'liked', 'likes_count': post.likes_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    try:
        post = Post.query.get_or_404(post_id)
        content = request.form.get('content')
        
        if not content or not content.strip():
            flash('Comment cannot be empty!', 'danger')
            return redirect(url_for('home'))
        
        comment = Comment(content=content.strip(), author=current_user, post=post)
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while adding your comment.', 'danger')
        return redirect(url_for('home'))

@app.route('/post/<int:post_id>/comments')
@login_required
def get_comments(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('_comments.html', post=post)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
