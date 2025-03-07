import json
import logging
import hashlib
from flask import Flask, request, jsonify
import telebot

from config import WEBHOOK_URL
from database import Database
from bot_handlers import bot, send_tweet_to_group

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize database
db = Database()

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handle webhook requests from Telegram and IFTTT.
    This endpoint processes both Telegram updates and tweet notifications.
    """
    try:
        # Try to get raw data from the request
        raw_data = request.get_data().decode('utf-8')
        
        # Check if it's a Telegram update (has 'update_id')
        try:
            data = json.loads(raw_data)
            if isinstance(data, dict) and 'update_id' in data:
                # Process Telegram update
                logger.debug("Received Telegram update")
                update = telebot.types.Update.de_json(raw_data)
                bot.process_new_updates([update])
                return 'OK', 200
        except json.JSONDecodeError:
            # Not a JSON payload, might be form data from IFTTT
            pass
        
        # If it's not a Telegram update, try to process as a tweet notification
        return process_tweet_notification(request)
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500

def process_tweet_notification(request):
    """Process a tweet notification from IFTTT."""
    # Get parameters from the request
    tweet_link = request.form.get('link')
    tweet_text = request.form.get('text')
    tweet_id = request.form.get('id')  # Optional
    
    # Validate required fields
    if not tweet_link or not tweet_text:
        logger.warning("Missing required fields in tweet notification")
        return jsonify({"error": "Fields 'link' and 'text' are required"}), 400
    
    # Generate an ID if none provided
    if not tweet_id:
        tweet_id = hashlib.md5(f"{tweet_link}:{tweet_text}".encode()).hexdigest()
    
    # Check if we've already processed this tweet
    if db.is_tweet_processed(tweet_id):
        logger.info(f"Tweet {tweet_id} already processed, skipping")
        return jsonify({"message": "Tweet already processed"}), 200
    
    # Log the received tweet
    logger.info(f"Received tweet notification: {tweet_id}")
    logger.debug(f"Tweet text: {tweet_text}")
    logger.debug(f"Tweet link: {tweet_link}")
    
    # Find users whose keywords match the tweet
    tweet_text_lower = tweet_text.lower()
    users = db.find_users_by_keywords(tweet_text)
    
    # Counter for successful deliveries
    delivery_count = 0
    
    # Send tweet to matching groups
    processed_groups = set()  # To avoid duplicate notifications
    for user in users:
        group_id = user.get('group_id')
        
        # Skip if no group or already processed
        if not group_id or group_id in processed_groups:
            continue
        
        # Try to send tweet to group
        if send_tweet_to_group(group_id, tweet_text, tweet_link):
            delivery_count += 1
            processed_groups.add(group_id)
    
    # Save the tweet as processed
    db.add_tweet(tweet_id, tweet_text, tweet_link)
    
    # Return success response
    return jsonify({
        "message": "Tweet processed successfully",
        "delivery_count": delivery_count,
        "matching_users": len(users),
        "unique_groups": len(processed_groups)
    }), 200

def setup_webhook(url=None):
    """Set up the webhook for the Telegram bot."""
    webhook_url = url or WEBHOOK_URL
    
    try:
        # Remove any existing webhook
        bot.remove_webhook()
        
        # Set the new webhook
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
        return True
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return False

def remove_webhook():
    """Remove the webhook from the Telegram bot."""
    try:
        bot.remove_webhook()
        logger.info("Webhook removed")
        return True
    except Exception as e:
        logger.error(f"Failed to remove webhook: {e}")
        return False