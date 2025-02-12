from flask import request, redirect, render_template, flash, url_for
from app import app
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash
from app.forms import RegistrationForm, LoginForm, AddBookForm, BasketForm, SearchForm, EditUserForm, PasswordForm, EmailForm, FeedbackForm
from app.user import User
from flask_login import login_user, current_user, logout_user
from datetime import datetime

# Главная страница, поиск книг по категории или автору
@app.route('/', methods=['GET', 'POST'])
def index():
    category_name = request.args.get('category_name')  # Получение категории из параметров запроса
    author_name = request.args.get('author_name')  # Получение автора из параметров запроса
    form = SearchForm()
    if form.validate_on_submit():  # Обработка поиска
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Поиск книг по названию или автору
                cur.execute('''SELECT * 
                            FROM book b
                            JOIN author_book ab ON b.isbn=ab.isbn
                            WHERE b.name ILIKE %s
                            OR ab.name_author ILIKE %s''',
                            (f'%{form.search_query.data}%', f'%{form.search_query.data}%',))
                books = cur.fetchall()
                return render_template('index.html', books=books, form=form)

        except Exception as e:
            flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')

    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()

            # Фильтр по автору или категории
            if author_name:
                cur.execute('''SELECT * 
                                   FROM book b
                                   JOIN author_book ab ON b.isbn = ab.isbn
                                   WHERE ab.name_author = %s''', (author_name,))
                books = cur.fetchall()
            elif category_name:
                cur.execute('''SELECT * 
                                    FROM book b
                                    JOIN author_book ab ON b.isbn = ab.isbn
                                    JOIN category_book cb ON b.isbn = cb.isbn
                                    WHERE cb.category_name = %s''', (category_name,))
                books = cur.fetchall()
            else:
                # Если фильтры не указаны, выводим все книги
                cur.execute('''SELECT * 
                            FROM book b
                            JOIN author_book ab ON b.isbn = ab.isbn''')
                books = cur.fetchall()

    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        books = []

    return render_template('index.html', books=books, form=form)


# Страница входа в систему
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Проверка пользователя по логину
                cur.execute('''SELECT * 
                                     FROM "user" 
                                     WHERE login = %s''', (login_form.login.data,))
                res = cur.fetchone()
            # Проверка введенного пароля
            if res is None or not check_password_hash(res[1], login_form.password.data):
                flash('Попытка входа неудачна', 'danger')
                return redirect(url_for('login'))
            login, password, name, email, role, library_card = res
            user = User(login, password, name, email, role, library_card)
            login_user(user)  # Авторизация пользователя
            flash(f'Вы успешно вошли в систему, {current_user.name}', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Ошибка при выполнении входа: {e}', 'danger')
    return render_template('login.html', form=login_form)


# Страница восстановления пароля (ввод email)
@app.route('/email', methods=['GET', 'POST'])
def email():
    form = EmailForm()
    if form.validate_on_submit():
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Проверка существующего email
            cur.execute('''SELECT email FROM "user"
                                WHERE email = %s''', (form.email.data,))
            cur_email = cur.fetchone()
        if cur_email:
            return redirect(url_for('password', cur_email=cur_email[0]))  # Переход на страницу смены пароля

    return render_template('email.html', form=form)


# Регистрация нового пользователя
@app.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    reg_form = RegistrationForm()  # Создаем объект формы регистрации
    if reg_form.validate_on_submit():  # Проверяем, была ли форма корректно заполнена
        password_hash = generate_password_hash(reg_form.password.data)  # Хэшируем пароль
        try:
            # Подключение к базе данных для сохранения нового пользователя
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Добавление нового пользователя в таблицу "user"
                cur.execute(
                    """
                    INSERT INTO "user" (login, password, name, email, role)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (reg_form.login.data, password_hash, reg_form.name.data, reg_form.email.data, "user")
                )
            flash(f'Регистрация {reg_form.name.data} успешна', 'success')
            return redirect(url_for('login'))  # Перенаправляем пользователя на страницу входа

        except psycopg.errors.UniqueViolation as e:  # Обработка ошибки уникальности
            flash('Ошибка: пользователь с таким логином или email уже существует.', 'danger')
            print(f"UniqueViolation Error: {e}")  # Логирование ошибки

        except Exception as e:  # Общая ошибка
            flash(f'Ошибка при регистрации: {str(e)}', 'danger')

    return render_template('sign_up.html', form=reg_form)  # Отображение страницы регистрации


# Редактирование данных пользователя
@app.route('/edit_user', methods=['GET', 'POST'])
def edit_user():
    # Подключение к базе данных для получения текущих данных пользователя
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        # Получаем имя и email текущего пользователя
        cur.execute('''SELECT name, email FROM "user"
                    WHERE login = %s''', (current_user.login,))
        user = cur.fetchone()
    # Инициализация формы редактирования с текущими данными
    form = EditUserForm(name=user[0], email=user[1])
    if form.validate_on_submit():  # Проверяем, была ли форма корректно заполнена
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Обновление данных пользователя
            cur.execute('''UPDATE "user"
                                SET name = %s, email = %s
                                WHERE login = %s''', (form.name.data, form.email.data, current_user.login,))
        flash('Изменения сохранены', 'success')
        return redirect(url_for('profile'))  # Перенаправляем на страницу профиля

    return render_template('edit_user.html', form=form)


# Страница профиля пользователя
@app.route('/profile')
def profile():
    return render_template('profile.html')


# Добавление новой книги (доступно только для админа)
@app.route('/add-book', methods=['GET', 'POST'])
def add_book():
    if current_user.role == 'admin' and current_user.is_authenticated:  # Проверка прав доступа
        form = AddBookForm()  # Создаем объект формы для добавления книги
        if form.validate_on_submit():  # Проверяем, была ли форма корректно заполнена
            try:
                # Подключение к базе данных
                with psycopg.connect(
                        host=app.config['DB_SERVER'],
                        user=app.config['DB_USER'],
                        port=app.config['DB_PORT'],
                        password=app.config['DB_PASSWORD'],
                        dbname=app.config['DB_NAME']
                ) as con:
                    cur = con.cursor()
                    # Добавление новой книги в базу данных
                    cur.execute(
                        """
                        INSERT INTO "book" (name, isbn, publication_year, num_stock, name_publish, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (form.name.data, form.isbn.data, form.publication_year.data,
                         form.num_stock.data, form.name_publish.data, form.description.data)
                    )
                    # Добавление категорий книги
                    for category_name in form.categories.data:
                        cur.execute(""" 
                            INSERT INTO category_book (isbn, category_name) 
                            VALUES (%s, %s)""", (form.isbn.data, category_name))

                    # Проверка существования автора, добавление при необходимости
                    cur.execute('''SELECT name FROM author
                                        WHERE name = %s''', (form.author_name.data,))
                    author = cur.fetchone()
                    if not author:
                        cur.execute('''INSERT INTO author (name)
                                        VALUES (%s)''', (form.author_name.data,))

                    # Связывание книги с автором
                    cur.execute('''INSERT INTO author_book (name_author, isbn)
                                        VALUES (%s, %s)''', (form.author_name.data, form.isbn.data,))

                flash(f'Книга "{form.name.data}" добавлена успешно', 'success')
                return redirect(url_for('add_book'))  # Перенаправляем обратно на страницу добавления книги
            except Exception as e:
                flash(f'Ошибка при добавлении книги: {str(e)}', 'danger')
        return render_template('addbook.html', form=form)  # Отображение формы добавления книги
    else:
        flash('Нет доступа!', 'danger')
        return redirect(url_for('index'))  # Перенаправление на главную страницу при отсутствии доступа


# Выход из системы
@app.route('/logout')
def logout():
    logout_user()  # Выход пользователя из системы
    flash('Вы вышли из системы', 'info')  # Отображение сообщения об успешном выходе
    return redirect(url_for('index'))  # Перенаправление на главную страницу

# Страница категорий и авторов
@app.route('/category')
def category():
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        # Получение списка категорий
        cur.execute('''SELECT name FROM category''')
        categories = cur.fetchall()
        # Получение списка авторов
        cur.execute('''SELECT name FROM author''')
        authors = cur.fetchall()
    # Отображение страницы категорий и авторов
    return render_template('category.html', categories=categories, authors=authors)

# Страница с детальной информацией о книге
@app.route('/book/<isbn>', methods=['GET', 'POST'])
def book_detail(isbn):
    num_form = BasketForm()  # Форма для добавления книги в бронь
    status = "Не подтвержден"  # Статус возврата книги

    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()

            # Получение данных книги по ISBN
            cur.execute("SELECT * FROM book WHERE isbn = %s", (isbn,))
            book = cur.fetchone()

            # Получение автора книги
            cur.execute("SELECT name_author FROM author_book WHERE isbn = %s", (isbn,))
            author = cur.fetchone()

            if not book:
                flash('Книга не найдена', 'danger')
                return redirect(url_for('index'))

            # Отображаем страницу с книгой перед обработкой формы
            if request.method == 'GET':
                return render_template('book_detail.html', book=book, author=author, form=num_form)

            # Проверка формы и бронирование книги
            if num_form.validate_on_submit() and book[3] > 0:  # Проверка формы на корректность
                cur.execute('''SELECT * FROM user_books
                            WHERE login = %s AND isbn = %s AND status = %s''',
                            (current_user.login, isbn, status,))
                exist = cur.fetchone()

                if exist:
                    flash(f'Книга уже забронирована', 'danger')
                else:
                    cur.execute('''INSERT INTO user_books (login, isbn)
                                VALUES (%s, %s)''', (current_user.login, isbn,))
                    flash(f'Книга забронирована', 'success')

                return redirect(url_for('book_detail', isbn=isbn))

            flash(f'Невозможно забронировать книгу', 'danger')
            return redirect(url_for('book_detail', isbn=isbn))

    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('index'))

# Удаление книги из каталога (для админа)
@app.route('/delete_book/<isbn>', methods=['POST'])
def delete_book(isbn):
    if current_user.role == 'admin':  # Проверка прав доступа
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Удаление книги по ISBN
                cur.execute('''DELETE FROM book 
                               WHERE isbn = %s''', (isbn,))
                flash('Книга удалена из каталога', 'success')
                return redirect(url_for('index'))
        except Exception as e:
            flash(f'Ошибка при удалении книги: {str(e)}', 'danger')
            return redirect(url_for('book_detail', isbn=isbn))
    else:
        flash('У вас нет прав на выполнение этого действия.', 'warning')
        return redirect(url_for('login'))  # Перенаправление на страницу входа при отсутствии прав

# Добавление книги в избранное
@app.route('/add_like/<isbn>', methods=['POST'])
def add_like(isbn):
    if current_user.is_authenticated:  # Проверка, авторизован ли пользователь
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Добавление книги в таблицу избранного
                cur.execute('''INSERT INTO liked_book(isbn, login)
                               VALUES (%s, %s)''', (isbn, current_user.login,))
                flash('Книга добавлена в избранные', 'success')
                return redirect(url_for('book_detail', isbn=isbn))
        except Exception as e:
            flash(f'Книга уже в избранных', 'danger')
            return redirect(url_for('book_detail', isbn=isbn))
    else:
        flash('Войдите в систему, чтобы добавить книгу в избранное.', 'warning')
        return redirect(url_for('login'))  # Перенаправление на страницу входа при отсутствии авторизации

# Отображение списка избранных книг
@app.route('/profile/like')
def like():
    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение всех книг из избранного текущего пользователя
            cur.execute('''SELECT b.isbn, b.name, ab.name_author 
                        FROM book b
                        JOIN liked_book lb ON b.isbn = lb.isbn
                        JOIN author_book ab ON b.isbn = ab.isbn
                        WHERE lb.login = %s''', (current_user.login,))
            books = cur.fetchall()

        return render_template('like.html', books=books)
    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('profile'))

# Удаление книги из избранного
@app.route('/delete_like/<isbn>', methods=['POST'])
def delete_like(isbn):
    if current_user.is_authenticated:  # Проверка, авторизован ли пользователь
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Удаление книги из избранного
                cur.execute('''DELETE FROM liked_book 
                               WHERE isbn = %s''', (isbn,))
                flash('Книга удалена из избранного', 'success')
                return redirect(url_for('like'))
        except Exception as e:
            flash(f'Ошибка при удалении: {str(e)}', 'danger')
            return redirect(url_for('book_detail', isbn=isbn))
    else:
        flash('Войдите в систему, чтобы удалить книгу из избранного.', 'warning')
        return redirect(url_for('login'))  # Перенаправление на страницу входа при отсутствии авторизации

# Просмотр брони пользователя
@app.route('/basket')
def basket():
    status = "Не подтвержден"  # Статус, означающий, что бронь еще не подтверждена
    try:
        # Подключение к базе данных для получения содержимого брони
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение данных о книгах в брони текущего пользователя
            cur.execute('''SELECT b.name, b.isbn, a.name_author 
                                FROM book b
                                JOIN user_books bt ON b.isbn = bt.isbn
                                JOIN author_book a ON b.isbn = a.isbn
                                WHERE bt.login = %s AND bt.status = %s''', (current_user.login, status,))
            books = cur.fetchall()
    except Exception as e:
        # В случае ошибки перенаправляем на главную страницу
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('index'))

    # Отображаем страницу брони с данными о книгах
    return render_template('basket.html', books=books)

# Удаление книги из брони
@app.route('/delete_basket/<isbn>', methods=['POST'])
def delete_basket(isbn):
    try:
        # Подключение к базе данных для удаления книги из брони
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Удаление книги из брони текущего пользователя по ISBN
            cur.execute('''DELETE FROM user_books 
                           WHERE isbn = %s AND login = %s''', (isbn, current_user.login,))
            flash('Книга удалена', 'success')
            return redirect(url_for('basket'))  # Перенаправление на страницу брони после удаления книги
    except Exception as e:
        # В случае ошибки возвращаем пользователя в брони
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('basket'))  # Перенаправление на брони при ошибке

# Отображение списка взятых книг текущего пользователя
@app.route('/my_orders')
def my_orders():
    status = 'Не подтвержден'  # Статус, означающий, что бронь еще не подтвержден
    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение всех книг текущего пользователя
            cur.execute('''SELECT * FROM user_books ub
                        JOIN book b ON b.isbn = ub.isbn
                        WHERE ub.login = %s AND ub.status != %s''', (current_user.login, status,))
            orders = cur.fetchall()
        return render_template('myorders.html', orders=orders)  # Отображение страницы со списком книг
    except Exception as e:
        flash(f'Ошибка при загрузке заказов: {str(e)}', 'danger')
        return redirect(url_for('index'))  # Перенаправление на главную страницу в случае ошибки

# Отображение списка обращений, требующих подтверждения (для админа)
@app.route('/check_orders')
def check_orders():
    none_status = 'Не подтвержден'
    back_status = 'Запрос на возврат'
    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение всех обращений с состоянием "Не подтвержден" или "Запрос на возврат"
            cur.execute('''SELECT * FROM user_books
                        WHERE status = %s OR status = %s''', (none_status, back_status,))
            orders = cur.fetchall()
        return render_template('myorders.html', orders=orders)
    except Exception as e:
        flash(f'Ошибка при загрузке заказов: {str(e)}', 'danger')
        return redirect(url_for('index'))  # Перенаправление на главную страницу при ошибке

# Просмотр всех обращений
@app.route('/all_orders')
def all_orders():
    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение всех обращений из базы данных
            cur.execute('''SELECT * FROM user_books''')
            orders = cur.fetchall()
        return render_template('myorders.html', orders=orders)
    except Exception as e:
        flash(f'Ошибка при загрузке заказов: {str(e)}', 'danger')
        return redirect(url_for('index'))  # Перенаправление на главную страницу при ошибке

# Детальная информация о конкретном обращении
@app.route('/order/<num>', methods=['GET', 'POST'])
def order_detail(num):
    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            cur.execute('''SELECT ub.id, b.name, ab.name_author, ub.begin_date, ub.end_date, ub.status, b.isbn 
                        FROM user_books ub
                        JOIN book b ON b.isbn = ub.isbn
                        JOIN author_book ab ON ab.isbn = b.isbn
                        WHERE ub.id = %s''', (num,))
            cur_order = cur.fetchone()

        return render_template('order_detail.html', order=cur_order)
    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('index'))  # Перенаправление на главную страницу при ошибке

# Изменение статуса обращения
@app.route('/change_status/<num>', methods=['POST'])
def change_status(num):
    get_status = 'Выдан'  # Статус обращения, когда книга выдана пользователю
    back_status = 'Запрос на возврат'  # Статус запроса на возврат книги
    end_status = 'Возвращен'  # Статус возврата книги
    current_date = datetime.now()
    date = current_date.date()  # Текущая дата для статуса "Доставлен"
    try:
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение текущего статуса заказа
            cur.execute('''SELECT status FROM user_books
                        WHERE id = %s''', (num,))
            status = cur.fetchone()
            if status and status[0] == "Не подтвержден":
                cur.execute('''UPDATE user_books
                                    SET status = %s, begin_date = %s
                                    WHERE id = %s''', (get_status, date, num,))
                cur.execute('''UPDATE book b
                                SET num_stock = num_stock - 1
                                FROM user_books ub
                                WHERE b.isbn = ub.isbn
                                AND ub.id = %s;''', (num,))
            elif status and status[0] == get_status:
                cur.execute('''UPDATE user_books
                                SET status = %s
                                WHERE id = %s''', (back_status, num,))
            elif status and status[0] == back_status:
                cur.execute('''UPDATE user_books
                                SET status = %s, end_date = %s
                                WHERE id = %s''', (end_status, date, num,))
                cur.execute('''UPDATE book b
                                SET num_stock = num_stock + 1
                                FROM user_books ub
                                WHERE b.isbn = ub.isbn
                                AND ub.id = %s;''', (num,))
        return redirect(url_for('order_detail', num=num))
    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('order_detail', num=num))

# Добавление отзыва о книге
@app.route('/add_feedback/<isbn>', methods=['GET', 'POST'])
def add_feedback(isbn):
    form = FeedbackForm()
    if form.validate_on_submit():
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Вставка нового отзыва в таблицу "feedback"
            cur.execute('''INSERT INTO feedback(mark, description, isbn, login)
                        VALUES (%s, %s, %s, %s)''', (form.mark.data, form.description.data, isbn, current_user.login,))
        flash('Отзыв успешно добавлен', 'success')
        return redirect(url_for('book_detail', isbn=isbn))  # Перенаправление на страницу книги
    return render_template('add_feedback.html', form=form)

# Просмотр всех отзывов о книге
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    isbn = request.args.get('isbn')  # Получение ISBN книги из параметров запроса
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        cur.execute('''SELECT f.mark, f.description, f.login, b.name
                    FROM book b 
                    JOIN feedback f ON b.isbn = f.isbn
                    WHERE f.isbn = %s''', (isbn,))
        feedbacks = cur.fetchall()
    if feedbacks:
        return render_template("feedback.html", feedbacks=feedbacks)  # Отображение отзывов
    else:
        flash('Отзывы отсутствуют', 'danger')
        return redirect(url_for('book_detail', isbn=isbn))  # Перенаправление на страницу книги при отсутствии отзывов

@app.route('/all_feedbacks', methods=['GET', 'POST'])
def all_feedbacks():
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        cur.execute('''SELECT f.mark, f.description, f.login, b.name
                        FROM book b 
                        JOIN feedback f ON b.isbn = f.isbn''')
        feedbacks = cur.fetchall()
    if feedbacks:
        return render_template("all_feedbacks.html", feedbacks=feedbacks)  # Отображение отзывов
    else:
        flash('Отзывы отсутствуют', 'danger')
        return redirect(url_for('profile'))  # Перенаправление на страницу профиля при отсутствии отзывов
