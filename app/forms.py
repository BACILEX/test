from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, DateField, TextAreaField, DecimalField, IntegerField, PasswordField, SubmitField, SelectField, validators
import psycopg
from app import app

class RegistrationForm(FlaskForm):
    login = StringField('Логин', [validators.Length(min=4, max=25)])
    name = StringField('Имя', [validators.Length(min=2, max=25)])
    email = StringField('E-mail', [validators.Length(min=6, max=100), validators.Email()])
    password = PasswordField('Пароль', [validators.InputRequired(),
                                        validators.Length(min=6, max=100),
                                        validators.EqualTo('confirm', message='Пароли должны совпадать')])
    confirm  = PasswordField('Повторите пароль')
    submit = SubmitField('Зарегистрироваться')

class EditUserForm(FlaskForm):
    name = StringField('Имя', [validators.Length(min=2, max=25)])
    email = StringField('E-mail', [validators.Length(min=6, max=100), validators.Email()])
    submit = SubmitField('Сохранить')

class LoginForm(FlaskForm):
    login = StringField('Логин', [validators.InputRequired()])
    password = PasswordField('Пароль', [validators.InputRequired()])
    submit = SubmitField('Войти')

class EmailForm(FlaskForm):
    email = StringField('E-mail', [validators.Length(min=6, max=100), validators.Email()])
    submit = SubmitField('Далее')

class PasswordForm(FlaskForm):
    email = StringField('E-mail', [validators.Length(min=6, max=100), validators.Email()])
    password = PasswordField('Пароль', [validators.InputRequired(),
                                        validators.Length(min=6, max=100),
                                        validators.EqualTo('confirm', message='Пароли должны совпадать')])
    confirm = PasswordField('Повторите пароль')
    submit = SubmitField('Сохранить')

class AddBookForm(FlaskForm):
    name = StringField('Название книги', [validators.Length(min=4, max=25)])
    author_name = StringField('Автор', [validators.Length(min=4, max=25)])
    num_stock = IntegerField('Количество', [validators.NumberRange(min=1)])
    isbn = IntegerField('ISBN', [validators.NumberRange(min=1)])
    publication_year = IntegerField('Год издательства:', [validators.NumberRange(min=1900)])
    name_publish = StringField('Издательство', [validators.Length(min=4, max=25)])
    description = TextAreaField('Описание', [validators.Length(min=1, max=500)])
    categories = SelectMultipleField('Категории', coerce=str, validators=[validators.DataRequired()])
    submit = SubmitField('Добавить книгу')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Получаем все категории из базы данных для SelectMultipleField
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            cur.execute('SELECT name FROM category')
            categories = cur.fetchall()

        # Устанавливаем выбор категорий
        self.categories.choices = [category[0] for category in categories]

class SaleForm(FlaskForm):
    new_price = IntegerField('Цена', [validators.NumberRange(min=1)])
    submit = SubmitField('Сохранить')

class SearchFrom(FlaskForm):
    isbn = StringField('ISBN', [validators.Length(min=1, max=10)])
    submit = SubmitField('Найти')

class AddressForm(FlaskForm):
    city = StringField('Город', [validators.Length(min=3, max=25)])
    street = StringField('Улица', [validators.Length(min=3, max=25)])
    home = StringField('Дом', [validators.Length(min=1, max=3)])
    flat = StringField('Квартира', [validators.Length(min=0, max=3)])
    submit = SubmitField('Сохранить')

class BasketForm(FlaskForm):
    submit = SubmitField('Создать бронь книги')

class OrderForm(FlaskForm):
    type = SelectField('Способ доставки', choices=[('ПВЗ', 'ПВЗ'), ('До квартиры', 'До квартиры')],validators=[validators.DataRequired()])
    addresses = SelectField('Адрес', coerce=str, choices=[('', 'Выберите адрес')])
    pvz = SelectField('Адрес пункта выдачи', coerce=str, choices=[('', 'Выберите адрес')])
    pay = SelectField('Способ оплаты', coerce=str, validators=[validators.DataRequired()])
    submit = SubmitField('Оформить')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with psycopg.connect(
                host=app.config['DB_SERVER'],
                user=app.config['DB_USER'],
                port=app.config['DB_PORT'],
                password=app.config['DB_PASSWORD'],
                dbname=app.config['DB_NAME']
        ) as con:
            cur = con.cursor()
            cur.execute('SELECT * FROM pay_type')
            types = cur.fetchall()
            self.pay.choices = [type[0] for type in types]

            cur.execute('SELECT * FROM address')
            names = cur.fetchall()
            self.addresses.choices = [('')] + [address[1] for address in names]

            cur.execute('SELECT * FROM pvz')
            names = cur.fetchall()
            self.pvz.choices = [('')] + [address[0] for address in names]

class SearchForm(FlaskForm):
    search_query = StringField('', [validators.Optional(), validators.Length(min=1)], render_kw={"placeholder": "Введите название или автора"})
    submit = SubmitField('Искать')

class FeedbackForm(FlaskForm):
    mark = IntegerField('Оценка', [validators.NumberRange(min=1, max=5)])
    description = TextAreaField('Отзыв', [validators.Length(min=1, max=500)])
    submit = SubmitField('Сохранить')