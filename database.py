import sqlite3
import json
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

def add_book(title, author, status="None"):
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

def update_book(book_id, title, author, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE books SET title = ?, author = ?, status = ? WHERE id = ?
    """, (title, author, status, book_id))

    conn.commit()
    conn.close()

def delete_book(book_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))

    conn.commit()
    conn.close()

def export_library(file_path):
    """Write the whole library out to a .json file.

    Returns the number of books exported. The 'id' column is left out on
    purpose — ids are auto-assigned, so an import shouldn't try to keep them.
    """
    books = get_all_books()
    data = [
        {
            "title": book["title"],
            "author": book["author"],
            "status": book["status"],
            "date_added": book["date_added"],
        }
        for book in books
    ]

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return len(data)

def import_library(file_path):
    """Read a .json file and add its entries into library.db.

    The database/table is created automatically if it doesn't exist yet, so
    importing into a fresh setup works. Each entry is appended (no ids are
    reused). Entries missing a title or author are skipped. Returns the number
    of books actually imported.
    """
    initialize_database()  # ensure the table exists before inserting

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # accept either a bare list or an object with a "books" key
    if isinstance(data, dict):
        data = data.get("books", [])

    if not isinstance(data, list):
        raise ValueError("JSON file must contain a list of book entries.")

    conn = get_connection()
    cursor = conn.cursor()

    imported = 0
    for entry in data:
        if not isinstance(entry, dict):
            continue

        title = (entry.get("title") or "").strip()
        author = (entry.get("author") or "").strip()
        # required fields — skip anything that doesn't have both
        if not title or not author:
            continue

        status = (entry.get("status") or "None").strip() or "None"
        date_added = (entry.get("date_added") or "").strip() or str(date.today())

        cursor.execute("""
            INSERT INTO books (title, author, status, date_added)
            VALUES (?, ?, ?, ?)
        """, (title, author, status, date_added))
        imported += 1

    conn.commit()
    conn.close()

    return imported

