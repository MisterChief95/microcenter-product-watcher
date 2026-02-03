import logging
import os
import re
from datetime import datetime

import discord
from discord.ext import commands
from discord.ui import Modal, Select, TextInput, View
from dotenv import load_dotenv

from stock_checker.config import Config
from stock_checker.monitor import ProductMonitor

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
monitor = ProductMonitor(bot)


def parse_product_url(user_input):
    """
    Parse user input and return a valid Microcenter product URL.
    Accepts:
    - Full URL: https://www.microcenter.com/product/12345/product-name
    - Partial URL: /product/12345/product-name

    Note: The slug (product-name) is required by Microcenter.
    """
    user_input = user_input.strip()

    # If it's already a full URL, validate it has the format /product/<number>/<slug>
    if user_input.startswith('https://www.microcenter.com/product/'):
        # Must have product number AND slug
        match = re.search(r'/product/(\d+)/(.+)', user_input)
        if match:
            return user_input
        return None

    # If it starts with /product/, add the domain
    if user_input.startswith('/product/'):
        # Must have product number AND slug
        match = re.search(r'/product/(\d+)/(.+)', user_input)
        if match:
            return f'https://www.microcenter.com{user_input}'
        return None

    return None


class RegisterModal(Modal):
    def __init__(self, monitor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = monitor

        self.store_number_input = TextInput(
            label='Store Number', placeholder='e.g., 131, 065, 121', required=True, max_length=3
        )
        self.add_item(self.store_number_input)

        self.url_input = TextInput(
            label='Microcenter Product URL or Path',
            placeholder='e.g., https://www.microcenter.com/product/12345/product-name or /product/12345/product-name',
            required=True,
            max_length=200,
        )
        self.add_item(self.url_input)

    async def on_submit(self, interaction: discord.Interaction):
        logger.info(f'User {interaction.user.id} ({interaction.user.name}) started product registration')
        await interaction.response.defer(ephemeral=True)

        store_number = self.store_number_input.value.strip()
        product_url = self.url_input.value

        logger.debug(f'Registration input - Store: {store_number}, URL: {product_url}')

        # Validate store number (should be numeric and 3 digits)
        if not store_number.isdigit() or len(store_number) != 3:
            logger.warning(f'Invalid store number provided by user {interaction.user.id}: {store_number}')
            await interaction.followup.send(
                '❌ Invalid store number. Please provide a 3-digit store number (e.g., 131, 065, 121).', ephemeral=True
            )
            return

        # Parse and normalize the URL
        parsed_url = parse_product_url(product_url)
        if not parsed_url:
            logger.warning(f'Invalid URL format provided by user {interaction.user.id}: {product_url}')
            await interaction.followup.send(
                '❌ Invalid URL format. Please provide:\n'
                '- Full URL: https://www.microcenter.com/product/12345/product-name\n'
                '- Partial: /product/12345/product-name\n\n'
                'Note: The full path including the product name is required.',
                ephemeral=True,
            )
            return

        logger.info(f'Parsed URL: {parsed_url}')
        logger.info(f'Checking product availability for user {interaction.user.id}')

        # Validate the product exists and get its title
        in_stock, title = await self.monitor.check_product_availability(parsed_url, store_number)

        if title is None:
            logger.error(f'Failed to fetch product info for {parsed_url} at store {store_number}')
            await interaction.followup.send(
                '❌ Unable to fetch product information from Microcenter.\n\n'
                'Please verify:\n'
                '- The product URL is correct\n'
                '- The store number is valid\n'
                '- The product page is accessible',
                ephemeral=True,
            )
            return

        logger.info(f'Product found: {title} - Stock status: {in_stock}')

        # Register the product
        success = await self.monitor.add_product(interaction.user.id, parsed_url, store_number, title, in_stock)

        if success:
            logger.info(f'Product registered successfully for user {interaction.user.id}: {title}')
            stock_status = '✅ In Stock' if in_stock else '❌ Out of Stock'
            await interaction.followup.send(
                f"""✅ Product registered successfully!
**{title}**
Store: {store_number}
Current Status: {stock_status}
{parsed_url}
I'll check availability every {Config.CHECK_INTERVAL // 60} minutes and notify you when it's in stock!""",
                ephemeral=True,
            )
        else:
            logger.error(f'Failed to register product for user {interaction.user.id}: {title}')
            await interaction.followup.send('❌ Failed to register product. Please try again.', ephemeral=True)


@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info('Bot is ready to receive commands')
    logger.info(f'Connected to {len(bot.guilds)} guild(s)')
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
        for cmd in synced:
            logger.debug(f'  - {cmd.name}')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}', exc_info=True)
    # Start the monitoring task
    logger.info('Starting product monitoring loop')
    bot.loop.create_task(monitor.check_products_loop())


@bot.tree.command(name='register', description='Register a product URL to monitor')
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def register_product(interaction: discord.Interaction):
    """Register a new product to monitor"""
    logger.info(f'User {interaction.user.id} ({interaction.user.name}) invoked /register command')
    modal = RegisterModal(monitor, title='Register Product')
    await interaction.response.send_modal(modal)


@bot.tree.command(name='list', description='List all your registered products')
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def list_products(interaction: discord.Interaction):
    """List all products registered by the user"""
    logger.info(f'User {interaction.user.id} ({interaction.user.name}) invoked /list command')
    products = monitor.get_user_products(interaction.user.id)
    logger.debug(f'User {interaction.user.id} has {len(products)} registered product(s)')

    if not products:
        await interaction.response.send_message(
            "You haven't registered any products yet.\nUse `/register` to start monitoring a product!", ephemeral=True
        )
        return

    message = '**Your Registered Products:**\n\n'
    for i, product in enumerate(products, 1):
        title = product.get('title', 'Unknown Product')
        message += f'{i}. **{title}**\n'
        message += f'   Store: {product["store_number"]}\n'
        message += f'   Status: {"✅ In Stock" if product.get("in_stock") else "❌ Out of Stock"}\n'

        # Format last checked as Discord timestamp
        last_checked = product.get('last_checked')
        if last_checked:
            try:
                dt = datetime.fromisoformat(last_checked)
                timestamp = int(dt.timestamp())
                message += f'   Last checked: <t:{timestamp}:f>\n'
            except (ValueError, AttributeError):
                message += f'   Last checked: {last_checked}\n'
        else:
            message += '   Last checked: Never\n'

        message += f'   URL: {product["url"]}\n\n'

    await interaction.response.send_message(message, ephemeral=True)


@bot.tree.command(name='remove', description='Remove a registered product')
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def remove_product(interaction: discord.Interaction, product_number: int):
    """Remove a product from monitoring"""
    logger.info(
        f'User {interaction.user.id} ({interaction.user.name}) invoked /remove command for product #{product_number}'
    )
    success = monitor.remove_product(interaction.user.id, product_number - 1)

    if success:
        logger.info(f'Product #{product_number} removed successfully for user {interaction.user.id}')
        await interaction.response.send_message(f'✅ Product #{product_number} removed successfully!', ephemeral=True)
    else:
        logger.warning(f'Product #{product_number} not found for user {interaction.user.id}')
        await interaction.response.send_message(
            f'❌ Could not find product #{product_number}. Use `/list` to see your products.', ephemeral=True
        )


@bot.tree.command(name='checkall', description='Manually check all your products now')
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def check_all(interaction: discord.Interaction):
    """Manually trigger a check for all user's products"""
    logger.info(f'User {interaction.user.id} ({interaction.user.name}) invoked /checkall command')
    await interaction.response.defer(ephemeral=True)

    products = monitor.get_user_products(interaction.user.id)
    logger.debug(f'User {interaction.user.id} has {len(products)} product(s) to check')

    if not products:
        await interaction.followup.send(
            "You haven't registered any products yet.\nUse `/register` to start monitoring a product!", ephemeral=True
        )
        return

    # Perform the check
    logger.info(f'Starting manual check for user {interaction.user.id}')
    await monitor.check_user_products(interaction.user.id)

    # Get updated product info
    products = monitor.get_user_products(interaction.user.id)

    # Build status message
    message = '✅ **Check Complete!**\n\n'
    in_stock_count = 0
    out_of_stock_count = 0

    for product in products:
        title = product.get('title', 'Unknown Product')
        status = product.get('in_stock', False)
        if status:
            in_stock_count += 1
            message += f'✅ **{title}** - IN STOCK\n'
        else:
            out_of_stock_count += 1
            message += f'❌ **{title}** - Out of Stock\n'
        message += f'   Store: {product["store_number"]}\n'
        message += f'   {product["url"]}\n\n'

    message += f'\n**Summary**: {in_stock_count} in stock, {out_of_stock_count} out of stock'
    logger.info(
        f'Manual check complete for user {interaction.user.id}: {in_stock_count} in stock, {out_of_stock_count} out of stock'
    )

    await interaction.followup.send(message, ephemeral=True)


class ProductSelectView(View):
    def __init__(self, products, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

        # Create select menu with product options
        options = []
        for i, product in enumerate(products):
            title = product.get('title', 'Unknown Product')
            # Truncate title if too long (max 100 chars for label)
            if len(title) > 97:
                title = title[:97] + '...'

            options.append(
                discord.SelectOption(
                    label=f'{i + 1}. {title}', description=f'Store: {product["store_number"]}', value=str(product['id'])
                )
            )

        select = Select(placeholder='Choose a product to view history...', options=options, custom_id='product_select')
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message('This menu is not for you!', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Get the selected value from the select component
        select_component = [item for item in self.children if isinstance(item, Select)][0]
        product_id = int(select_component.values[0])

        # Get product info
        products = monitor.get_user_products(interaction.user.id)
        product = next((p for p in products if p['id'] == product_id), None)

        if not product:
            await interaction.followup.send('❌ Product not found.', ephemeral=True)
            return

        # Get stock history
        history = monitor.db.get_product_stock_history(product_id, limit=20)

        if not history:
            await interaction.followup.send(
                f'**{product.get("title", "Unknown Product")}**\n\n'
                f'No stock history available yet. The product will be checked during the next monitoring cycle.',
                ephemeral=True,
            )
            return

        # Build history message
        title = product.get('title', 'Unknown Product')
        message = f'**Stock History: {title}**\n'
        message += f'Store: {product["store_number"]}\n'
        message += f'{product["url"]}\n\n'
        message += '**Last 20 Checks:**\n'

        # Group consecutive same-status checks
        grouped = []
        prev_status = None
        prev_time = None
        count = 0
        start_time = None

        for entry in reversed(history):  # Process oldest first for grouping
            status = entry['in_stock']
            if status == prev_status:
                count += 1
            else:
                if prev_status is not None:
                    grouped.append((prev_status, count, start_time, prev_time))
                prev_status = status
                count = 1
                start_time = entry['checked_at']
            prev_time = entry['checked_at']

        # Add last group
        if prev_status is not None:
            grouped.append((prev_status, count, start_time, prev_time))

        # Display grouped history (most recent first)
        for status, count, start_time, end_time in reversed(grouped):
            status_icon = '✅ In Stock' if status else '❌ Out of Stock'

            try:
                end_dt = datetime.fromisoformat(end_time)
                end_timestamp = int(end_dt.timestamp())

                if count == 1:
                    message += f'{status_icon} - <t:{end_timestamp}:f>\n'
                else:
                    start_dt = datetime.fromisoformat(start_time)
                    start_timestamp = int(start_dt.timestamp())
                    message += f'{status_icon} - <t:{start_timestamp}:f> to <t:{end_timestamp}:f> ({count} checks)\n'
            except (ValueError, AttributeError):
                message += f'{status_icon} - {end_time}\n'

        await interaction.followup.send(message, ephemeral=True)


@bot.tree.command(name='history', description='View stock history for your products')
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def view_history(interaction: discord.Interaction):
    """View stock check history for a product"""
    logger.info(f'User {interaction.user.id} ({interaction.user.name}) invoked /history command')
    products = monitor.get_user_products(interaction.user.id)

    if not products:
        await interaction.response.send_message(
            "You haven't registered any products yet.\nUse `/register` to start monitoring a product!", ephemeral=True
        )
        return

    # Show select menu
    view = ProductSelectView(products, interaction.user.id)
    await interaction.response.send_message('Select a product to view its stock history:', view=view, ephemeral=True)


def main():
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error('DISCORD_BOT_TOKEN not found in environment variables!')
        logger.error('Please create a .env file with your Discord bot token.')
        return

    logger.info('Starting bot...')
    bot.run(token)


if __name__ == '__main__':
    main()
