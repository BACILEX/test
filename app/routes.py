from flask import request, redirect, render_template, flash, url_for
from app import app
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash
from app.forms import RegistrationForm, LoginForm, AddBookForm, SaleForm, SearchFrom, AddressForm, BasketForm, SearchForm, OrderForm, EditUserForm, PasswordForm, EmailForm, FeedbackForm
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
                            OR ab.name_author ILIKE %s''', (f'%{form.search_query.data}%', f'%{form.search_query.data}%',))
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
                                WHERE email = %s''', (form.email.data, ))
            cur_email = cur.fetchone()
        if cur_email:
            return redirect(url_for('password', cur_email=cur_email[0]))  # Переход на страницу смены пароля

    return render_template('email.html', form=form)

# Страница смены пароля
@app.route('/new_password/<cur_email>', methods=['GET', 'POST'])
def password(cur_email):
    form = PasswordForm()

    if form.validate_on_submit():
        password_hash = generate_password_hash(form.password.data)  # Хеширование нового пароля
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Обновление пароля в базе данных
                cur.execute('''UPDATE "user" SET password = %s WHERE email = %s''', (password_hash, cur_email,))
                con.commit()

            flash('Пароль успешно изменён', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Ошибка при изменении пароля: {e}', 'danger')
            return redirect(url_for('password'))

    return render_template('password.html', form=form)

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

# Добавление новой книги (доступно только для продавцов)
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
                            VALUES (%s, %s)
                        """, (form.isbn.data, category_name))

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
    flash('Вы вышли из системы', 'info')
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
    num_form = BasketForm()
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

            if num_form.validate_on_submit():  # Проверка формы на корректность
                cur.execute('''SELECT * FROM user_books
                            WHERE login = %s AND isbn = %s''', (current_user.login, isbn, ))
                exist = cur.fetchone()
                if not exist:
                    cur.execute('''INSERT INTO user_books (login, isbn)
                                VALUES (%s, %s)''', (current_user.login, isbn, ))
                    flash(f'Книга забронирована', 'success')
                    return redirect(url_for('book_detail', isbn=isbn))  # Перезагрузка страницы
                else:
                    flash(f'Книга уже забронирована', 'danger')
                    return redirect(url_for('book_detail', isbn=isbn))
            if book:
                # Отображение информации о книге
                return render_template('book_detail.html', book=book, author=author, form=num_form)
            else:
                flash('Книга не найдена', 'danger')
                return redirect(url_for('index'))

    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('index'))

# Удаление книги из каталога (для продавцов)
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
        return redirect(url_for('login'))

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
        return redirect(url_for('login'))

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
        return redirect(url_for('login'))

# Обновление цены книги (для продавцов)
@app.route('/sale', methods=['GET', 'POST'])
def sale():
    sale_form = SaleForm()  # Форма для изменения цены
    isbn = request.args.get('isbn')  # Получение ISBN книги из параметров запроса
    if sale_form.validate_on_submit() and isbn:  # Проверка формы и наличия ISBN
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Обновление цены книги
                cur.execute('''UPDATE book 
                               SET old_price = price, price = %s 
                               WHERE isbn = %s''', (sale_form.new_price.data, isbn))
            flash('Цена успешно обновлена!', 'success')
            return redirect(url_for('book_detail', isbn=isbn))
        except Exception as e:
            flash(f'Ошибка при обновлении цены: {str(e)}', 'danger')
            return redirect(url_for('sale', isbn=isbn))

    # Получение имени книги для отображения
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        cur.execute('''SELECT name FROM book WHERE isbn = %s''', (isbn,))
        book_name = cur.fetchone()
    return render_template('sale.html', form=sale_form, name=book_name[0])

# Поиск книги для обновления цены
@app.route('/search_for_sale', methods=['GET', 'POST'])
def search_for_sale():
    search_form = SearchFrom()  # Форма для поиска книги
    if search_form.validate_on_submit():  # Проверка формы
        try:
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Поиск книги по ISBN
                cur.execute('''SELECT * FROM book WHERE isbn = %s''', (search_form.isbn.data,))
                book = cur.fetchone()
                if book:
                    return redirect(url_for('sale', isbn=search_form.isbn.data))
                else:
                    flash('Книга не найдена по этому ISBN', 'danger')
                    return redirect(url_for('search_for_sale'))
        except Exception as e:
            flash(f'Ошибка: {str(e)}', 'danger')
            return redirect(url_for('search_for_sale'))

    return render_template('search_for_sale.html', form=search_form)
# Просмотр списка адресов пользователя
@app.route('/address')
def address():
    try:
        # Подключение к базе данных для получения адресов текущего пользователя
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение адресов, связанных с логином текущего пользователя
            cur.execute('''SELECT name_address FROM address WHERE login = %s''', (current_user.login,))
            addresses = cur.fetchall()
            if addresses:
                # Если адреса найдены, отображаем их на странице
                return render_template('address.html', addresses=addresses)
            else:
                # Если адресов нет, выводим сообщение
                flash('Адреса не найдены.', 'info')
                return render_template('address.html', addresses=[])
    except Exception as e:
        # В случае ошибки возвращаем пользователя на страницу профиля
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('profile'))

# Добавление нового адреса
@app.route('/add_address', methods=['GET', 'POST'])
def add_address():
    form = AddressForm()  # Создаем объект формы для добавления адреса
    if form.validate_on_submit():  # Проверяем, была ли форма корректно заполнена
        # Формируем строку адреса из данных формы
        address_str = f'Г. {form.city.data}, ул. {form.street.data}, д. {form.home.data}'
        if form.flat.data:  # Если указана квартира, добавляем её к строке
            address_str = f'{address_str}, кв. {form.flat.data}'
        try:
            # Подключение к базе данных для сохранения нового адреса
            with psycopg.connect(
                    host=app.config['DB_SERVER'],
                    user=app.config['DB_USER'],
                    port=app.config['DB_PORT'],
                    password=app.config['DB_PASSWORD'],
                    dbname=app.config['DB_NAME']
            ) as con:
                cur = con.cursor()
                # Вставка нового адреса в таблицу "address"
                cur.execute('''INSERT INTO address (name_address, login)
                               VALUES (%s, %s)''', (address_str, current_user.login,))

            flash('Адрес добавлен успешно', 'success')
            return redirect(url_for('address'))  # Перенаправление на страницу адресов
        except Exception as e:
            # В случае ошибки возвращаем пользователя на страницу профиля
            flash(f'Ошибка: {str(e)}', 'danger')
            return redirect(url_for('profile'))
    return render_template('add_address.html', form=form)

# Просмотр корзины пользователя
@app.route('/basket')
def basket():
    status = "Не подтвержден"
    try:
        # Подключение к базе данных для получения содержимого корзины
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получение данных о книгах в корзине текущего пользователя
            cur.execute('''SELECT b.name, b.isbn, a.name_author 
                                FROM book b
                                JOIN user_books bt ON b.isbn = bt.isbn
                                JOIN author_book a ON b.isbn = a.isbn
                                WHERE bt.login = %s AND bt.status = %s''', (current_user.login, status, ))
            books = cur.fetchall()
    except Exception as e:
        # В случае ошибки перенаправляем на главную страницу
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('index'))

    # Отображаем страницу корзины с данными о книгах
    return render_template('basket.html', books=books)

# Удаление книги из корзины
@app.route('/delete_basket/<isbn>', methods=['POST'])
def delete_basket(isbn):
    try:
        # Подключение к базе данных для удаления книги из корзины
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Удаление книги из корзины текущего пользователя по ISBN
            cur.execute('''DELETE FROM user_books 
                           WHERE isbn = %s AND login = %s''', (isbn, current_user.login,))
            flash('Книга удалена', 'success')
            return redirect(url_for('basket'))
    except Exception as e:
        # В случае ошибки возвращаем пользователя в корзину
        flash(f'Ошибка: {str(e)}', 'danger')
        return redirect(url_for('basket'))

# Выбор типа доставки при оформлении заказа
@app.route('/delivery', methods=['GET', 'POST'])
def type_delivery():
    form = OrderForm()  # Создаем объект формы для выбора типа доставки
    if form.validate_on_submit():
        # При успешной отправке формы перенаправляем на страницу оформления заказа
        return redirect(url_for('order', delivery_type=form.type.data))

    # Отображаем форму выбора типа доставки
    return render_template('delivery.html', form=form)

# Оформление заказа
@app.route('/order', methods=['GET', 'POST'])
def order():
    end_price = 0  # Итоговая стоимость заказа
    books = []  # Список книг в заказе
    current_date = datetime.now()
    begin_date = current_date.date()  # Дата начала заказа

    # Проверяем, что пользователь авторизован и имеет роль "Покупатель"
    if current_user.role == 'Покупатель' and current_user.is_authenticated:
        form = OrderForm()

        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            # Получаем данные о книгах в корзине пользователя
            cur.execute('''SELECT b.price, bt.num_book, b.name, b.isbn 
                           FROM book b
                           JOIN basket bt ON b.isbn=bt.isbn
                           WHERE login = %s''', (current_user.login,))
            prices = cur.fetchall()
            for price in prices:
                end_price += (price[0] * price[1])  # Рассчитываем общую стоимость
                books.append([price[2], price[1]])  # Добавляем книгу и количество в список

        if form.validate_on_submit():  # Проверяем, была ли форма корректно заполнена
            try:
                # Подключение к базе данных для оформления заказа
                with psycopg.connect(
                        host=app.config['DB_SERVER'],
                        user=app.config['DB_USER'],
                        port=app.config['DB_PORT'],
                        password=app.config['DB_PASSWORD'],
                        dbname=app.config['DB_NAME']
                ) as con:
                    cur = con.cursor()
                    if form.type.data == 'ПВЗ':  # Если выбран пункт выдачи заказов
                        # Создание заказа с указанием пункта выдачи
                        cur.execute('''INSERT INTO "order" (begin_date, end_price, type_delivery, pvz_dot, login, type_pay)
                                       VALUES (%s, %s, %s, %s, %s, %s)''',
                                    (begin_date, end_price, form.type.data, form.pvz.data, current_user.login, form.pay.data))
                        cur.execute('SELECT CURRVAL(pg_get_serial_sequence(\'"order"\' , \'id\'))')
                        order_number = cur.fetchone()[0]
                    else:
                        # Если доставка на адрес
                        cur.execute('''SELECT id FROM address
                                       WHERE name_address = %s''', (form.addresses.data,))
                        cur_address = cur.fetchone()[0]
                        cur.execute('''INSERT INTO "order" (begin_date, end_price, type_delivery, address_user, login, type_pay)
                                       VALUES (%s, %s, %s, %s, %s, %s)''',
                                    (begin_date, end_price, form.type.data, cur_address, current_user.login, form.pay.data))
                        cur.execute('SELECT CURRVAL(pg_get_serial_sequence(\'"order"\' , \'id\'))')
                        order_number = cur.fetchone()[0]

                    # Удаляем книги из корзины после оформления заказа
                    cur.execute('''DELETE FROM basket WHERE login = %s''', (current_user.login,))
                    for book in prices:
                        # Сохраняем книги в заказе и уменьшаем их количество на складе
                        cur.execute('''INSERT INTO position_order(num_book, isbn, id_order)
                                        VALUES (%s, %s, %s)''', (book[1], book[3], order_number,))
                        cur.execute('''UPDATE book 
                                        SET num_stock = num_stock - %s
                                        WHERE isbn = %s''', (book[1], book[3]))

                    flash('Заказ успешно оформлен!', 'success')
                    return redirect(url_for('index'))  # Перенаправляем на главную страницу
            except Exception as e:
                flash(f'Ошибка: {str(e)}', 'danger')
                return redirect(url_for('basket'))

        # Отображаем страницу оформления заказа
        return render_template('order.html', form=form, end_price=end_price, books=books)
    else:
        flash('Нет доступа!', 'danger')
        return redirect(url_for('index'))

# Отображение списка заказов текущего пользователя
@app.route('/my_orders')
def my_orders():
    status = 'Не подтвержден'
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        # Получение всех заказов текущего пользователя
        cur.execute('''SELECT * FROM user_books ub
                        JOIN book b ON b.isbn = ub.isbn
                        WHERE ub.login = %s and ub.status != %s''', (current_user.login, status, ))
        orders = cur.fetchall()
    # Отображение страницы с заказами
    return render_template('myorders.html', orders=orders)

# Отображение списка всех заказов (для администраторов)
@app.route('/check_orders')
def check_orders():
    none_status = 'Не подтвержден'
    back_status = 'Запрос на возврат'
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        # Получение всех заказов из базы данных
        cur.execute('''SELECT * FROM user_books
                    WHERE status = %s OR status = %s''', (none_status, back_status, ))
        orders = cur.fetchall()
    # Отображение страницы со всеми заказами
    return render_template('myorders.html', orders=orders)

@app.route('/all_orders')
def all_orders():
    with psycopg.connect(
            host=app.config['DB_SERVER'],
            user=app.config['DB_USER'],
            port=app.config['DB_PORT'],
            password=app.config['DB_PASSWORD'],
            dbname=app.config['DB_NAME']
    ) as con:
        cur = con.cursor()
        # Получение всех заказов из базы данных
        cur.execute('''SELECT * FROM user_books''')
        orders = cur.fetchall()
    # Отображение страницы со всеми заказами
    return render_template('myorders.html', orders=orders)

# Детальная информация о конкретном заказе
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
            # Получение данных о заказе
            cur.execute('''SELECT ub.id, b.name, ab.name_author, ub.begin_date, ub.end_date, ub.status, b.isbn FROM user_books ub
                        JOIN book b ON b.isbn = ub.isbn
                        JOIN author_book ab ON ab.isbn = b.isbn
                        WHERE ub.id = %s''', (num,))
            cur_order = cur.fetchone()

        # Отображение страницы с деталями заказа
        return render_template('order_detail.html', order=cur_order)
    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('index'))

# Изменение статуса заказа (для администратора или менеджера)
@app.route('/change_status/<num>', methods=['POST'])
def change_status(num):
    get_status = 'Выдан'
    back_status = 'Запрос на возврат'
    end_status = 'Возвращен'
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
    if form.validate_on_submit():  # Проверка, была ли форма корректно заполнена
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
        if isbn:
            cur.execute('''SELECT f.mark, f.description, f.login, b.name
                        FROM book b 
                        JOIN feedback f ON b.isbn = f.isbn
                        WHERE f.isbn = %s''', (isbn,))
        else:
            cur.execute('''SELECT f.mark, f.description, f.login, b.name
                                    FROM book b 
                                    JOIN feedback f ON b.isbn = f.isbn''')
        feedbacks = cur.fetchall()
    if feedbacks:
        return render_template("feedback.html", feedbacks=feedbacks)
    else:
        flash('Отзывы отсутствуют', 'danger')
        return redirect(url_for('book_detail', isbn=isbn))

