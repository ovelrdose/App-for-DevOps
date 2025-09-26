from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime

# Загрузка .env файла вручную
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        print(f"Loading environment from: {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env_file()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Универсальные пути для Docker
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Пути внутри контейнера (стандартные для Linux)
DB_PATH = os.environ.get('DB_PATH', '/app/data/cats.db')
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    """Create database connection with row factory"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database and create necessary directories"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            title TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized at: {DB_PATH}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
def get_all_cats():
    """Get all cats from database"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM cats ORDER BY upload_date DESC')
    cats = c.fetchall()
    conn.close()
    return cats

def get_cat_by_id(cat_id):
    """Get cat by ID"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM cats WHERE id = ?', (cat_id,))
    cat = c.fetchone()
    conn.close()
    return cat

def save_cat_info(filename, original_name, title):
    """Save cat info to database"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO cats (filename, original_name, title) VALUES (?, ?, ?)', 
              (filename, original_name, title))
    conn.commit()
    conn.close()

def delete_cat(cat_id):
    """Delete cat from database and filesystem"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT filename FROM cats WHERE id = ?', (cat_id,))
    result = c.fetchone()
    
    if result:
        filename = result['filename']
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Deleted file: {filepath}")
        
        c.execute('DELETE FROM cats WHERE id = ?', (cat_id,))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def resize_image(image_path, max_size=(1000, 800)):
    """Resize image for optimization"""
    try:
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail(max_size)
            img.save(image_path, optimize=True, quality=85)
            print(f"Image resized: {image_path}")
    except Exception as e:
        print(f"Error resizing image: {e}")

@app.route('/')
def index():
    """Main page - display all cat pictures"""
    try:
        cats = get_all_cats()
        return render_template('index.html', cats=cats)
    except Exception as e:
        flash('Ошибка загрузки данных из базы')
        print(f"Database error: {e}")
        return render_template('index.html', cats=[])

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Page for uploading new pictures"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файл не выбран')
            return redirect(request.url)
        
        file = request.files['file']
        title = request.form.get('title', '').strip()
        
        if not title:
            flash('Введите заголовок для котика')
            return redirect(request.url)
        
        if file.filename == '':
            flash('Файл не выбран')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(filepath)
                resize_image(filepath)
                save_cat_info(filename, file.filename, title)
                
                flash('Картинка успешно загружена!')
                return redirect(url_for('index'))
                
            except Exception as e:
                flash('Ошибка при сохранении файла')
                print(f"Upload error: {e}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                
        else:
            flash('Разрешены только файлы: png, jpg, jpeg, gif')
    
    return render_template('upload.html')

@app.route('/manage')
def manage():
    """Cat management page"""
    try:
        cats = get_all_cats()
        return render_template('manage.html', cats=cats)
    except Exception as e:
        flash('Ошибка загрузки данных из базы')
        print(f"Database error: {e}")
        return render_template('manage.html', cats=[])

@app.route('/delete/<int:cat_id>', methods=['POST'])
def delete_cat_route(cat_id):
    """Delete cat route"""
    try:
        if delete_cat(cat_id):
            flash('Котик успешно удален!')
        else:
            flash('Котик не найден')
    except Exception as e:
        flash('Ошибка при удалении котика')
        print(f"Delete error: {e}")
    
    return redirect(url_for('manage'))

@app.errorhandler(413)
def too_large(e):
    flash('Файл слишком большой. Максимальный размер: 2MB')
    return redirect(request.url)

# Initialize database
init_db()

if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')  # По умолчанию localhost на Windows
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    
    print(f"Starting Flask app on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Database path: {DB_PATH}")
    print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Base directory: {BASE_DIR}")
    
    app.run(debug=debug, host=host, port=port)