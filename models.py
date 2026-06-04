from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='visitor')
    sphere = db.Column(db.String(30))
    avatar_filename = db.Column(db.String(200))
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_author(self):
        return self.role == 'author'

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    content_type = db.Column(db.String(50), default='mixed')
    video_file = db.Column(db.String(300))
    video_link = db.Column(db.String(300))
    thumbnail_filename = db.Column(db.String(300))
    
    views_count = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    author = db.relationship('User', backref=db.backref('projects', lazy=True))
    images = db.relationship('Image', backref='project', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='project', cascade='all, delete-orphan')
    links = db.relationship('Link', backref='project', cascade='all, delete-orphan')
    views = db.relationship('View', backref='project', cascade='all, delete-orphan')
    files = db.relationship('ProjectFile', backref='project', cascade='all, delete-orphan')
    code_blocks = db.relationship('CodeBlock', backref='project', cascade='all, delete-orphan')
    
    def update_rating(self):
        from sqlalchemy import func
        avg = db.session.query(func.avg(Review.rating)).filter_by(project_id=self.id).scalar()
        self.rating = round(avg, 2) if avg else 0
        db.session.commit()

class Image(db.Model):
    __tablename__ = 'images'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sort_order = db.Column(db.Integer, default=0)

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    visitor_name = db.Column(db.String(80))
    visitor_email = db.Column(db.String(120))
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='reviews')

class View(db.Model):
    __tablename__ = 'views'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    visitor_ip = db.Column(db.String(45))
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)

class Link(db.Model):
    __tablename__ = 'links'
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200))
    icon = db.Column(db.String(50), default='globe')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sort_order = db.Column(db.Integer, default=0)

class ProjectFile(db.Model):
    __tablename__ = 'project_files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    original_filename = db.Column(db.String(300), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0)
    language = db.Column(db.String(50))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CodeBlock(db.Model):
    __tablename__ = 'code_blocks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), default='python')
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sort_order = db.Column(db.Integer, default=0)