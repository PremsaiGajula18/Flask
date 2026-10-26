import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(INSTANCE_DIR, 'movie_night.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'movie-night-secret-key-prod-99482914-secure')
    DATABASE = DATABASE_PATH
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
