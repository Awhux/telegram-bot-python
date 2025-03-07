import logging
import os
import json
from datetime import datetime
from telebot import types

from config import ADMIN_IDS, MESSAGES
from database import Database
from bot_handlers import bot

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

class AdminCommands:
    """Admin command handlers and utilities."""
    
    @staticmethod
    def is_admin(user_id):
        """Check if a user is an admin."""
        return str(user_id) in ADMIN_IDS
    
    @staticmethod
    def require_admin(func):
        """Decorator to require admin privileges for a function."""
        def wrapper(message, *args, **kwargs):
            if not AdminCommands.is_admin(message.from_user.id):
                bot.reply_to(message, MESSAGES["admin_only"])
                return
            return func(message, *args, **kwargs)
        return wrapper
    
    @staticmethod
    @require_admin
    def stats(message):
        """Show bot statistics."""
        try:
            # Get database statistics
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Count users
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                # Count groups
                cursor.execute("SELECT COUNT(*) FROM groups")
                group_count = cursor.fetchone()[0]
                
                # Count keywords
                cursor.execute("SELECT COUNT(*) FROM keywords")
                keyword_count = cursor.fetchone()[0]
                
                # Count tweets
                cursor.execute("SELECT COUNT(*) FROM tweets")
                tweet_count = cursor.fetchone()[0]
                
                # Get active users (with groups)
                cursor.execute("SELECT COUNT(*) FROM users WHERE group_id IS NOT NULL AND group_id != ''")
                active_user_count = cursor.fetchone()[0]
                
                # Get unique keywords
                cursor.execute("SELECT COUNT(DISTINCT keyword) FROM keywords")
                unique_keyword_count = cursor.fetchone()[0]
                
                # Get database file size
                db_size = os.path.getsize(db.db_file) / (1024 * 1024)  # Size in MB
            
            # Format stats message
            stats_message = "📊 *Estatísticas do Bot*\n\n"
            stats_message += f"👥 *Usuários:* {user_count}\n"
            stats_message += f"👥 *Usuários Ativos:* {active_user_count}\n"
            stats_message += f"👥 *Grupos:* {group_count}\n"
            stats_message += f"🔑 *Palavras-chave:* {keyword_count}\n"
            stats_message += f"🔑 *Palavras-chave Únicas:* {unique_keyword_count}\n"
            stats_message += f"🐦 *Tweets Processados:* {tweet_count}\n"
            stats_message += f"💾 *Tamanho do Banco de Dados:* {db_size:.2f} MB\n"
            
            # Send stats message
            bot.send_message(
                message.chat.id,
                stats_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error generating stats: {e}")
            bot.reply_to(message, "Erro ao gerar estatísticas.")
    
    @staticmethod
    @require_admin
    def backup(message):
        """Create database backup."""
        backup_file = db.backup_database()
        if backup_file:
            bot.reply_to(
                message,
                MESSAGES["backup_success"].format(backup_file=backup_file)
            )
        else:
            bot.reply_to(message, "❌ Falha ao criar backup do banco de dados.")
    
    @staticmethod
    @require_admin
    def broadcast(message):
        """Broadcast a message to all users."""
        # Extract command text
        command_parts = message.text.split(' ', 1)
        if len(command_parts) < 2:
            bot.reply_to(message, "❓ Uso: /broadcast MENSAGEM")
            return
        
        broadcast_text = command_parts[1].strip()
        
        # Get all users
        users = db.list_users()
        
        # Counter for successful sends
        success_count = 0
        fail_count = 0
        
        # Start broadcast
        status_message = bot.reply_to(
            message,
            f"🔄 Iniciando broadcast para {len(users)} usuários..."
        )
        
        # Send messages
        for i, user in enumerate(users):
            try:
                # Send message
                bot.send_message(
                    user['chat_id'],
                    f"📢 *Anúncio do Administrador*\n\n{broadcast_text}",
                    parse_mode="Markdown"
                )
                success_count += 1
                
                # Update status every 10 users
                if i % 10 == 0:
                    bot.edit_message_text(
                        f"🔄 Broadcast em andamento... {i+1}/{len(users)}",
                        chat_id=status_message.chat.id,
                        message_id=status_message.message_id
                    )
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user['chat_id']}: {e}")
                fail_count += 1
        
        # Final status
        bot.edit_message_text(
            f"✅ Broadcast concluído!\n\n"
            f"✓ Enviados: {success_count}\n"
            f"❌ Falhas: {fail_count}",
            chat_id=status_message.chat.id,
            message_id=status_message.message_id
        )
    
    @staticmethod
    @require_admin
    def export_users(message):
        """Export users to JSON file."""
        try:
            # Get all users with keywords
            users = db.list_users(with_keywords=True)
            
            # Create export directory if it doesn't exist
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_dir}/users_export_{timestamp}.json"
            
            # Write JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            
            # Send file
            with open(filename, 'rb') as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"✅ Exportação concluída: {len(users)} usuários"
                )
        except Exception as e:
            logger.error(f"Error exporting users: {e}")
            bot.reply_to(message, "❌ Erro ao exportar usuários.")
    
    @staticmethod
    @require_admin
    def find_user(message):
        """Find a user by ID or name."""
        # Extract search term
        command_parts = message.text.split(' ', 1)
        if len(command_parts) < 2:
            bot.reply_to(message, "❓ Uso: /finduser TERMO_DE_BUSCA")
            return
        
        search_term = command_parts[1].strip().lower()
        
        # Get all users
        users = db.list_users(with_keywords=True)
        
        # Filter users
        found_users = []
        for user in users:
            if (search_term in user['name'].lower() or
                search_term in user['email'].lower() or
                search_term == user['chat_id']):
                found_users.append(user)
        
        if not found_users:
            bot.reply_to(message, "❌ Nenhum usuário encontrado.")
            return
        
        # Format results
        result_message = f"🔍 *Usuários Encontrados ({len(found_users)})*\n\n"
        
        for i, user in enumerate(found_users):
            # Format keywords
            keywords_str = ", ".join(user['keywords']) if 'keywords' in user and user['keywords'] else "Nenhum"
            
            result_message += f"{i+1}. *{user['name']}*\n"
            result_message += f"   ID: `{user['chat_id']}`\n"
            result_message += f"   Email: {user['email']}\n"
            result_message += f"   Interesses: {keywords_str}\n"
            result_message += f"   Grupo: {user['group_id'] or 'Não atribuído'}\n\n"
        
        # Send results
        bot.send_message(
            message.chat.id,
            result_message,
            parse_mode="Markdown"
        )
    
    @staticmethod
    @require_admin
    def add_group(message):
        """Add a new group to the database."""
        # Extract group ID
        command_parts = message.text.split(' ', 1)
        if len(command_parts) < 2:
            bot.reply_to(message, "❓ Uso: /addgroup GROUP_ID")
            return
        
        group_id = command_parts[1].strip()
        
        # Add group
        group_id = db.add_group(group_id)
        if group_id:
            bot.reply_to(message, f"✅ Grupo adicionado com ID: {group_id}")
        else:
            bot.reply_to(message, "❌ Falha ao adicionar grupo.")
    
    @staticmethod
    @require_admin
    def debug(message):
        """Print debug information."""
        try:
            # System info
            import platform
            import psutil
            import time
            
            # Get memory usage
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / (1024 * 1024)  # Memory in MB
            
            # Get uptime
            uptime = time.time() - process.create_time()
            uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
            
            # Debug message
            debug_message = "🔧 *Informações de Debug*\n\n"
            debug_message += f"🖥️ *Sistema:* {platform.system()} {platform.release()}\n"
            debug_message += f"🐍 *Python:* {platform.python_version()}\n"
            debug_message += f"⏱️ *Uptime:* {uptime_str}\n"
            debug_message += f"💾 *Uso de Memória:* {memory_usage:.2f} MB\n"
            debug_message += f"🔢 *PID:* {os.getpid()}\n"
            debug_message += f"📂 *Diretório:* {os.getcwd()}\n"
            
            # Send debug info
            bot.send_message(
                message.chat.id,
                debug_message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error generating debug info: {e}")
            bot.reply_to(message, f"❌ Erro ao gerar informações de debug: {e}")

# Register command handlers
def register_admin_commands():
    """Register admin command handlers with the bot."""
    bot.message_handler(commands=['stats'])(AdminCommands.stats)
    bot.message_handler(commands=['adminbackup'])(AdminCommands.backup)
    bot.message_handler(commands=['broadcast'])(AdminCommands.broadcast)
    bot.message_handler(commands=['export'])(AdminCommands.export_users)
    bot.message_handler(commands=['finduser'])(AdminCommands.find_user)
    bot.message_handler(commands=['addgroup'])(AdminCommands.add_group)
    bot.message_handler(commands=['debug'])(AdminCommands.debug)