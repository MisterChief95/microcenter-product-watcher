# Testing Guide

This project includes comprehensive tests to verify functionality before running the bot in production.

## Available Tests

### 1. Database Operations Test

**File:** [test_database.py](test_database.py)

**What it tests:**
- Database initialization and schema creation
- Adding users and products
- Product deduplication (multiple users tracking same product)
- Getting user products
- Updating product stock status
- Getting all products (for monitoring loop)
- Finding users tracking a specific product
- Notification status updates
- Product removal
- Stock history tracking

**How to run:**
```bash
python test_database.py
```

**Expected output:**
```
============================================================
Database Tests
============================================================

Test 1: Initialize database
[PASS] Database initialized

Test 2: Add users and products
  User 1, Product 1: ✅ (ID: 1)
  User 1, Product 2: ✅ (ID: 2)
  ...
```

All tests should pass with checkmarks. The test creates a temporary database, runs all operations, and cleans up afterwards.

---

### 2. Discord Notification Test

**File:** [test_notification.py](test_notification.py)

**What it tests:**
- Bot connection to Discord
- Ability to fetch user information
- Sending DM notifications to users
- Access to database for user/product info

**Prerequisites:**
- You must have at least one product registered in the database
- The bot must have permission to DM you on Discord
- Your `.env` file must have a valid `DISCORD_BOT_TOKEN`

**How to run:**
```bash
python test_notification.py
```

**Expected output:**
```
============================================================
Discord Notification Test
============================================================

BotName#1234 has connected to Discord!

Found 1 user(s) in database:
1. User ID: 123456789 (3 products)

Using user: 123456789

User's products:
1. Gigabyte NVIDIA GeForce RTX 5090...
   Store: 205
   URL: https://www.microcenter.com/product/...
   Current status: Out of Stock

Sending test notification to user 123456789...
✅ Test notification sent successfully!
Check your Discord DMs from BotName

Test complete. Shutting down...
```

**What you'll receive:**
A Discord DM from your bot with a test notification that looks like:

> 🎉 **PRODUCT NOW IN STOCK!** (TEST NOTIFICATION)
>
> **Gigabyte NVIDIA GeForce RTX 5090...**
>
> **Store:** 205
> **URL:** https://www.microcenter.com/product/...
>
> Hurry and grab it before it's gone!
>
> _This is a test notification. The product may not actually be in stock._

---

## Common Issues

### Database Test Issues

**Issue:** `FileNotFoundError: [Errno 2] No such file or directory: 'test_products.db'`
- **Solution:** This is expected - the test creates and deletes its own database

**Issue:** Tests fail with database errors
- **Solution:** Make sure no other process is using the test database file

### Notification Test Issues

**Issue:** `No users found in database!`
- **Solution:** Register at least one product using the Discord bot first with `/register`

**Issue:** `Cannot send DM to user`
- **Solution:**
  - Make sure you've interacted with the bot at least once
  - Check your Discord privacy settings allow DMs from server members
  - Ensure the bot has the proper intents enabled in Discord Developer Portal

**Issue:** `DISCORD_BOT_TOKEN not found`
- **Solution:** Create a `.env` file with your bot token (see `.env.example`)

---

## Running All Tests

You can run all tests in sequence:

**Windows:**
```bash
python test_database.py && python test_notification.py
```

**Linux/Mac:**
```bash
python3 test_database.py && python3 test_notification.py
```

---

## Integration Testing

To fully test the bot end-to-end:

1. Start the bot: `python bot.py`
2. Use Discord slash commands:
   - `/register store_number:131 product_url:https://www.microcenter.com/product/12345/test`
   - `/list` to see your products
   - `/checkall` to manually trigger a check
   - `/remove product_number:1` to remove a product
3. Wait for the scheduled check cycle to run
4. Verify you receive DMs when products come in stock

---

## Debugging

If you encounter issues, check:

1. **Database file exists:** `products.db` should be created automatically
2. **Bot token is valid:** Check `.env` file
3. **Bot has correct permissions:** MESSAGE CONTENT INTENT and DM permissions in Discord Developer Portal
4. **Python version:** Requires Python 3.8+
5. **Dependencies installed:** Run `pip install -r requirements.txt`

For detailed logs, check the console output when running the bot or tests.
