import os
import cv2
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import Flask, render_template, redirect, url_for, flash, request, abort, session, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import text
from models import db, User, Project, Image, Review, View, Link, ProjectFile, CodeBlock

from config import Config
from forms import RegistrationForm, LoginForm, ProjectForm, ReviewForm, ProfileForm

# Создание приложения
app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'

# Создание папки для загрузок
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


# Регистрация для шрифтов
font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fonts')
font_path_regular = os.path.join(font_dir, 'arialmt.ttf')
font_path_bold = os.path.join(font_dir, 'arial_bolditalicmt.ttf')

FONT_NORMAL = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'

if os.path.exists(font_path_regular):
    pdfmetrics.registerFont(TTFont('Arial', font_path_regular))
    FONT_NORMAL = 'Arial'

if os.path.exists(font_path_bold):
    pdfmetrics.registerFont(TTFont('Arial-Bold', font_path_bold))
    FONT_BOLD = 'Arial-Bold'

# Helpers

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def author_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['author', 'admin']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def allowed_video(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4', 'webm', 'mov'}

def get_author_rating(user_id):
    projects = Project.query.filter_by(author_id=user_id).all()
    if not projects:
        return 0
    ratings = [p.rating for p in projects if p.rating > 0]
    return round(sum(ratings) / len(ratings), 2) if ratings else 0

def detect_link_icon(url):
    if 'github.com' in url:
        return 'github'
    elif 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'behance.net' in url:
        return 'behance'
    elif 'linkedin.com' in url:
        return 'linkedin'
    elif 't.me' in url or 'telegram' in url:
        return 'telegram'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    else:
        return 'globe'

def get_file_language(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    languages = {
        'py': 'python',
        'js': 'javascript',
        'html': 'html',
        'css': 'css',
        'json': 'json',
        'sql': 'sql',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
        'rb': 'ruby',
        'go': 'go',
        'rs': 'rust',
        'php': 'php',
        'ts': 'typescript',
        'txt': 'text',
        'md': 'markdown'
    }
    return languages.get(ext, 'text')

def get_project_thumbnail(project):
    if project.thumbnail_filename:
        return project.thumbnail_filename
    if project.images and len(project.images) > 0:
        return project.images[0].filename
    return None

def extract_video_thumbnail(video_path, thumbnail_path, time_sec=1):
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False
        cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(thumbnail_path, frame)
            cap.release()
            return True
        cap.release()
        return False
    except Exception:
        return False

def save_project_files(project, files):
    for idx, file in enumerate(files):
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext not in Config.ALLOWED_FILE_EXTENSIONS:
                continue
            
            original_filename = file.filename
            filename = secure_filename(f"project_{project.id}_{idx}_{original_filename}")
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            project_file = ProjectFile(
                filename=filename,
                original_filename=original_filename,
                file_path=filepath,
                file_size=os.path.getsize(filepath),
                language=get_file_language(original_filename),
                project_id=project.id,
                sort_order=idx
            )
            db.session.add(project_file)

@app.context_processor
def utility_processor():
    return {
        'get_project_thumbnail': get_project_thumbnail
    }

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 9  # 9 проектов на страницу (3x3 сетка)
    
    projects = Project.query.order_by(Project.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('index.html', projects=projects)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Пользователь с таким логином уже существует', 'danger')
            return render_template('register.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            sphere=form.sphere.data if form.sphere.data else None,
            role='author'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешно завершена! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user:
            user = User.query.filter_by(email=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверный логин или пароль', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

# Профиль автора

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    projects = Project.query.filter_by(author_id=user_id).order_by(Project.created_at.desc()).all()
    author_rating = get_author_rating(user_id)
    total_views = sum(p.views_count for p in projects)
    
    return render_template('profile.html', user=user, projects=projects, 
                           author_rating=author_rating, total_views=total_views)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        current_user.sphere = form.sphere.data
        
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and allowed_file(file.filename):
                if current_user.avatar_filename:
                    old_path = os.path.join(Config.UPLOAD_FOLDER, current_user.avatar_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(f"user_{current_user.id}_{file.filename}")
                file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
                current_user.avatar_filename = filename
        
        db.session.commit()
        flash('Профиль успешно обновлён!', 'success')
        return redirect(url_for('profile', user_id=current_user.id))
    
    return render_template('edit_profile.html', form=form)

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect(url_for('profile', user_id=current_user.id))
    
    file = request.files['avatar']
    if file and allowed_file(file.filename):
        filename = secure_filename(f"user_{current_user.id}_{file.filename}")
        file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        current_user.avatar_filename = filename
        db.session.commit()
        flash('Аватар успешно обновлён!', 'success')
    else:
        flash('Недопустимый формат файла', 'danger')
    
    return redirect(url_for('profile', user_id=current_user.id))

# CRUD операции

@app.route('/project/new', methods=['GET', 'POST'])
@author_required
def create_project():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            title=form.title.data,
            description=form.description.data,
            author_id=current_user.id,
            content_type=form.content_type.data,
            video_link=form.video_link.data,
        )
        db.session.add(project)
        db.session.flush()
        
        # Обработка ссылок
        for key, value in request.form.items():
            if key.startswith('link_url_'):
                idx = key.split('_')[-1]
                title_key = f'link_title_{idx}'
                url = value
                title = request.form.get(title_key, '')
                if url:
                    icon = detect_link_icon(url)
                    link = Link(
                        url=url,
                        title=title,
                        icon=icon,
                        project_id=project.id
                    )
                    db.session.add(link)
        
        # Обработка изображений
        files = request.files.getlist('images')
        for idx, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(f"project_{project.id}_{idx}_{file.filename}")
                file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
                image = Image(filename=filename, project_id=project.id, sort_order=idx)
                db.session.add(image)
        
        # Обработка видеофайла и генерация обложки
        video_file = request.files.get('video_file')
        if video_file and allowed_video(video_file.filename):
            filename = secure_filename(f"video_{project.id}_{video_file.filename}")
            video_file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
            project.video_file = filename
            
            thumbnail_filename = f"thumb_{project.id}_{video_file.filename}.jpg"
            thumbnail_path = os.path.join(Config.UPLOAD_FOLDER, thumbnail_filename)
            video_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            
            if extract_video_thumbnail(video_path, thumbnail_path):
                project.thumbnail_filename = thumbnail_filename
        
        if not project.thumbnail_filename and project.images and len(project.images) > 0:
            project.thumbnail_filename = project.images[0].filename
        
        project_files = request.files.getlist('project_files')
        if project_files and project_files[0].filename:
            save_project_files(project, project_files)
        
        db.session.commit()
        flash('Проект успешно создан!', 'success')
        return redirect(url_for('profile', user_id=current_user.id))
    
    return render_template('edit_project.html', form=form, title='Создание проекта')

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    if project.author_id != current_user.id and current_user.role != 'admin':
        abort(403)
    
    form = ProjectForm(obj=project)
    
    if form.validate_on_submit():
        project.title = form.title.data
        project.description = form.description.data
        project.content_type = form.content_type.data
        project.video_link = form.video_link.data
        project.updated_at = datetime.utcnow()
        
        # Удаляем старые ссылки
        Link.query.filter_by(project_id=project.id).delete()
        
        # Добавляем новые ссылки
        for key, value in request.form.items():
            if key.startswith('link_url_'):
                idx = key.split('_')[-1]
                title_key = f'link_title_{idx}'
                url = value
                title = request.form.get(title_key, '')
                if url:
                    icon = detect_link_icon(url)
                    link = Link(
                        url=url,
                        title=title,
                        icon=icon,
                        project_id=project.id
                    )
                    db.session.add(link)
        
        # Обработка изображений
        files = request.files.getlist('images')
        for idx, file in enumerate(files):
            if file and allowed_file(file.filename):
                filename = secure_filename(f"project_{project.id}_{idx}_{file.filename}")
                file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
                image = Image(filename=filename, project_id=project.id, sort_order=idx)
                db.session.add(image)
        
        # Обработка обложки
        if 'remove_thumbnail' in request.form:
            if project.thumbnail_filename:
                old_path = os.path.join(Config.UPLOAD_FOLDER, project.thumbnail_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
                project.thumbnail_filename = None
        
        thumbnail_file = request.files.get('thumbnail')
        if thumbnail_file and allowed_file(thumbnail_file.filename):
            if project.thumbnail_filename:
                old_path = os.path.join(Config.UPLOAD_FOLDER, project.thumbnail_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(f"thumb_{project.id}_{thumbnail_file.filename}")
            thumbnail_file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
            project.thumbnail_filename = filename
        
        # Обработка видео
        video_file = request.files.get('video_file')
        if video_file and allowed_video(video_file.filename):
            if project.video_file:
                old_path = os.path.join(Config.UPLOAD_FOLDER, project.video_file)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(f"video_{project.id}_{video_file.filename}")
            video_file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
            project.video_file = filename
        
        # Обработка блоков кода
        CodeBlock.query.filter_by(project_id=project.id).delete()
        
        code_titles = []
        code_descriptions = []
        code_languages = []
        code_contents = []
        
        for key, value in request.form.items():
            if key.startswith('code_title_'):
                code_titles.append(value)
            elif key.startswith('code_description_'):
                code_descriptions.append(value)
            elif key.startswith('code_language_'):
                code_languages.append(value)
            elif key.startswith('code_content_'):
                code_contents.append(value)
        
        for i in range(len(code_contents)):
            if code_contents[i] and code_contents[i].strip():
                code_block = CodeBlock(
                    title=code_titles[i] if i < len(code_titles) else '',
                    description=code_descriptions[i] if i < len(code_descriptions) else '',
                    code=code_contents[i],
                    language=code_languages[i] if i < len(code_languages) else 'python',
                    project_id=project.id,
                    sort_order=i
                )
                db.session.add(code_block)
        
        # Обработка файлов проекта
        if 'clear_files' in request.form:
            for pf in project.files:
                if os.path.exists(pf.file_path):
                    os.remove(pf.file_path)
            ProjectFile.query.filter_by(project_id=project.id).delete()
        
        project_files = request.files.getlist('project_files')
        if project_files and project_files[0].filename:
            save_project_files(project, project_files)
        
        db.session.commit()
        flash('Проект успешно обновлён!', 'success')
        return redirect(url_for('view_project', project_id=project.id))
    
    return render_template('edit_project.html', form=form, project=project, title='Редактирование проекта')

@app.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    if project.author_id != current_user.id and current_user.role != 'admin':
        abort(403)
    
    for image in project.images:
        path = os.path.join(Config.UPLOAD_FOLDER, image.filename)
        if os.path.exists(path):
            os.remove(path)
    if project.video_file:
        path = os.path.join(Config.UPLOAD_FOLDER, project.video_file)
        if os.path.exists(path):
            os.remove(path)
    for pf in project.files:
        if os.path.exists(pf.file_path):
            os.remove(pf.file_path)
    
    db.session.delete(project)
    db.session.commit()
    flash('Проект удалён', 'success')
    return redirect(url_for('profile', user_id=current_user.id))

@app.route('/project/<int:project_id>', methods=['GET', 'POST'])
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    visitor_ip = request.remote_addr
    view = View(project_id=project.id, visitor_ip=visitor_ip, viewed_at=datetime.utcnow())
    db.session.add(view)
    project.views_count += 1
    db.session.commit()

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            project_id=project.id,
            rating=form.rating.data,
            comment=form.comment.data,
            visitor_name=form.name.data if form.name.data else 'Аноним',
            visitor_email=form.email.data,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(review)
        db.session.commit()
        
        project.update_rating()
        
        flash('Отзыв успешно добавлен! Спасибо за оценку.', 'success')
        return redirect(url_for('view_project', project_id=project.id))
    
    reviews = Review.query.filter_by(project_id=project.id).order_by(Review.created_at.desc()).all()
    
    return render_template('project.html', project=project, reviews=reviews, form=form)

# Проектные файлы

@app.route('/get_file_content/<int:file_id>')
def get_file_content(file_id):
    file = ProjectFile.query.get_or_404(file_id)
    try:
        with open(file.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Не удалось прочитать файл: {e}"

@app.route('/download_file/<int:file_id>')
def download_file(file_id):
    file = ProjectFile.query.get_or_404(file_id)
    return send_file(
        file.file_path,
        as_attachment=True,
        download_name=file.original_filename
    )

@app.route('/admin/file/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file(file_id):
    file = ProjectFile.query.get_or_404(file_id)
    project = Project.query.get(file.project_id)
    
    if current_user.id != project.author_id and current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Нет прав'}), 403
    
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    db.session.delete(file)
    db.session.commit()
    
    return jsonify({'success': True})

# Админка

@app.route('/admin')
@admin_required
def admin_panel():
    users = User.query.all()
    projects = Project.query.all()
    reviews = Review.query.all()
    return render_template('admin.html', users=users, projects=projects, reviews=reviews)

@app.route('/admin/user/<int:user_id>/toggle_block', methods=['POST'])
@admin_required
def toggle_block_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Нельзя заблокировать самого себя', 'danger')
        return redirect(url_for('admin_panel'))
    
    user.is_active = not user.is_active
    db.session.commit()
    flash(f'Пользователь {user.username} {"заблокирован" if not user.is_active else "разблокирован"}', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/user/<int:user_id>/change_role', methods=['POST'])
@admin_required
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if new_role in ['visitor', 'author', 'admin']:
        user.role = new_role
        db.session.commit()
        flash(f'Роль пользователя {user.username} изменена на {new_role}', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/project/<int:project_id>/delete', methods=['POST'])
@admin_required
def admin_delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    for image in project.images:
        path = os.path.join(Config.UPLOAD_FOLDER, image.filename)
        if os.path.exists(path):
            os.remove(path)
    for pf in project.files:
        if os.path.exists(pf.file_path):
            os.remove(pf.file_path)
    if project.video_file:
        path = os.path.join(Config.UPLOAD_FOLDER, project.video_file)
        if os.path.exists(path):
            os.remove(path)
    
    db.session.delete(project)
    db.session.commit()
    flash('Проект удалён', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/review/<int:review_id>/delete', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    project_id = review.project_id
    db.session.delete(review)
    db.session.commit()
    
    project = Project.query.get(project_id)
    if project:
        project.update_rating()
    
    flash('Отзыв удалён', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/image/<int:image_id>/delete', methods=['POST'])
@login_required
def delete_image(image_id):
    image = Image.query.get_or_404(image_id)
    project = Project.query.get(image.project_id)
    
    if current_user.id != project.author_id and current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Нет прав'}), 403
    
    filepath = os.path.join(Config.UPLOAD_FOLDER, image.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    db.session.delete(image)
    db.session.commit()
    
    return jsonify({'success': True})

# Экспорт PDF

@app.route('/export_pdf/<int:user_id>')
@login_required
def export_pdf(user_id):
    if current_user.id != user_id and current_user.role != 'admin':
        abort(403)
    
    user = User.query.get_or_404(user_id)
    projects = Project.query.filter_by(author_id=user_id).all()
    
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    pdf.setFont(FONT_BOLD, 20)
    pdf.drawString(50, height - 50, f"Portfolio: {user.username}")
    
    pdf.setFont(FONT_NORMAL, 12)
    pdf.drawString(50, height - 80, f"Email: {user.email}")
    pdf.drawString(50, height - 100, f"Sphere: {user.sphere or 'Not specified'}")
    
    if user.bio:
        pdf.drawString(50, height - 120, f"About: {user.bio[:100]}...")
    
    total_views = sum(p.views_count for p in projects)
    author_rating = get_author_rating(user_id)
    
    pdf.setFont(FONT_BOLD, 14)
    pdf.drawString(50, height - 160, "Statistics:")
    pdf.setFont(FONT_NORMAL, 12)
    pdf.drawString(50, height - 180, f"• Total projects: {len(projects)}")
    pdf.drawString(50, height - 200, f"• Total views: {total_views}")
    pdf.drawString(50, height - 220, f"• Author rating: {author_rating}")
    
    y = height - 270
    pdf.setFont(FONT_BOLD, 14)
    pdf.drawString(50, y, "Projects:")
    y -= 30
    
    for project in projects:
        if y < 100:
            pdf.showPage()
            y = height - 50
            pdf.setFont(FONT_BOLD, 14)
            pdf.drawString(50, y, "Projects (continued):")
            y -= 30
        
        pdf.setFont(FONT_BOLD, 12)
        pdf.drawString(50, y, f"• {project.title}")
        y -= 18
        pdf.setFont(FONT_NORMAL, 10)
        
        desc = project.description[:150] + "..." if len(project.description) > 150 else project.description
        pdf.drawString(50, y, f"  {desc}")
        y -= 14
        pdf.drawString(50, y, f"  Rating: {project.rating} | Views: {project.views_count}")
        y -= 25
    
    pdf.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{user.username}_portfolio.pdf",
        mimetype='application/pdf'
    )

# Инициализация БД
with app.app_context():
    db.create_all()
    
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            role='admin',
            sphere='other',
            bio='Администратор системы'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.commit()
        print('Создан администратор: admin / admin123')

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
