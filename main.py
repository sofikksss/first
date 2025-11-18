from flask import Flask,render_template,g, request, redirect, url_for
import sqlite3
from werkzeug.security import  generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
app = Flask(__name__)
DATABASE = 'post1.db'
app.config['SECRET_KEY'] = 'dithebest'

login_manager = LoginManager(app)
login_manager.login_view = 'login'
username = 'admin'
password = 'admin123'
password_hash = generate_password_hash(password)
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user = db.execute(
        'SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    if user is not None:
        return User(user[0], user[1], user[2])
    db.commit()
    return None
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
    return g.db

def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.teardown_appcontext
def close_connection(exception):
    close_db(exception)

@app.route('/')
def index():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''SELECT post.id, post.title, post.content, post.author_id,
                      user.username, COUNT(like.id) AS likes FROM post
                      JOIN user ON post.author_id = user.id
                      LEFT JOIN like ON post.id = like.post_id
                      GROUP BY post.id, post.title, post.content,
                      post.author_id, user.username''')
    result = cursor.fetchall()
    posts = []
    for post in reversed(result):
        posts.append(
         {'id': post[0],
          'title':post[1],
          'content': post[2],
          'author_id': post[3],
          'username': post[4],
          'likes': post[5]}
        )
        if current_user.is_authenticated:
            db.execute(
                'SELECT post_id FROM like WHERE user_id = ?', (current_user.id, )
            )
            likes_result = cursor.fetchall()
            liked_posts = []
            for like in likes_result:
                liked_posts.append(int(like[0]))
            posts[-1]['liked_posts'] = liked_posts
    context = {
        'posts': posts
    }
    return render_template('blog.html',  **context)


@app.route('/SF/')
def SF():
    context = {
        'sf' : [
            {
                'title': 'Sally Face',
                'content': 'Sally Face — приключенческая инди-игра с элементами хоррора и детектива, разработанная американским геймдизайнером Стивом Габри.Игра повествует о мальчике по имени Сал Фишер, который носит протез на лице и вместе с друзьями расследует убийства, совершаемые в городе Нокфелл.'
            }
        ]
    }

    return render_template('Sally Face.html', **context)
@app.route('/FB/')
def FB():
    return render_template('Fran Bow.html')
@app.route('/add/', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        db = get_db()
        db.execute('INSERT INTO post (title, content, author_id) VALUES (?, ?, ?)', (title, content, current_user.id))
        db.commit()
    return render_template('add_post.html')
@app.route('/register', methods=['GET','POST'])
def register():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO user (username, password_hash, email) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), email)
            )
            db.commit()
            print('Регистрация прошла успешно')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            message = 'Username already exists!'
    return render_template('register.html', message=message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()
        if user and User(user[0], user[1], user[2]).check_password(password):
            login_user(User(user[0], user[1], user[2]))
            return redirect(url_for('index'))
        else:
            return render_template('login.html', message='Invalid username or password')

    # Возврат формы при GET-запросе
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM post WHERE id = ?',(post_id,)).fetchone()
    if post and post[3] == current_user.id:
        db.execute('DELETE FROM post WHERE id = ?', (post_id,))
        db.commit()
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

def user_is_liking(user_id, post_id):
    db = get_db()
    like = db.execute('SELECT * FROM like WHERE user_id = ? AND post_id = ?',
                      (user_id, post_id)).fetchone()
    db.commit()
    return bool(like)

@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM post WHERE id = ?',(post_id,)).fetchone()
    if post:
        if user_is_liking(current_user.id, post_id):
            db = get_db()
            db.execute('DELETE FROM like WHERE user_id = ? AND post_id = ?',
                       (current_user.id, post_id))
            db.commit()
            print('You unliked this post')
        else:
            db.execute('INSERT INTO like (user_id,post_id) VALUES (?, ?)',
                       (current_user.id, post_id))
            db.commit()
            print('You liked this post')
        return redirect(url_for('index'))
    return 'Post not found', 404

if __name__ == '__main__':
    app.run(debug=True)
