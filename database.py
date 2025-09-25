import sqlite3
import os

def init_db():
    conn = sqlite3.connect('cats.db')
    c = conn.cursor()
    
    # Создаем таблицу для хранения информации о картинках
    c.execute('''
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Создаем папку для загрузок, если ее нет
    os.makedirs('static/uploads', exist_ok=True)

def get_all_cats():
    conn = sqlite3.connect('cats.db')
    c = conn.cursor()
    c.execute('SELECT * FROM cats ORDER BY upload_date DESC')
    cats = c.fetchall()
    conn.close()
    return cats

def save_cat_info(filename, original_name):
    conn = sqlite3.connect('cats.db')
    c = conn.cursor()
    c.execute('INSERT INTO cats (filename, original_name) VALUES (?, ?)', 
              (filename, original_name))
    conn.commit()
    conn.close()