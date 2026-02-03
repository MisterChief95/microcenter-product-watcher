import aiohttp
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta

from stock_checker.config import Config
from stock_checker.database import Database


class ProductMonitor:
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()  # Use default path from DATABASE_PATH env var
        # Cache for recent product checks: {(url, store_number): {'in_stock': bool, 'title': str, 'timestamp': datetime}}
        self._check_cache = {}
        self._cache_duration = timedelta(seconds=10)

    async def add_product(self, user_id, url, store_number, title=None, in_stock=None):
        """Add a product to monitor for a user"""
        user_id_str = str(user_id)
        success, product_id = self.db.add_product_for_user(user_id_str, url, store_number)

        if success and title:
            # Update the product with title and stock status
            self.db.update_product_stock(product_id, in_stock if in_stock is not None else False, title)

        return success

    def get_user_products(self, user_id):
        """Get all products for a user"""
        user_id_str = str(user_id)
        return self.db.get_user_products(user_id_str)

    def remove_product(self, user_id, index):
        """Remove a product at the given index"""
        user_id_str = str(user_id)
        return self.db.remove_product_for_user(user_id_str, index)

    def _clean_expired_cache(self):
        """Remove expired entries from the cache"""
        now = datetime.now()
        expired_keys = [
            key for key, data in self._check_cache.items()
            if now - data['timestamp'] >= self._cache_duration
        ]
        for key in expired_keys:
            del self._check_cache[key]

        if expired_keys:
            print(f"Cleaned {len(expired_keys)} expired cache entries")

    async def check_product_availability(self, url, store_number, use_cache=True):
        """Check if a product is in stock at the specified store and return (in_stock, title)

        Args:
            url: Product URL
            store_number: Store number
            use_cache: If True, return cached result if available and fresh (within 10 seconds)
        """
        cache_key = (url, store_number)

        # Check cache if enabled
        if use_cache and cache_key in self._check_cache:
            cached_data = self._check_cache[cache_key]
            cache_age = datetime.now() - cached_data['timestamp']

            if cache_age < self._cache_duration:
                print(f"Using cached result for {url} at store {store_number} (cached {cache_age.total_seconds():.1f}s ago)")
                return cached_data['in_stock'], cached_data['title']

        try:
            # Create cookie for store selection
            cookie = {
                'name': 'storeSelected',
                'value': store_number,
                'domain': '.microcenter.com',
                'path': '/',
                'secure': True,
                'httpOnly': False
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.microcenter.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="131", "Google Chrome";v="131"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Cache-Control': 'max-age=0'
            }

            # Add timeout to prevent hanging requests
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Set up cookies
                cookies = {cookie['name']: cookie['value']}

                async with session.get(url, headers=headers, cookies=cookies) as response:
                    if response.status != 200:
                        print(f"Failed to fetch {url}: Status {response.status}")
                        return None, None

                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')

                    # Extract product title from og:title meta tag
                    product_title = None
                    og_title = soup.find('meta', property='og:title')
                    if og_title and og_title.get('content'):
                        # Remove " - Micro Center" suffix if present
                        product_title = og_title.get('content').replace(' - Micro Center', '').strip()

                    # Try to find stock information
                    # Microcenter typically shows stock with specific classes/IDs
                    # You may need to adjust these selectors based on actual page structure

                    in_stock = None

                    # Look for "Add to Cart" button (usually means in stock)
                    add_to_cart = soup.find('button', {'data-name': 'Add to Cart'})
                    if add_to_cart and 'disabled' not in add_to_cart.get('class', []):
                        in_stock = True

                    # Check for inventory text
                    if in_stock is None:
                        inventory_div = soup.find('div', class_='inventory')
                        if inventory_div:
                            text = inventory_div.get_text().lower()
                            if 'in stock' in text and 'out of stock' not in text:
                                in_stock = True

                    # Check for out of stock indicators
                    if in_stock is None:
                        out_of_stock_indicators = [
                            'sold out',
                            'out of stock',
                            'not available',
                            'unavailable'
                        ]

                        page_text = soup.get_text().lower()
                        for indicator in out_of_stock_indicators:
                            if indicator in page_text:
                                in_stock = False
                                break

                    # Store in cache
                    self._check_cache[cache_key] = {
                        'in_stock': in_stock,
                        'title': product_title,
                        'timestamp': datetime.now()
                    }

                    return in_stock, product_title

        except Exception as e:
            print(f"Error checking product availability: {e}")
            return None, None

    async def check_user_products(self, user_id):
        """Check all products for a specific user"""
        user_id_str = str(user_id)
        products = self.db.get_user_products(user_id_str)

        if not products:
            return

        user = await self.bot.fetch_user(int(user_id))
        if not user:
            return

        for product in products:
            product_id = product['id']
            url = product['url']
            store_number = product['store_number']

            in_stock, title = await self.check_product_availability(url, store_number)

            if in_stock is None:
                continue  # Skip if we couldn't determine stock

            # Update product in database
            previous_stock, current_stock = self.db.update_product_stock(product_id, in_stock, title)

            # Notify user if stock status changed from out of stock to in stock
            if current_stock and not previous_stock and not product['notified']:
                product_title = title or product.get('title', 'Unknown Product')
                await user.send(
                    f"🎉 **PRODUCT NOW IN STOCK!**\n\n"
                    f"**{product_title}**\n"
                    f"Store: {store_number}\n"
                    f"{url}\n\n"
                    f"Hurry and grab it before it's gone!"
                )
                self.db.update_notified_status(user_id_str, product_id, True)
            elif not current_stock and previous_stock:
                # Reset notification flag when product goes out of stock
                self.db.update_notified_status(user_id_str, product_id, False)

    async def check_products_loop(self):
        """Continuously check all products for all users"""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            print(f"[{datetime.now().isoformat()}] Checking products...")

            # Clean expired cache entries before each check cycle
            self._clean_expired_cache()

            # Get all unique products to check
            all_products = self.db.get_all_products()

            for product in all_products:
                try:
                    product_id = product['id']
                    url = product['url']
                    store_number = product['store_number']

                    # Check availability
                    in_stock, title = await self.check_product_availability(url, store_number)

                    if in_stock is None:
                        continue

                    # Update product status
                    previous_stock, current_stock = self.db.update_product_stock(product_id, in_stock, title)

                    # If stock changed to in-stock, notify all users tracking this product
                    if current_stock and not previous_stock:
                        user_ids = self.db.get_users_tracking_product(product_id)
                        product_title = title or product.get('title', 'Unknown Product')

                        for user_id in user_ids:
                            try:
                                user = await self.bot.fetch_user(int(user_id))
                                if user:
                                    await user.send(
                                        f"🎉 **PRODUCT NOW IN STOCK!**\n\n"
                                        f"**{product_title}**\n"
                                        f"Store: {store_number}\n"
                                        f"{url}\n\n"
                                        f"Hurry and grab it before it's gone!"
                                    )
                                    self.db.update_notified_status(user_id, product_id, True)
                            except Exception as e:
                                print(f"Error notifying user {user_id}: {e}")

                    elif not current_stock and previous_stock:
                        # Reset notification flags for all users
                        self.db.reset_notifications_for_product(product_id)

                except Exception as e:
                    print(f"Error checking product {product.get('id', 'unknown')}: {e}")

            print(f"[{datetime.now().isoformat()}] Check complete. "
                  f"Sleeping for {Config.CHECK_INTERVAL} seconds...")

            await asyncio.sleep(Config.CHECK_INTERVAL)
