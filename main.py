#!/usr/bin/env python3
"""
Twitter/X Notifications Telegram Bot

This bot allows users to receive Twitter/X notifications based on their interests.
It uses SQLite for database storage and Flask for webhook handling.
"""

import logging
import time
import signal
import sys
import os

from config import setup_logging, WEBHOOK_HOST, WEBHOOK_PORT, ADMIN_IDS
from bot_handlers import bot
from webhook import app, setup_webhook, remove_webhook
from monitor import monitor
from admin_commands import register_admin_commands
from database import Database

# Initialize main logger
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

def signal_handler(sig, frame):
    """Handle termination signals gracefully."""
    logger.info("Received termination signal. Shutting down...")
    
    # Stop monitoring thread
    monitor.stop()
    
    # Remove webhook
    remove_webhook()
    
    # Backup database before exiting
    db.backup_database()
    
    logger.info("Shutdown complete. Exiting.")
    sys.exit(0)

def setup():
    """Set up the application."""
    # Configure logging
    setup_logging()
    logger.info("Starting Twitter/X Notifications Bot")
    
    # Register admin commands
    register_admin_commands()
    logger.info("Admin commands registered")
    
    # Add default admin if specified
    if not ADMIN_IDS:
        logger.warning("No admin IDs configured. Add at least one admin ID for proper functionality.")
    
    # Start group monitor
    monitor.start()
    logger.info("Group monitor started")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set up webhook
    setup_webhook()
    logger.info("Webhook set up")
    
    # Create database backup directory if it doesn't exist
    os.makedirs("backups", exist_ok=True)
    logger.info("Backup directory created")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    logger.info("Logs directory created")
    
    logger.info("Setup complete")

def run_app():
    """Run the Flask application."""
    try:
        logger.info(f"Starting Flask app on {WEBHOOK_HOST}:{WEBHOOK_PORT}")
        app.run(host=WEBHOOK_HOST, port=WEBHOOK_PORT, use_reloader=False)
    except Exception as e:
        logger.error(f"Error starting Flask app: {e}")
        # Try to remove webhook on error
        remove_webhook()
        raise

if __name__ == "__main__":
    # Set up the application
    setup()
    
    # Run the Flask application
    run_app()