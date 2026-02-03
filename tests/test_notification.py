"""
Test script for sending Discord notifications.
This script allows you to test the notification system without waiting for actual stock changes.
"""

import asyncio
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Add stock_checker to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from stock_checker.database import Database

load_dotenv()


async def test_send_notification():
    """Test sending a notification to a user"""

    # Set up bot with minimal intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True

    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f'{bot.user} has connected to Discord!')

        # Get database
        db = Database('products.db')

        # Get all users
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        user_rows = cursor.fetchall()
        conn.close()

        if not user_rows:
            print('\nNo users found in database!')
            print('Please register a product first using the Discord bot.')
            await bot.close()
            return

        print(f'\nFound {len(user_rows)} user(s) in database:')
        for i, row in enumerate(user_rows, 1):
            user_id = row['user_id']
            products = db.get_user_products(user_id)
            print(f'{i}. User ID: {user_id} ({len(products)} products)')

        # Ask which user to test (or just use the first one)
        if len(user_rows) == 1:
            test_user_id = user_rows[0]['user_id']
            print(f'\nUsing user: {test_user_id}')
        else:
            # For simplicity, just use the first user
            # You could expand this to allow selection
            test_user_id = user_rows[0]['user_id']
            print(f'\nUsing first user: {test_user_id}')

        # Get user's products
        products = db.get_user_products(test_user_id)

        if not products:
            print('User has no products!')
            await bot.close()
            return

        print("\nUser's products:")
        for i, product in enumerate(products, 1):
            print(f'{i}. {product.get("title", "Unknown Product")}')
            print(f'   Store: {product["store_number"]}')
            print(f'   URL: {product["url"]}')
            print(f'   Current status: {"In Stock" if product["in_stock"] else "Out of Stock"}')
            print()

        # Send test notification
        print(f'Sending test notification to user {test_user_id}...')

        try:
            user = await bot.fetch_user(int(test_user_id))

            if user:
                # Use the first product for the test
                test_product = products[0]
                product_title = test_product.get('title', 'Unknown Product')
                store_number = test_product['store_number']
                url = test_product['url']

                await user.send(
                    f'🎉 **PRODUCT NOW IN STOCK!** (TEST NOTIFICATION)\n\n'
                    f'**{product_title}**\n'
                    f'Store: {store_number}\n'
                    f'{url}\n\n'
                    f"Hurry and grab it before it's gone!\n\n"
                    f'_This is a test notification. The product may not actually be in stock._'
                )

                print('✅ Test notification sent successfully!')
                print(f'Check your Discord DMs from {bot.user.name}')
            else:
                print(f'❌ Could not fetch user with ID {test_user_id}')

        except discord.errors.Forbidden:
            print(f'❌ Cannot send DM to user {test_user_id}')
            print('The user may have DMs disabled or has not interacted with the bot.')
        except Exception as e:
            print(f'❌ Error sending notification: {e}')

        print('\nTest complete. Shutting down...')
        await bot.close()

    # Get token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print('ERROR: DISCORD_BOT_TOKEN not found in environment variables!')
        print('Please create a .env file with your Discord bot token.')
        return

    # Run bot
    await bot.start(token)


if __name__ == '__main__':
    print('=' * 60)
    print('Discord Notification Test')
    print('=' * 60)
    print()

    asyncio.run(test_send_notification())
