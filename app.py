from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import sqlite3
import os
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('cats.db')
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
    os.makedirs('static/uploads', exist_ok=True)

# Получить всех котов из БД
def get_all_cats():
    conn = sqlite3.connect('cats.db')
    c = conn.cursor()
    c.execute('SELECT * FROM cats ORDER BY upload_date DESC')
    cats = c.fetchall()
    conn.close()
    return cats

# Получить кота по ID
def get_cat_by_id(cat_id):
    conn = sqlite3.connect('cats.db')
    c = conn.cursor()
    c.execute('SELECT * FROM cats WHERE id = ?', (cat_id,))
    cat = c.fetchone()
    conn.close()
    return cat

# Сохранить информацию о коте в БД
def save_cat_info(filename, original_name, title):
    conn = sqlite3.connect('cats.db')
    c = conn.cursor()
    c.execute('INSERT INTO cats (filename, original_name, title) VALUES (?, ?, ?)', 
              (filename, original_name, title))
    conn.commit()
    conn.close()

# Удалить кота из БД
def delete_cat(cat_id):
    conn = sqlite3.connect('cats.db')
    c = conn.cursor()
    
    # Сначала получаем информацию о файле
    c.execute('SELECT filename FROM cats WHERE id = ?', (cat_id,))
    result = c.fetchone()
    
    if result:
        filename = result[0]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Удаляем файл картинки
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Удаляем запись из БД
        c.execute('DELETE FROM cats WHERE id = ?', (cat_id,))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def resize_image(image_path, max_size=(1000, 800)):
    """Изменяет размер изображения для оптимизации"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size)
            img.save(image_path)
    except Exception as e:
        print(f"Ошибка при изменении размера: {e}")

@app.route('/')
def index():
    """Главная страница - отображает все картинки котов"""
    cats = get_all_cats()
    return render_template('index.html', cats=cats)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Страница загрузки новых картинок"""
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
            file.save(filepath)
            
            resize_image(filepath)
            save_cat_info(filename, file.filename, title)
            
            flash('Картинка успешно загружена!')
            return redirect(url_for('index'))
        else:
            flash('Разрешены только файлы: png, jpg, jpeg, gif')
    
    return render_template('upload.html')

@app.route('/manage')
def manage():
    """Страница управления котами"""
    cats = get_all_cats()
    return render_template('manage.html', cats=cats)

@app.route('/delete/<int:cat_id>', methods=['POST'])
def delete_cat_route(cat_id):
    """Удаление кота"""
    if delete_cat(cat_id):
        flash('Котик успешно удален!')
    else:
        flash('Ошибка при удалении котика')
    
    return redirect(url_for('manage'))

# Инициализируем БД при запуске приложения
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)