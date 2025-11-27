# Code-Based File Provider Ecosystem

A production-ready Telegram bot system for secure file distribution using resource codes, rewarded ads, and cryptographic token verification.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)

## 🌟 Features

### Core Functionality
- **🔍 Smart Code Detection**: Automatically detects resource codes in any format with fuzzy matching
- **🎯 Lazy Search**: Typo-tolerant search with intelligent suggestions
- **📮 Request System**: Users can request unavailable files with automatic fulfillment
- **🔐 Secure Tokens**: HMAC-signed permanent tokens with single-use enforcement
- **🎬 Rewarded Ads**: Monetization through stateless Mini WebApp integration
- **📦 Version Control**: Multiple file versions with independent management
- **🏢 Group Management**: Automatic approval for main admin, strict authorization

### Security Features
- **Atomic Operations**: Race-condition-free token redemption using MongoDB `find_one_and_update`
- **HMAC Signatures**: Per-file secrets with SHA-256 signing
- **Spam Protection**: Progressive cooldowns, rate limiting, auto-ban system
- **Input Validation**: Comprehensive sanitization and format checking

### Admin Features
- **📊 Statistics Dashboard**: Real-time system metrics
- **👥 User Management**: Ban/unban, warning system, activity tracking
- **📁 File Management**: Upload, delete, rotate secrets, manage versions
- **🔐 Token Control**: View usage, revoke tokens, regenerate secrets

## 📋 Table of Contents

- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🏗️ Architecture

### System Components

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│             │         │              │         │             │
│  Main Bot   │────────▶│   MongoDB    │◀────────│  File Bot   │
│  (Search)   │         │  (Database)  │         │ (Delivery)  │
│             │         │              │         │             │
└──────┬──────┘         └──────────────┘         └──────▲──────┘
       │                                                 │
       │                ┌──────────────┐                │
       │                │              │                │
       └───────────────▶│  Mini WebApp │────────────────┘
                        │ (Rewarded Ad)│
                        │              │
                        └──────────────┘
```

### Data Flow

1. **Search Flow**: User → Main Bot → MongoDB → Lazy Search → Results
2. **Unlock Flow**: User → Token Generation → Mini WebApp → Ad Display → FileBot
3. **Delivery Flow**: FileBot → Token Verification → MongoDB → File Delivery
4. **Upload Flow**: Admin → Database Channel → Parser → MongoDB → Request Fulfillment

## 💻 Requirements

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL
- **Python**: 3.11 or higher
- **MongoDB**: 7.0 or higher
- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: Minimum 10GB free space

### External Services
- **Telegram Bot API**: Two bot tokens (Main Bot + File Bot)
- **MongoDB Atlas** (optional): For cloud database
- **PHP Hosting**: For Mini WebApp (InfinityFree, 000webhost, or VPS)
- **Ad Network**: Libtl.com account with rewarded interstitial zone

## 🚀 Installation

### Option 1: Docker Deployment (Recommended)

```
# Clone repository
git clone https://github.com/yourusername/code-file-provider.git
cd code-file-provider

# Copy environment file
cp .env.example .env

# Edit configuration (see Configuration section)
nano .env

# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f main_bot
docker-compose logs -f file_bot

# Stop services
docker-compose down
```

### Option 2: Manual Installation

```
# Clone repository
git clone https://github.com/yourusername/code-file-provider.git
cd code-file-provider

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install MongoDB
# Ubuntu/Debian:
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Configure environment
cp .env.example .env
nano .env

# Run bots (use separate terminals or tmux/screen)
python -m main_bot.bot
python -m file_bot.bot
```

## ⚙️ Configuration

### Environment Variables

Create `.env` file with the following variables:

```
# Telegram Bot Tokens
MAIN_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz  # From @BotFather
FILE_BOT_TOKEN=987654321:ZYXwvuTSRqponMLKjihGFEdcba  # Separate bot for delivery

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=file_provider_db

# Admin Configuration
MAIN_ADMIN_ID=123456789  # Your Telegram user ID
DATABASE_CHANNEL_ID=-1001234567890  # Private channel for file storage
REQUEST_CHANNEL_ID=-1001234567891  # Channel for request notifications

# Mini WebApp Configuration
MINI_WEBAPP_URL=https://yourdomain.com/miniapp  # Full URL to PHP webapp

# Security
MASTER_SECRET_KEY=generate_random_32_byte_hex_string_here

# Optional: Logging
LOG_LEVEL=INFO
```

### Getting Required IDs

**Your Telegram User ID:**
```
1. Message @userinfobot on Telegram
2. Copy the ID number
```

**Channel IDs:**
```
1. Create two private channels
2. Add your bot as admin to both
3. Forward a message from each channel to @userinfobot
4. Copy the channel IDs (they start with -100)
```

**Generate Secret Key:**
```
python -c "import secrets; print(secrets.token_hex(32))"
```

### Mini WebApp Setup

1. **Upload to PHP hosting** (InfinityFree, 000webhost, or your VPS):
```
# Upload mini_webapp/index.php and mini_webapp/.htaccess
```

2. **Get Ad Zone ID** from [Libtl.com](https://libtl.com):
   - Sign up and create a rewarded interstitial zone
   - Replace `10242377` in `index.php` with your zone ID

3. **Update FileBot username** in `index.php`:
```
const filebot_url = `https://t.me/YOUR_FILE_BOT_USERNAME?start=${token}`;
```

## 🎯 Usage

### For Users

**Searching for files:**
```
Send: ABC-123
Bot responds with availability and unlock option
```

**Requesting files:**
```
If file not found, click "Request" button
You'll be notified when it's uploaded
```

**Unlocking files:**
```
1. Click "Get File" button
2. Watch ~15-30 second ad
3. Receive file automatically in FileBot
```

### For Admins

**Uploading files:**
```
1. Go to Database Channel
2. Upload file with caption: CODE VERSION
   Example: ABC-123 v1.0
3. Bot processes automatically and notifies requesters
```

**Admin panel:**
```
/adminpanel - Access full control panel
```

**Approving groups:**
```
1. Add bot to group
2. Run: /approvegroup
```

**Managing admins:**
```
Admin Panel → Manage Admins → Add/Remove
```

## 📚 API Reference

### Main Bot Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/start` | All | Welcome message and basic info |
| `/help` | All | Comprehensive usage guide |
| `/adminpanel` | Admin | Access admin control panel |
| `/approvegroup` | Main Admin | Approve current group |

### Callback Data Formats

```
# Search callbacks
"view_{code}"                 # View resource details
"unlock_{code}_{version}"     # Generate unlock token
"request_{code}"              # Request unavailable file

# Admin callbacks
"admin_stats"                 # View statistics
"admin_files"                 # File management
"admin_requests"              # View pending requests
"admin_tokens"                # Token management
"admin_admins"                # Admin management
"admin_groups"                # Group management
"admin_bans"                  # Banned users
```

### Database Collections

**videos**
```
{
  "code": "ABC-123",              // Normalized resource code
  "versions": [                   // Array of file versions
    {
      "version": "1.0",
      "file_id": "BQACAgEAAxkB...",
      "file_type": "document",
      "file_size": 12345678,
      "file_name": "file.pdf",
      "uploaded_by": 123456789,
      "uploaded_at": ISODate("...")
    }
  ],
  "file_secret": "hex_string",    // Per-file HMAC secret
  "description": "Description",
  "created_at": ISODate("..."),
  "updated_at": ISODate("..."),
  "total_downloads": 0,
  "active": true
}
```

**tokens**
```
{
  "token": "base64.signature",    // Full signed token
  "resource_id": "ABC-123",
  "version": "1.0",
  "nonce": "random_string",
  "used": false,                  // Single-use flag
  "used_at": null,
  "used_by": null,
  "created_at": ISODate("...")
}
```

## 🧪 Testing

### Run All Tests

```
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_code_detector.py -v
```

### Test Categories

- **Unit Tests**: `test_code_detector.py`, `test_token_service.py`, `test_lazy_search.py`
- **Integration Tests**: Require running MongoDB instance
- **Manual Testing**: Use Telegram test environment

## 🔧 Troubleshooting

### Common Issues

**Bot doesn't respond in groups:**
```
1. Check if group is approved: /approvegroup
2. Verify bot has "Read Messages" permission
3. Check logs: docker-compose logs main_bot
```

**Token verification fails:**
```
1. Verify file_secret exists in videos collection
2. Check MongoDB connection
3. Ensure token hasn't been used
4. Verify HMAC signature matches
```

**File delivery fails:**
```
1. Confirm file_id is valid
2. Check FileBot has access to Database Channel
3. Verify user hasn't blocked FileBot
4. Review logs: docker-compose logs file_bot
```

**MongoDB connection issues:**
```
# Check MongoDB status
sudo systemctl status mongod

# Restart MongoDB
sudo systemctl restart mongod

# View MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

### Debug Mode

Enable detailed logging:
```
# In .env
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart
```

## 📊 Performance Optimization

### MongoDB Indexes
All required indexes are created automatically on startup. Verify:
```
use file_provider_db
db.videos.getIndexes()
db.tokens.getIndexes()
```

### Scaling Considerations
- **Horizontal scaling**: Run multiple bot instances with load balancer
- **Database**: Use MongoDB Atlas with replica sets
- **Caching**: Implement Redis for frequently accessed data
- **CDN**: Use Telegram's native file caching

## 🔒 Security Best Practices

1. **Never commit `.env` file** to version control
2. **Rotate MASTER_SECRET_KEY** periodically
3. **Use MongoDB authentication** in production
4. **Enable HTTPS** for Mini WebApp
5. **Monitor logs** for suspicious activity
6. **Backup database** regularly

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📞 Support

- **Documentation**: [Wiki](https://github.com/yourusername/code-file-provider/wiki)
- **Issues**: [GitHub Issues](https://github.com/yourusername/code-file-provider/issues)
- **Telegram**: @yourusername

---

**Built with ❤️ for the Telegram community**
```

***

## 17. Additional Production Files

**`run_main_bot.sh`** (Service runner script)
```bash
#!/bin/bash

# Production runner for Main Bot with auto-restart

cd "$(dirname "$0")"
source venv/bin/activate

while true; do
    echo "$(date): Starting Main Bot..."
    python -m main_bot.bot
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "$(date): Main Bot stopped gracefully"
        break
    else
        echo "$(date): Main Bot crashed with exit code $exit_code. Restarting in 5 seconds..."
        sleep 5
    fi
done
```

**`run_file_bot.sh`**
```bash
#!/bin/bash

# Production runner for File Bot with auto-restart

cd "$(dirname "$0")"
source venv/bin/activate

while true; do
    echo "$(date): Starting File Bot..."
    python -m file_bot.bot
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "$(date): File Bot stopped gracefully"
        break
    else
        echo "$(date): File Bot crashed with exit code $exit_code. Restarting in 5 seconds..."
        sleep 5
    fi
done
```

**`systemd/main-bot.service`** (Systemd service)
```ini
[Unit]
Description=File Provider Main Bot
After=network.target mongod.service
Wants=mongod.service

[Service]
Type=simple
User=botuser
WorkingDirectory=/opt/code-file-provider
Environment="PATH=/opt/code-file-provider/venv/bin"
ExecStart=/opt/code-file-provider/venv/bin/python -m main_bot.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

