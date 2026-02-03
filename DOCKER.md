# Docker Setup Guide

This guide covers running the Microcenter Product Watcher using Docker and Docker Compose.

## Quick Start

1. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your DISCORD_BOT_TOKEN
   ```

2. **Create data directory:**
   ```bash
   mkdir -p data
   ```

3. **Build and run:**
   ```bash
   docker-compose up -d
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

## Architecture

### Container Structure

- **Base Image:** `python:3.11-slim`
- **Working Directory:** `/app`
- **Database Location:** `/app/data/products.db` (mounted volume)
- **Python Environment:** Isolated with all dependencies installed

### Volume Mounts

The SQLite database is stored in a volume mount to persist data across container restarts:

```yaml
volumes:
  - ./data:/app/data
```

This means:
- Host directory: `./data` (relative to docker-compose.yml)
- Container directory: `/app/data`
- Database file: `data/products.db`

## Environment Variables

Required environment variables (configured in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token | (required) |
| `CHECK_INTERVAL` | Seconds between product checks | 300 |
| `DATABASE_PATH` | Path to SQLite database | /app/data/products.db |

## Docker Commands

### Using docker-compose (Recommended)

```bash
# Build the image
docker-compose build

# Start in background
docker-compose up -d

# Start in foreground (see logs directly)
docker-compose up

# Stop container
docker-compose down

# Restart container
docker-compose restart

# View logs (last 100 lines, follow mode)
docker-compose logs -f --tail=100

# View container status
docker-compose ps

# Execute commands in running container
docker-compose exec microcenter-watcher python tests/test_database.py

# Open shell in container
docker-compose exec microcenter-watcher /bin/bash

# Rebuild and restart
docker-compose up -d --build

# Stop and remove volumes (DELETES DATABASE!)
docker-compose down -v
```

### Using Makefile

A Makefile is provided for convenience:

```bash
# View all available commands
make help

# Build image
make build

# Start container
make up

# Stop container
make down

# View logs
make logs

# Open shell
make shell

# Clean everything (removes database!)
make clean
```

### Using Docker directly

```bash
# Build image
docker build -t microcenter-watcher .

# Run container
docker run -d \
  --name microcenter-watcher \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  microcenter-watcher

# View logs
docker logs -f microcenter-watcher

# Stop container
docker stop microcenter-watcher

# Remove container
docker rm microcenter-watcher
```

## Data Persistence

### Database Location

The SQLite database is stored at `./data/products.db` on your host machine. This ensures:
- Data persists across container restarts
- Database survives container deletion
- Easy backup and migration
- Direct access for debugging

### Backing Up Data

```bash
# Copy database to backup location
cp data/products.db data/products.db.backup

# Or create timestamped backup
cp data/products.db "data/products-$(date +%Y%m%d-%H%M%S).db"
```

### Restoring Data

```bash
# Stop container first
docker-compose down

# Restore from backup
cp data/products.db.backup data/products.db

# Start container
docker-compose up -d
```

## Troubleshooting

### Container won't start

**Check logs:**
```bash
docker-compose logs
```

**Common issues:**
- Missing `.env` file
- Invalid `DISCORD_BOT_TOKEN`
- Port conflicts (unlikely for this bot)

### Database permission errors

**On Linux/Mac:**
```bash
# Ensure correct permissions
chmod -R 755 data/
```

**On Windows:**
- Usually not an issue due to Docker Desktop handling permissions

### Container keeps restarting

**Check container status:**
```bash
docker-compose ps
docker-compose logs -f
```

**Common causes:**
- Invalid bot token (bot can't connect to Discord)
- Network connectivity issues
- Code errors (check logs for Python tracebacks)

### Environment variables not loading

**Verify `.env` file:**
```bash
cat .env
```

**Check variable names:**
- Must exactly match expected names
- No spaces around `=`
- No quotes needed for values

**Reload environment:**
```bash
docker-compose down
docker-compose up -d
```

### Database locked errors

This can happen if:
- Multiple containers are accessing the same database
- Previous container didn't shut down cleanly

**Fix:**
```bash
docker-compose down
# Wait a few seconds
docker-compose up -d
```

### Can't access database file

**Check volume mount:**
```bash
# List files in container
docker-compose exec microcenter-watcher ls -la /app/data

# Check if database exists on host
ls -la data/
```

## Development with Docker

### Running tests in container

```bash
# Run database tests
docker-compose exec microcenter-watcher python tests/test_database.py

# Run notification tests
docker-compose exec microcenter-watcher python tests/test_notification.py
```

### Code changes

Since code is copied during image build, you need to rebuild after changes:

```bash
docker-compose up -d --build
```

### Development mode with live reload

For development, consider mounting the code as a volume:

```yaml
# Add to docker-compose.yml services.microcenter-watcher
volumes:
  - ./data:/app/data
  - ./bot.py:/app/bot.py
  - ./monitor.py:/app/monitor.py
  - ./database.py:/app/database.py
  - ./config.py:/app/config.py
```

Then restart to pick up changes without rebuilding.

## Production Deployment

### Best Practices

1. **Use specific tags instead of `latest`:**
   ```bash
   docker build -t microcenter-watcher:v1.0.0 .
   ```

2. **Use restart policy:**
   ```yaml
   restart: unless-stopped
   ```

3. **Configure logging:**
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

4. **Monitor container health:**
   ```bash
   docker-compose ps
   docker stats microcenter-watcher
   ```

### Deploying to a server

```bash
# On your server
git clone <repository>
cd microcenter-product-watcher

# Configure environment
cp .env.example .env
nano .env  # Add your bot token

# Create data directory
mkdir data

# Start container
docker-compose up -d

# Enable automatic restart on server reboot
# (handled by restart: unless-stopped in docker-compose.yml)
```

### Running as a system service

For servers without Docker Compose, create a systemd service:

```ini
# /etc/systemd/system/microcenter-watcher.service
[Unit]
Description=Microcenter Product Watcher
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/microcenter-product-watcher
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable microcenter-watcher
sudo systemctl start microcenter-watcher
```

## Resource Usage

Typical resource consumption:
- **Memory:** ~100-150 MB
- **CPU:** Minimal (periodic checks only)
- **Disk:** ~10 MB (code) + database size (~1 MB per 1000 products)
- **Network:** Minimal (HTTP requests for checking products)

## Security Considerations

1. **Protect your `.env` file:**
   - Never commit to version control
   - Secure with proper file permissions: `chmod 600 .env`

2. **Keep bot token secret:**
   - Don't share in logs or screenshots
   - Regenerate if compromised

3. **Regular updates:**
   ```bash
   git pull
   docker-compose build --no-cache
   docker-compose up -d
   ```

4. **Network isolation:**
   - Bot only needs outbound internet access
   - No ports need to be exposed

## Advanced Configuration

### Using named volumes instead of bind mounts

Edit `docker-compose.yml`:

```yaml
volumes:
  - microcenter-data:/app/data

volumes:
  microcenter-data:
    driver: local
```

Benefits:
- Managed by Docker
- Better performance on some systems
- Easier to backup with Docker tools

### Multi-stage builds for smaller images

For production, consider a multi-stage Dockerfile to reduce image size.

### Running multiple instances

To run multiple bots (different tokens):

```bash
# Create separate directories
cp -r microcenter-product-watcher bot1
cp -r microcenter-product-watcher bot2

# Configure each with different tokens
cd bot1 && nano .env
cd ../bot2 && nano .env

# Start both
cd bot1 && docker-compose up -d
cd ../bot2 && docker-compose up -d
```
