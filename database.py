import sqlite3
from datetime import date

DB_PATH = "library.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            author      TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'Reading',
            date_added  TEXT    NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def add_book(title, author, status="Archived"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO books (title, author, status, date_added)
        VALUES (?, ?, ?, ?)
    """, (title, author, status, str(date.today())))

    conn.commit()
    conn.close()

def get_all_books():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books ORDER BY date_added DESC")
    books = cursor.fetchall()

    conn.close()
    return books

def update_status(book_id, new_status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE books SET status = ? WHERE id = ?
    """, (new_status, book_id))

    conn.commit()
    conn.close()

def delete_book(book_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))

    conn.commit()
    conn.close()


