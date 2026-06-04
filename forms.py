from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange

class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтверждение', validators=[DataRequired(), EqualTo('password')])
    sphere = SelectField('Сфера деятельности', choices=[
        ('', 'Выберите сферу'),
        ('designer', 'Дизайнер'),
        ('developer', 'Разработчик'),
        ('actor', 'Актёр'),
        ('videographer', 'Видеограф'),
        ('photographer', 'Фотограф'),
        ('other', 'Другое')
    ])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Логин или Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class ProjectForm(FlaskForm):
    title = StringField('Название проекта', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    
    content_type = SelectField('Тип контента', choices=[
        ('text', 'Текст'),
        ('images', 'Галерея изображений'),
        ('video', 'Видео'),
        ('code', 'Код (несколько листингов)'),
        ('mixed', 'Смешанный (всё вместе)')
    ], default='mixed')
    
    # Видео
    video_file = FileField('Видеофайл (MP4, WebM)', validators=[FileAllowed(['mp4', 'webm', 'mov'])])
    video_link = StringField('Ссылка на видео (YouTube/Vimeo)', validators=[Length(max=300)])
    
    # Изображения
    images = FileField('Изображения', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])], render_kw={'multiple': True})
    
    # Файлы проекта
    project_files = FileField('Файлы проекта', validators=[FileAllowed(['py', 'js', 'html', 'css', 'json', 'txt', 'md', 'sql', 'java', 'cpp', 'c', 'rb', 'go', 'rs', 'php', 'ts'])], render_kw={'multiple': True})
    
    submit = SubmitField('Сохранить проект')

class ReviewForm(FlaskForm):
    rating = SelectField('Оценка', choices=[(1, '★'), (2, '★★'), (3, '★★★'), (4, '★★★★'), (5, '★★★★★')], coerce=int)
    comment = TextAreaField('Комментарий', validators=[Length(max=1000)])
    name = StringField('Ваше имя', validators=[Length(max=80)])
    email = StringField('Email', validators=[Email()])
    submit = SubmitField('Отправить отзыв')

class ProfileForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=80)])
    bio = TextAreaField('О себе', validators=[Length(max=500)])
    sphere = SelectField('Сфера деятельности', choices=[
        ('designer', 'Дизайнер'),
        ('developer', 'Разработчик'),
        ('actor', 'Актёр'),
        ('videographer', 'Видеограф'),
        ('photographer', 'Фотограф'),
        ('other', 'Другое')
    ])
    submit = SubmitField('Сохранить изменения')