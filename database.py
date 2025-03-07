import sqlite3
import os
import json
import time
import logging
import shutil
from datetime import datetime
from contextlib import contextmanager
from threading import Lock

# Initialize logger
logger = logging.getLogger(__name__)

class Database:
    """
    Database manager for the Telegram bot.
    Handles all database operations with SQLite.
    """
    
    # SQL statements
    SQL_CREATE_USERS_TABLE = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        chat_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        intention TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        group_id TEXT,
        group_name TEXT,
        invite_link TEXT
    );"""
    
    SQL_CREATE_GROUPS_TABLE = """
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        group_id TEXT NOT NULL UNIQUE,
        group_name TEXT,
        invite_link TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );"""
    
    SQL_CREATE_KEYWORDS_TABLE = """
    CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        keyword TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE(user_id, keyword)
    );"""
    
    SQL_CREATE_ADMINS_TABLE = """
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL UNIQUE,
        added_at TEXT NOT NULL
    );"""
    
    SQL_CREATE_TWEETS_TABLE = """
    CREATE TABLE IF NOT EXISTS tweets (
        id INTEGER PRIMARY KEY,
        tweet_id TEXT UNIQUE,
        tweet_text TEXT NOT NULL,
        tweet_link TEXT NOT NULL,
        processed_at TEXT NOT NULL
    );"""
    
    def __init__(self, db_file="bot_database.db"):
        """Initialize the database manager."""
        self.db_file = db_file
        self.connection = None
        self.db_lock = Lock()  # Lock for thread safety
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        with self.db_lock:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            try:
                yield conn
            finally:
                conn.close()
    
    def init_db(self):
        """Initialize the database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Create tables
            cursor.execute(self.SQL_CREATE_USERS_TABLE)
            cursor.execute(self.SQL_CREATE_GROUPS_TABLE)
            cursor.execute(self.SQL_CREATE_KEYWORDS_TABLE)
            cursor.execute(self.SQL_CREATE_ADMINS_TABLE)
            cursor.execute(self.SQL_CREATE_TWEETS_TABLE)
            
            # Create index for faster keyword searches
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);")
            conn.commit()
            
            # Add default admin if needed (adjust with your admin's user ID)
            self.add_admin_if_not_exists("YOUR_ADMIN_ID")
            
            logger.info("Database initialized successfully")
    
    def add_admin_if_not_exists(self, admin_id):
        """Add a default admin if no admins exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM admins")
            count = cursor.fetchone()[0]
            
            if count == 0 and admin_id != "YOUR_ADMIN_ID":
                now = datetime.now().isoformat()
                cursor.execute(
                    "INSERT INTO admins (user_id, added_at) VALUES (?, ?)",
                    (admin_id, now)
                )
                conn.commit()
                logger.info(f"Added default admin: {admin_id}")
    
    def backup_database(self):
        """Create a backup of the database file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = "backups"
            
            # Create backup directory if it doesn't exist
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            backup_file = f"{backup_dir}/backup_{timestamp}.db"
            
            # Ensure the database is not being written to during backup
            with self.db_lock:
                shutil.copy2(self.db_file, backup_file)
            
            # Remove old backups (keep only last 5)
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("backup_")])
            if len(backups) > 5:
                for old_backup in backups[:-5]:
                    os.remove(f"{backup_dir}/{old_backup}")
            
            logger.info(f"Database backed up successfully to {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return None
    
    def restore_database(self, backup_file):
        """Restore the database from a backup file."""
        try:
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Ensure the database is not being accessed during restore
            with self.db_lock:
                shutil.copy2(backup_file, self.db_file)
            
            logger.info(f"Database restored successfully from {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False

    # User operations
    def add_user(self, chat_id, name, email, intention, keywords):
        """Add a new user with their interests."""
        try:
            now = datetime.now().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert user
                cursor.execute(
                    """INSERT INTO users 
                       (chat_id, name, email, intention, created_at, updated_at) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (chat_id, name, email, intention, now, now)
                )
                
                user_id = cursor.lastrowid
                
                # Insert keywords
                keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
                for keyword in keyword_list:
                    cursor.execute(
                        "INSERT INTO keywords (user_id, keyword, created_at) VALUES (?, ?, ?)",
                        (user_id, keyword.lower(), now)
                    )
                
                conn.commit()
                logger.info(f"Added new user: {name} (ID: {user_id})")
                return user_id
        except sqlite3.IntegrityError:
            logger.warning(f"User with chat_id {chat_id} already exists")
            return None
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return None
    
    def get_user_by_chat_id(self, chat_id):
        """Get user information by chat ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            user = cursor.fetchone()
            
            if user:
                # Get user's keywords
                cursor.execute("SELECT keyword FROM keywords WHERE user_id = ?", (user['id'],))
                keywords = [row['keyword'] for row in cursor.fetchall()]
                
                # Convert to dict and add keywords
                user_dict = dict(user)
                user_dict['keywords'] = keywords
                return user_dict
            
            return None
    
    def remove_user(self, chat_id):
        """Remove a user and their keywords."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get user ID first
                cursor.execute("SELECT id FROM users WHERE chat_id = ?", (chat_id,))
                user = cursor.fetchone()
                
                if not user:
                    return False
                
                # Delete user and related keywords (cascading should handle this)
                cursor.execute("DELETE FROM users WHERE chat_id = ?", (chat_id,))
                conn.commit()
                
                logger.info(f"Removed user with chat_id: {chat_id}")
                return True
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            return False
    
    def list_users(self, with_keywords=False):
        """List all users, optionally with their keywords."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            users = [dict(row) for row in cursor.fetchall()]
            
            if with_keywords:
                for user in users:
                    cursor.execute("SELECT keyword FROM keywords WHERE user_id = ?", (user['id'],))
                    user['keywords'] = [row['keyword'] for row in cursor.fetchall()]
            
            return users
    
    def update_user_group(self, chat_id, group_id, group_name, invite_link):
        """Update user's assigned group."""
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE users SET 
                   group_id = ?, group_name = ?, invite_link = ?, updated_at = ? 
                   WHERE chat_id = ?""",
                (group_id, group_name, invite_link, now, chat_id)
            )
            conn.commit()
            
            return cursor.rowcount > 0
    
    # Group operations
    def add_group(self, group_id, group_name=None, invite_link=None):
        """Add a new group."""
        try:
            now = datetime.now().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO groups 
                       (group_id, group_name, invite_link, created_at, updated_at) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (group_id, group_name, invite_link, now, now)
                )
                conn.commit()
                
                logger.info(f"Added new group: {group_id}")
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Group with ID {group_id} already exists")
            return None
        except Exception as e:
            logger.error(f"Error adding group: {e}")
            return None
    
    def update_group(self, group_id, group_name, invite_link):
        """Update group information."""
        now = datetime.now().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE groups SET 
                   group_name = ?, invite_link = ?, updated_at = ? 
                   WHERE group_id = ?""",
                (group_name, invite_link, now, group_id)
            )
            conn.commit()
            
            return cursor.rowcount > 0
    
    def get_incomplete_groups(self):
        """Get groups that need to be completed with information."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM groups 
                   WHERE group_name IS NULL OR group_name = '' 
                   OR invite_link IS NULL OR invite_link = ''"""
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_without_group(self):
        """Get a user who hasn't been assigned a group yet."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM users 
                   WHERE group_id IS NULL OR group_id = '' 
                   ORDER BY created_at ASC LIMIT 1"""
            )
            user = cursor.fetchone()
            
            if user:
                cursor.execute("SELECT keyword FROM keywords WHERE user_id = ?", (user['id'],))
                keywords = [row['keyword'] for row in cursor.fetchall()]
                
                user_dict = dict(user)
                user_dict['keywords'] = keywords
                return user_dict
            
            return None
    
    # Admin operations
    def is_admin(self, user_id):
        """Check if a user is an admin."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM admins WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None
    
    def add_admin(self, user_id):
        """Add a new admin."""
        try:
            now = datetime.now().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO admins (user_id, added_at) VALUES (?, ?)",
                    (user_id, now)
                )
                conn.commit()
                
                logger.info(f"Added new admin: {user_id}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Admin with user_id {user_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Error adding admin: {e}")
            return False
    
    def remove_admin(self, user_id):
        """Remove an admin."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    # Tweet operations
    def add_tweet(self, tweet_id, tweet_text, tweet_link):
        """Add a processed tweet to avoid duplicates."""
        try:
            now = datetime.now().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO tweets 
                       (tweet_id, tweet_text, tweet_link, processed_at) 
                       VALUES (?, ?, ?, ?)""",
                    (tweet_id, tweet_text, tweet_link, now)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Tweet already processed
            return False
        except Exception as e:
            logger.error(f"Error adding tweet: {e}")
            return False
    
    def is_tweet_processed(self, tweet_id):
        """Check if a tweet has already been processed."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tweets WHERE tweet_id = ?", (tweet_id,))
            return cursor.fetchone() is not None
    
    def find_users_by_keywords(self, tweet_text):
        """Find users whose keywords match the tweet text."""
        tweet_text_lower = tweet_text.lower()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all keywords first (optimization to avoid checking each user)
            cursor.execute("SELECT DISTINCT keyword FROM keywords")
            all_keywords = [row['keyword'] for row in cursor.fetchall()]
            
            # Find matching keywords in the tweet
            matching_keywords = [kw for kw in all_keywords if kw in tweet_text_lower]
            
            if not matching_keywords:
                return []
            
            # Get users who have these keywords
            placeholders = ','.join(['?'] * len(matching_keywords))
            cursor.execute(
                f"""SELECT DISTINCT u.* FROM users u
                   JOIN keywords k ON u.id = k.user_id
                   WHERE k.keyword IN ({placeholders})
                   AND u.group_id IS NOT NULL AND u.group_id != ''""",
                matching_keywords
            )
            
            matching_users = [dict(row) for row in cursor.fetchall()]
            return matching_users