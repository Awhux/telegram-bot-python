import time
import logging
import threading
from datetime import datetime

from config import DB_POLL_INTERVAL
from database import Database
from bot_handlers import generate_invite_link, send_invite

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

class GroupMonitor:
    """Monitor groups and handle group assignment to users."""
    
    def __init__(self, poll_interval=DB_POLL_INTERVAL):
        """Initialize the group monitor."""
        self.poll_interval = poll_interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the group monitoring thread."""
        if self.running:
            logger.warning("Group monitor already running")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        logger.info("Group monitor started")
        return True
    
    def stop(self):
        """Stop the group monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        
        logger.info("Group monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._process_groups()
            except Exception as e:
                logger.error(f"Error in group monitor: {e}")
            
            # Sleep for the specified interval
            time.sleep(self.poll_interval)
    
    def _process_groups(self):
        """Process groups that need to be completed with information."""
        logger.debug("Checking for incomplete groups...")
        
        # Get groups that need completion
        incomplete_groups = db.get_incomplete_groups()
        
        if not incomplete_groups:
            logger.debug("No incomplete groups found")
            return
        
        logger.info(f"Found {len(incomplete_groups)} incomplete groups")
        
        for group in incomplete_groups:
            group_id = group['group_id']
            
            # Skip if the group has a name and invite link
            if group['group_name'] and group['invite_link']:
                continue
            
            logger.info(f"Processing incomplete group: {group_id}")
            
            # Find a user who hasn't been assigned a group
            user = db.get_user_without_group()
            if not user:
                logger.info("No available users for group assignment")
                break
            
            # Generate permanent invite link
            invite_link = generate_invite_link(group_id)
            if not invite_link:
                logger.error(f"Failed to generate invite link for group {group_id}")
                continue
            
            # Format keywords for group name
            keywords = ', '.join(user['keywords'][:3]) if user['keywords'] else 'Geral'
            group_name = f"Grupo de {user['name']} - {keywords}"
            
            # Update group information
            if db.update_group(group_id, group_name, invite_link):
                logger.info(f"Updated group {group_id} with name '{group_name}'")
            else:
                logger.error(f"Failed to update group {group_id}")
                continue
            
            # Update user with the group assignment
            if db.update_user_group(user['chat_id'], group_id, group_name, invite_link):
                logger.info(f"Assigned group {group_id} to user {user['name']}")
            else:
                logger.error(f"Failed to update user {user['name']} with group {group_id}")
                continue
            
            # Send invite link to the user
            if send_invite(user['chat_id'], invite_link):
                logger.info(f"Sent invite link to user {user['name']}")
            else:
                logger.error(f"Failed to send invite link to user {user['name']}")

def process_group(group_id, force_update=False):
    """
    Process a specific group manually.
    This can be called from other parts of the application.
    """
    try:
        logger.info(f"Processing group {group_id} (force_update={force_update})")
        
        # Check if group exists
        group = None
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM groups WHERE group_id = ?", (group_id,))
            group = cursor.fetchone()
        
        if not group:
            # Add new group
            db.add_group(group_id)
            logger.info(f"Added new group {group_id}")
        elif force_update or not group['invite_link']:
            # Generate new invite link
            invite_link = generate_invite_link(group_id)
            if invite_link:
                db.update_group(group_id, group['group_name'], invite_link)
                logger.info(f"Updated group {group_id} with new invite link")
        
        return True
    except Exception as e:
        logger.error(f"Error processing group {group_id}: {e}")
        return False

# Create a singleton instance
monitor = GroupMonitor()