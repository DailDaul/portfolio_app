import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', '080746079b49269016739c7c1e61eaf7e01b5442e30c15b8871f483103791bec')
    
    #PostgreSQL (для production) с поддержкой переменных окружения
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:281205@localhost:5432/portfolio_db')
    
    #Используем PostgreSQL, если есть DATABASE_URL, иначе SQLite для разработки
    if DATABASE_URL and DATABASE_URL.startswith('postgresql'):
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        #Для локальной разработки без PostgreSQL
        SQLALCHEMY_DATABASE_URI = 'sqlite:///portfolio.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    ALLOWED_FILE_EXTENSIONS = {
    'py', 'js', 'html', 'css', 'json', 'txt', 'md', 'sql', 
    'java', 'cpp', 'c', 'h', 'rb', 'go', 'rs', 'php', 'ts'
    }
    
    #Настройки для PostgreSQL (опционально)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }