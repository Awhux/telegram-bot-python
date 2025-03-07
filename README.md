# Twitter/X Notifications Telegram Bot

A Telegram bot for receiving personalized Twitter/X notifications based on user interests.

## Features

- User registration with interest keywords
- Automatic group assignment and invitation
- Interest-based tweet filtering
- SQLite database for efficient data storage
- Automatic database backups
- Admin commands for user management
- Webhook support for Twitter/X notifications

## Setup

1. Clone this repository
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
4. Edit the `.env` file with your configuration:
   - Add your Telegram Bot Token
   - Set your webhook URL
   - Add admin Telegram chat IDs

## Running the Bot

To run the bot:

```bash
python main.py
```

For production, it's recommended to use a process manager like Supervisor.

## Webhook Setup

The bot uses webhooks for both Telegram updates and tweet notifications. Set up your webhook URL in the `.env` file.

For receiving Twitter/X notifications, you can use IFTTT or similar services to send POST requests to your webhook endpoint.

## Admin Commands

- `/admin` - Access admin panel
- `/stats` - Show bot statistics
- `/adminbackup` - Create database backup
- `/broadcast` - Send message to all users
- `/export` - Export user data to JSON
- `/finduser` - Find a user by ID or name
- `/addgroup` - Add a new group to the database
- `/debug` - Show debug information
- `/removeuser` - Remove a user by chat ID

## User Commands

- `/start` - Start the bot and register
- `/status` - Show current profile status
- `/update` - Update interests
- `/help` - Show available commands
- `/myid` - Show your Telegram chat ID

## Database

The bot uses SQLite for data storage. The database file is specified in the `.env` file and defaults to `bot_database.db`.

Automatic backups are created in the `backups` directory.

## Security Notes

- Keep your `.env` file secure
- Regularly backup your database
- Add only trusted users as admins