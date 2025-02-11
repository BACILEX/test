import psycopg
from app import app, login_manager
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, login, password, name, email, role, library_card):
        self.name = name
        self.login = login
        self.password = password
        self.email = email
        self.role = role
        self.library_card = library_card

    def get_id(self):
        return self.login

@login_manager.user_loader
def load_user(login):
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        cur.execute('''SELECT * FROM "user" WHERE login = %s''', (login,))
        user_data = cur.fetchone()
        if user_data:
            login, password, name, email, role, library_card = user_data
            return User(login, password, name, email, role, library_card)