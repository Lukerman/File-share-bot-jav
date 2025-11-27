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
Clone repositorygit clone https://github.com/yourusername/code-file-provider.git
cd code-file-providerCopy environment filecp .env.example .envEdit configuration (see Configuration section)nano .envBuild and start servicesdocker-compose up -dView logsdocker-compose logs -f main_bot
docker-compose logs -f file_botStop servicesdocker-compose down

### Option 2: Manual Installation
Clone repositorygit clone https://github.com/yourusername/code-file-provider.git
cd code-file-providerCreate virtual environmentpython3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activateInstall dependenciespip install -r requirements.txtInstall MongoDBUbuntu/Debian:wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongodConfigure environmentcp .env.example .env
nano .envRun bots (use separate terminals or tmux/screen)python -m main_bot.bot
python -m file_bot.bot


## ⚙️ Configuration

### Environment Variables

Create `.env` file with the following variables:

Telegram Bot TokensMAIN_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz  # From @BotFather
FILE_BOT_TOKEN=987654321:ZYXwvuTSRqponMLKjihGFEdcba  # Separate bot for deliveryMongoDB ConfigurationMONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=file_provider_dbAdmin ConfigurationMAIN_ADMIN_ID=123456789  # Your Telegram user ID
DATABASE_CHANNEL_ID=-1001234567890  # Private channel for file storage
REQUEST_CHANNEL_ID=-1001234567891  # Channel for request notificationsMini WebApp ConfigurationMINI_WEBAPP_URL=https://yourdomain.com/miniapp  # Full URL to PHP webappSecurityMASTER_SECRET_KEY=generate_random_32_byte_hex_string_hereOptional: LoggingLOG_LEVEL=INFO
Mini WebApp ConfigurationMINI_WEBAPP_URL=https://yourdomain.com/miniapp  # Full URL to PHP webappSecurityMASTER_SECRET_KEY=generate_random_32_byte_hex_string_hereOptional: LoggingLOG_LEVEL=INFO
