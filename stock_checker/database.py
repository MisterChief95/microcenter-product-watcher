import os
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import json


class Database:
    def __init__(self, db_path=None):
        # Use environment variable if set, otherwise use default
        if db_path is None:
            db_path = os.getenv('DATABASE_PATH', 'products.db')
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def init_database(self):
        """Initialize the database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Products table - deduplicated by URL and store number
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                store_number TEXT NOT NULL,
                title TEXT,
                in_stock BOOLEAN DEFAULT 0,
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(url, store_number)
            )
        ''')

        # User-Product relationship table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_products (
                user_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                notified BOOLEAN DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, product_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')

        # Stock history table for analytics (optional, but useful)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                in_stock BOOLEAN NOT NULL,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')

        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_url ON products(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_store ON products(store_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_products_user ON user_products(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_history_product ON stock_history(product_id)')

        conn.commit()
        conn.close()

    def add_or_get_user(self, user_id: str) -> None:
        """Add a user if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        conn.close()

    def add_product_for_user(self, user_id: str, url: str, store_number: str) -> Tuple[bool, int]:
        """
        Add a product for a user. If the product already exists, just create the user-product link.
        Returns (success, product_id)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Ensure user exists
            self.add_or_get_user(user_id)

            # Check if product already exists
            cursor.execute(
                'SELECT id FROM products WHERE url = ? AND store_number = ?',
                (url, store_number)
            )
            row = cursor.fetchone()

            if row:
                product_id = row['id']
            else:
                # Create new product
                cursor.execute(
                    'INSERT INTO products (url, store_number) VALUES (?, ?)',
                    (url, store_number)
                )
                product_id = cursor.lastrowid

            # Create user-product relationship (ignore if already exists)
            cursor.execute(
                'INSERT OR IGNORE INTO user_products (user_id, product_id) VALUES (?, ?)',
                (user_id, product_id)
            )

            conn.commit()
            return True, product_id

        except Exception as e:
            print(f"Error adding product for user: {e}")
            conn.rollback()
            return False, -1

        finally:
            conn.close()

    def get_user_products(self, user_id: str) -> List[Dict]:
        """Get all products for a user"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT p.*, up.notified
            FROM products p
            JOIN user_products up ON p.id = up.product_id
            WHERE up.user_id = ?
            ORDER BY up.added_at DESC
        ''', (user_id,))

        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row['id'],
                'url': row['url'],
                'store_number': row['store_number'],
                'title': row['title'],
                'in_stock': bool(row['in_stock']),
                'last_checked': row['last_checked'],
                'notified': bool(row['notified'])
            })

        conn.close()
        return products

    def remove_product_for_user(self, user_id: str, product_index: int) -> bool:
        """Remove a product from a user's list by index"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Get the product at the given index
            products = self.get_user_products(user_id)

            if 0 <= product_index < len(products):
                product_id = products[product_index]['id']

                # Remove the user-product relationship
                cursor.execute(
                    'DELETE FROM user_products WHERE user_id = ? AND product_id = ?',
                    (user_id, product_id)
                )

                # Check if any other users are tracking this product
                cursor.execute(
                    'SELECT COUNT(*) as count FROM user_products WHERE product_id = ?',
                    (product_id,)
                )
                count = cursor.fetchone()['count']

                # If no other users are tracking it, delete the product
                if count == 0:
                    cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))

                conn.commit()
                return True

            return False

        except Exception as e:
            print(f"Error removing product: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def update_product_stock(self, product_id: int, in_stock: bool, title: Optional[str] = None) -> Tuple[bool, bool]:
        """
        Update product stock status and optionally title.
        Returns (previous_stock_status, current_stock_status)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Get current stock status
            cursor.execute('SELECT in_stock FROM products WHERE id = ?', (product_id,))
            row = cursor.fetchone()
            previous_stock = bool(row['in_stock']) if row else False

            # Update product
            if title:
                cursor.execute(
                    'UPDATE products SET in_stock = ?, title = ?, last_checked = ? WHERE id = ?',
                    (in_stock, title, datetime.now().isoformat(), product_id)
                )
            else:
                cursor.execute(
                    'UPDATE products SET in_stock = ?, last_checked = ? WHERE id = ?',
                    (in_stock, datetime.now().isoformat(), product_id)
                )

            # Record in stock history
            cursor.execute(
                'INSERT INTO stock_history (product_id, in_stock) VALUES (?, ?)',
                (product_id, in_stock)
            )

            conn.commit()
            return previous_stock, in_stock

        except Exception as e:
            print(f"Error updating product stock: {e}")
            conn.rollback()
            return False, False

        finally:
            conn.close()

    def get_all_products(self) -> List[Dict]:
        """Get all products across all users (for monitoring loop)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM products ORDER BY last_checked ASC NULLS FIRST')

        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row['id'],
                'url': row['url'],
                'store_number': row['store_number'],
                'title': row['title'],
                'in_stock': bool(row['in_stock']),
                'last_checked': row['last_checked']
            })

        conn.close()
        return products

    def get_users_tracking_product(self, product_id: int) -> List[str]:
        """Get all user IDs tracking a specific product"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT user_id FROM user_products WHERE product_id = ?',
            (product_id,)
        )

        user_ids = [row['user_id'] for row in cursor.fetchall()]
        conn.close()
        return user_ids

    def update_notified_status(self, user_id: str, product_id: int, notified: bool) -> None:
        """Update the notified flag for a user-product relationship"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE user_products SET notified = ? WHERE user_id = ? AND product_id = ?',
            (notified, user_id, product_id)
        )

        conn.commit()
        conn.close()

    def reset_notifications_for_product(self, product_id: int) -> None:
        """Reset notification flags for all users tracking a product"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE user_products SET notified = 0 WHERE product_id = ?',
            (product_id,)
        )

        conn.commit()
        conn.close()

    def get_product_stock_history(self, product_id: int, limit: int = 50) -> List[Dict]:
        """Get stock history for a product (most recent first)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, product_id, in_stock, checked_at
            FROM stock_history
            WHERE product_id = ?
            ORDER BY checked_at DESC
            LIMIT ?
        ''', (product_id, limit))

        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row['id'],
                'product_id': row['product_id'],
                'in_stock': bool(row['in_stock']),
                'checked_at': row['checked_at']
            })

        conn.close()
        return history
