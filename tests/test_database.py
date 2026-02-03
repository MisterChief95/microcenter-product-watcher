"""
Unit tests for database operations.
Run this to verify database functionality without needing Discord.
"""

import os
import sys
from pathlib import Path

# Add stock_checker to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_checker.database import Database


def run_tests():
    """Run database tests"""
    test_db = 'test_products.db'

    # Clean up any existing test database
    if os.path.exists(test_db):
        os.remove(test_db)

    print('=' * 60)
    print('Database Tests')
    print('=' * 60)
    print()

    # Initialize database
    print('Test 1: Initialize database')
    db = Database(test_db)
    print('[PASS] Database initialized\n')

    # Test adding users and products
    print('Test 2: Add users and products')
    test_user_1 = '123456789'
    test_user_2 = '987654321'

    success_1, product_id_1 = db.add_product_for_user(
        test_user_1, 'https://www.microcenter.com/product/12345/test-product-1', '131'
    )
    print(f'  User 1, Product 1: {"✅" if success_1 else "❌"} (ID: {product_id_1})')

    success_2, product_id_2 = db.add_product_for_user(
        test_user_1, 'https://www.microcenter.com/product/67890/test-product-2', '131'
    )
    print(f'  User 1, Product 2: {"✅" if success_2 else "❌"} (ID: {product_id_2})')

    # Test deduplication - same product for different user
    success_3, product_id_3 = db.add_product_for_user(
        test_user_2, 'https://www.microcenter.com/product/12345/test-product-1', '131'
    )
    print(f'  User 2, Product 1 (duplicate): {"✅" if success_3 else "❌"} (ID: {product_id_3})')

    if product_id_1 == product_id_3:
        print('  ✅ Deduplication working! Same product ID for both users')
    else:
        print(f'  ❌ Deduplication failed! Different product IDs: {product_id_1} vs {product_id_3}')
    print()

    # Test getting user products
    print('Test 3: Get user products')
    user_1_products = db.get_user_products(test_user_1)
    print(f'  User 1 has {len(user_1_products)} products')
    for p in user_1_products:
        print(f'    - Product {p["id"]}: {p["url"]} (Store: {p["store_number"]})')

    user_2_products = db.get_user_products(test_user_2)
    print(f'  User 2 has {len(user_2_products)} products')
    for p in user_2_products:
        print(f'    - Product {p["id"]}: {p["url"]} (Store: {p["store_number"]})')
    print()

    # Test updating product stock
    print('Test 4: Update product stock')
    prev, curr = db.update_product_stock(product_id_1, True, 'Test Product Title')
    print(f'  Stock update: Previous={prev}, Current={curr}')
    print(f'  {"✅" if curr else "❌"} Product marked as in stock')

    # Verify the update
    updated_products = db.get_user_products(test_user_1)
    updated_product = next((p for p in updated_products if p['id'] == product_id_1), None)
    if updated_product:
        print(f'  Title: {updated_product["title"]}')
        print(f'  In Stock: {updated_product["in_stock"]}')
        print(f'  Last Checked: {updated_product["last_checked"]}')
    print()

    # Test getting all products
    print('Test 5: Get all products (for monitoring loop)')
    all_products = db.get_all_products()
    print(f'  Total unique products: {len(all_products)}')
    for p in all_products:
        print(f'    - Product {p["id"]}: {p["url"]} (Store: {p["store_number"]})')
    print()

    # Test getting users tracking a product
    print('Test 6: Get users tracking a product')
    tracking_users = db.get_users_tracking_product(product_id_1)
    print(f'  Product {product_id_1} is tracked by {len(tracking_users)} user(s):')
    for user_id in tracking_users:
        print(f'    - User: {user_id}')
    print()

    # Test notification status
    print('Test 7: Update notification status')
    db.update_notified_status(test_user_1, product_id_1, True)
    user_products = db.get_user_products(test_user_1)
    notified_product = next((p for p in user_products if p['id'] == product_id_1), None)
    if notified_product and notified_product['notified']:
        print('  ✅ Notification status updated')
    else:
        print('  ❌ Notification status NOT updated')
    print()

    # Test removing a product
    print('Test 8: Remove product from user')
    success = db.remove_product_for_user(test_user_1, 0)  # Remove first product
    print(f'  Remove result: {"✅" if success else "❌"}')

    user_1_products_after = db.get_user_products(test_user_1)
    print(f'  User 1 now has {len(user_1_products_after)} products')

    # Check if product still exists (should, because user 2 is tracking it)
    all_products_after = db.get_all_products()
    if product_id_1 in [p['id'] for p in all_products_after]:
        print(f'  ✅ Product {product_id_1} still exists (tracked by user 2)')
    else:
        print(f'  ❌ Product {product_id_1} was deleted (should still exist)')
    print()

    # Test stock history
    print('Test 9: Check stock history')
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM stock_history')
    history_count = cursor.fetchone()['count']
    print(f'  Stock history entries: {history_count}')

    cursor.execute('SELECT product_id, in_stock, checked_at FROM stock_history ORDER BY checked_at DESC LIMIT 5')
    print('  Recent stock checks:')
    for row in cursor.fetchall():
        print(
            f'    - Product {row["product_id"]}: {"In Stock" if row["in_stock"] else "Out of Stock"} at {row["checked_at"]}'
        )
    conn.close()
    print()

    # Clean up
    print('Test 10: Clean up')
    os.remove(test_db)
    print('  ✅ Test database removed')
    print()

    print('=' * 60)
    print('All tests completed!')
    print('=' * 60)


if __name__ == '__main__':
    run_tests()
