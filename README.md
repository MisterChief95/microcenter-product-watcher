# Microcenter Product Watcher Discord Bot

A Discord bot that monitors Microcenter product availability at specific store locations and notifies you when products come back in stock.

## Features

- Register product URLs to monitor
- Set specific Microcenter store locations
- Automatic periodic checking for stock availability
- Direct message notifications when products come in stock
- Manage multiple products per user

## Prerequisites

- **Option 1 (Docker - Recommended):**
  - Docker and Docker Compose installed
  - A Discord bot token
  - Discord account

- **Option 2 (Manual):**
  - Python 3.8 or higher
  - A Discord bot token
  - Discord account

## Setup

### Option 1: Docker Setup (Recommended)

Docker provides an isolated, consistent environment and handles all dependencies automatically.

#### 1. Clone the Repository

```bash
cd microcenter-product-watcher
```

#### 2. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - MESSAGE CONTENT INTENT
   - DIRECT MESSAGES INTENT
5. Go to "Installation" tab and configure:
   - **Installation Contexts**: Enable both "Guild Install" and "User Install"
   - **Install Link**: Set to "Discord Provided Link"
   - **Default Install Settings**:
     - Scopes: `applications.commands` and `bot`
     - Permissions: `Send Messages` (permission code: 2048)
6. Copy your bot token from the "Bot" tab

#### 3. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your bot token:
   ```
   DISCORD_BOT_TOKEN=your_actual_bot_token_here
   CHECK_INTERVAL=300
   ```

#### 4. Create Data Directory

```bash
mkdir -p data
```

This directory will store the SQLite database and persist across container restarts.

#### 5. Build and Run with Docker Compose

```bash
# Build the Docker image
docker-compose build

# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

#### 6. Install the Bot to Discord

Follow the same installation steps as in the manual setup below.

#### Docker Management Commands

```bash
# View running containers
docker-compose ps

# Restart the bot
docker-compose restart

# View logs (last 100 lines)
docker-compose logs --tail=100

# Stop and remove containers
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Option 2: Manual Setup

#### 1. Clone the Repository

```bash
cd microcenter-product-watcher
```

#### 2. Install Dependencies

Choose one of the following methods:

**Using pyproject.toml (Recommended):**
```bash
pip install -e .

# For development with linting tools
pip install -e ".[dev]"
```

**Using requirements.txt (Legacy):**
```bash
pip install -r requirements.txt
```

#### 3. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - MESSAGE CONTENT INTENT
   - DIRECT MESSAGES INTENT
5. Go to "Installation" tab and configure:
   - **Installation Contexts**: Enable both "Guild Install" and "User Install"
   - **Install Link**: Set to "Discord Provided Link"
   - **Default Install Settings**:
     - Scopes: `applications.commands` and `bot`
     - Permissions: `Send Messages` (permission code: 2048)
6. Copy your bot token from the "Bot" tab

#### 4. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your bot token:
   ```
   DISCORD_BOT_TOKEN=your_actual_bot_token_here
   CHECK_INTERVAL=300
   ```

   - `DISCORD_BOT_TOKEN`: Your Discord bot token
   - `CHECK_INTERVAL`: How often to check products (in seconds, default: 300 = 5 minutes)

#### 5. Install the Bot

You can install the bot in two ways:

#### Option A: User Install (Recommended)
Install the bot directly to your Discord account - works everywhere you go:

1. In the Discord Developer Portal, go to "Installation" tab
2. Copy the "Install Link"
3. Open the link in your browser
4. Click "Add to Account" or "Add to Server"

#### Option B: Manual Install URL
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=2048&scope=bot+applications.commands
```

Replace `YOUR_CLIENT_ID` with your Application ID from the Developer Portal.

**Note**: With user install, the bot follows you across all servers. All command responses are ephemeral (only visible to you), and stock notifications are sent via DM.

## Usage

The bot uses Discord slash commands. You can use them in DMs or in any server where the bot is present.

### Register a Product

Use the `/register` command with the store number and product URL:

```
/register store_number:131 product_url:https://www.microcenter.com/product/12345/product-name
```

Or with a partial URL:
```
/register store_number:131 product_url:/product/12345/product-name
```

Parameters:
- `store_number`: Your 3-digit Microcenter store number (e.g., 131 for Tustin, CA)
- `product_url`: The Microcenter product URL (full or partial path)

### List Your Products

```
/list
```

Shows all your registered products with their current stock status.

### Remove a Product

```
/remove product_number:2
```

Remove a product by its number (use `/list` to see numbers).

### Manually Check All Products

```
/checkall
```

Triggers an immediate check of all your registered products.

## Finding Store Numbers

Visit [Microcenter Stores](https://www.microcenter.com/site/stores/default.aspx) to find your store.

Common store numbers:
- 131: Tustin, CA
- 065: Westmont, IL
- 121: Cambridge, MA
- 101: Rockville, MD
- 181: St. Louis Park, MN

## Running the Bot

```bash
python -m stock_checker.bot
```

The bot will:
1. Connect to Discord
2. Start monitoring registered products
3. Check products every `CHECK_INTERVAL` seconds
4. Send you a DM when a product comes in stock

## Testing

Before running the bot, you can verify everything works:

### Test Database Operations

```bash
python tests/test_database.py
```

This runs unit tests for all database operations (add/remove products, deduplication, etc.)

### Test Discord Notifications

```bash
python tests/test_notification.py
```

This sends a test DM notification to verify the bot can reach you on Discord.

**See [TESTING.md](TESTING.md) for detailed testing instructions and troubleshooting.**

## Notes

- The bot checks products periodically based on `CHECK_INTERVAL`
- You'll only be notified when a product goes from out-of-stock to in-stock
- All data is stored in a SQLite database (`products.db`) in the same directory
- Products are deduplicated - if multiple users track the same product at the same store, only one entry is stored
- Stock history is tracked for analytics
- The bot uses web scraping, so it may need updates if Microcenter changes their website structure

## Development

### Code Quality Tools

This project includes Ruff and Pylint for code quality and formatting:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run Ruff linter
ruff check stock_checker/ tests/

# Run Ruff formatter
ruff format stock_checker/ tests/

# Run Pylint
pylint stock_checker/

# Run tests
pytest
```

### Building Docker Images

```bash
# Build with custom tag
docker build -t microcenter-watcher:v1.0.0 .

# Build without cache
docker-compose build --no-cache

# Push to registry (if configured)
docker tag microcenter-watcher:latest your-registry/microcenter-watcher:latest
docker push your-registry/microcenter-watcher:latest
```

## Troubleshooting

### Docker Issues

**Container keeps restarting:**
```bash
# Check logs for errors
docker-compose logs -f

# Check container status
docker-compose ps
```

**Database permission issues:**
```bash
# Ensure data directory has correct permissions
chmod -R 755 data/
```

**Environment variables not loading:**
- Verify `.env` file exists in the same directory as `docker-compose.yml`
- Check that variable names match exactly
- Restart container after changing `.env`: `docker-compose restart`

### General Issues

### Bot doesn't respond
- Make sure you've enabled MESSAGE CONTENT INTENT in the Discord Developer Portal
- Check that your bot token is correct in `.env`

### Stock detection not working
- Microcenter's website structure may have changed
- Check the console output for errors
- You may need to adjust the selectors in [monitor.py](stock_checker/monitor.py)

### Bot goes offline
- Ensure the script is running continuously
- Consider using a process manager like `pm2` or running in a screen/tmux session
- For production, deploy to a server or cloud platform

## Project Structure

```
microcenter-product-watcher/
├── stock_checker/                    # Source code directory
│   ├── __init__.py         # Package initialization
│   ├── bot.py              # Main Discord bot with command handlers
│   ├── monitor.py          # Product monitoring logic
│   ├── database.py         # SQLite database operations
│   └── config.py           # Configuration settings
├── tests/                  # Test directory
│   ├── __init__.py         # Test package initialization
│   ├── test_database.py    # Database unit tests
│   └── test_notification.py # Discord notification test
├── data/                   # Docker volume for database persistence
│   └── products.db         # SQLite database (created automatically)
├── pyproject.toml          # Python project configuration and dependencies
├── requirements.txt        # Python dependencies (legacy)
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── Makefile                # Build and development commands
├── .dockerignore           # Docker build ignore patterns
├── .env                    # Environment variables (create from .env.example)
├── .env.example            # Environment variables template
├── .gitignore              # Git ignore file
├── README.md               # This file
├── DOCKER.md               # Docker setup and deployment guide
└── TESTING.md              # Testing guide
```

## License

This project is for educational purposes. Please respect Microcenter's terms of service and don't abuse their website with excessive requests.
