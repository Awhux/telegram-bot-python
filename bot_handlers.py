import telebot
import logging
from telebot import types
import time
from datetime import datetime

from config import TELEGRAM_BOT_TOKEN, MESSAGES, ADMIN_IDS
from database import Database

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Initialize database
db = Database()

# User states
user_states = {}

class ConversationState:
    """Enum for conversation states."""
    AWAITING_NAME = 'awaiting_name'
    AWAITING_EMAIL = 'awaiting_email'
    AWAITING_INTENTION = 'awaiting_intention'
    AWAITING_INTERESTS = 'awaiting_interests'
    AWAITING_ADMIN_COMMAND = 'awaiting_admin_command'

# Function to generate keyboard for admin commands
def get_admin_keyboard():
    """Generate a keyboard for admin commands."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    # Add buttons for admin actions
    markup.add(
        types.KeyboardButton('📊 List Users'),
        types.KeyboardButton('🔍 Find User'),
        types.KeyboardButton('🗑️ Remove User'),
        types.KeyboardButton('💾 Backup Database'),
        types.KeyboardButton('♻️ Restore Database'),
        types.KeyboardButton('❌ Cancel')
    )
    
    return markup

# Function to generate inline keyboard for backup selection
def get_backup_selection_keyboard():
    """Generate inline keyboard for selecting a backup file."""
    import os
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Check for backup files
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        markup.add(types.InlineKeyboardButton("No backups found", callback_data="no_backups"))
        return markup
    
    # List backup files, sort by date (newest first)
    backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("backup_")], reverse=True)
    
    if not backups:
        markup.add(types.InlineKeyboardButton("No backups found", callback_data="no_backups"))
        return markup
    
    # Add buttons for each backup (limit to 5)
    for backup in backups[:5]:
        # Extract date from filename for display
        date_str = backup.replace("backup_", "").replace(".db", "")
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]
        hour = date_str[9:11]
        minute = date_str[11:13]
        
        # Format date for display
        display_date = f"{day}/{month}/{year} {hour}:{minute}"
        
        markup.add(types.InlineKeyboardButton(
            f"Backup from {display_date}",
            callback_data=f"restore_{backup}"
        ))
    
    # Add cancel button
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_restore"))
    
    return markup

# Function to send a help message with command descriptions
def send_help_message(chat_id):
    """Send help message with available commands."""
    bot.send_message(
        chat_id,
        MESSAGES["help"],
        parse_mode="Markdown"
    )

# General command handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle the /start command."""
    chat_id = message.chat.id
    
    # Check if user already exists
    user = db.get_user_by_chat_id(str(chat_id))
    if user:
        # User already registered, send welcome back message
        bot.send_message(
            chat_id,
            f"Bem-vindo de volta, {user['name']}! Seu perfil já está configurado. Você receberá notificações com base em seus interesses."
        )
        return
    
    # New user, start registration process
    user_states[chat_id] = {
        "state": ConversationState.AWAITING_NAME,
        "data": {}
    }
    
    # Send welcome message
    bot.send_message(chat_id, MESSAGES["welcome"])
    time.sleep(1)  # Small delay for better UX
    bot.send_message(chat_id, MESSAGES["ask_name"])

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Handle the /help command."""
    chat_id = message.chat.id
    send_help_message(chat_id)

@bot.message_handler(commands=['status'])
def handle_status(message):
    """Handle the /status command."""
    chat_id = message.chat.id
    
    # Get user information
    user = db.get_user_by_chat_id(str(chat_id))
    if not user:
        bot.send_message(
            chat_id,
            "Você ainda não está registrado. Use o comando /start para se registrar."
        )
        return
    
    # Format keywords for display
    keywords_str = ", ".join(user['keywords']) if user['keywords'] else "Nenhuma"
    
    # Create status message
    status_msg = f"📊 *Seu Perfil*\n\n"
    status_msg += f"👤 *Nome:* {user['name']}\n"
    status_msg += f"📧 *Email:* {user['email']}\n"
    status_msg += f"🎯 *Intenção:* {user['intention']}\n"
    status_msg += f"🔑 *Interesses:* {keywords_str}\n\n"
    
    if user['group_id']:
        status_msg += f"🔗 *Link do Grupo:* {user['invite_link']}\n"
    else:
        status_msg += "⏳ *Status do Grupo:* Aguardando criação\n"
    
    bot.send_message(
        chat_id,
        status_msg,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['update'])
def handle_update(message):
    """Handle the /update command to update user preferences."""
    chat_id = message.chat.id
    
    # Check if user exists
    user = db.get_user_by_chat_id(str(chat_id))
    if not user:
        bot.send_message(
            chat_id,
            "Você ainda não está registrado. Use o comando /start para se registrar."
        )
        return
    
    # Start update process - for now, we'll only allow updating interests
    user_states[chat_id] = {
        "state": ConversationState.AWAITING_INTERESTS,
        "data": {
            "name": user['name'],
            "email": user['email'],
            "intention": user['intention'],
            "update_mode": True,
            "user_id": user['id']
        }
    }
    
    bot.send_message(
        chat_id,
        "Vamos atualizar seus interesses. Por favor, informe suas palavras-chave de interesse separadas por vírgula:"
    )

@bot.message_handler(commands=['myid'])
def handle_myid(message):
    """Handle the /myid command."""
    chat_id = message.chat.id
    bot.send_message(chat_id, f"Seu ID no Telegram é: {chat_id}")

# Admin command handlers
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    """Handle the /admin command."""
    chat_id = message.chat.id
    
    # Check if user is admin
    if str(chat_id) not in ADMIN_IDS:
        bot.send_message(chat_id, MESSAGES["admin_only"])
        return
    
    # Send admin menu
    bot.send_message(
        chat_id,
        "🔐 *Painel de Administração*\n\nEscolha uma opção:",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    
    # Set admin state
    user_states[chat_id] = {
        "state": ConversationState.AWAITING_ADMIN_COMMAND,
        "data": {}
    }

@bot.message_handler(commands=['backup'])
def handle_backup(message):
    """Handle the /backup command."""
    chat_id = message.chat.id
    
    # Check if user is admin
    if str(chat_id) not in ADMIN_IDS:
        bot.send_message(chat_id, MESSAGES["admin_only"])
        return
    
    # Create database backup
    backup_file = db.backup_database()
    if backup_file:
        bot.send_message(
            chat_id,
            MESSAGES["backup_success"].format(backup_file=backup_file)
        )
    else:
        bot.send_message(chat_id, "❌ Falha ao criar backup do banco de dados.")

@bot.message_handler(commands=['restore'])
def handle_restore(message):
    """Handle the /restore command."""
    chat_id = message.chat.id
    
    # Check if user is admin
    if str(chat_id) not in ADMIN_IDS:
        bot.send_message(chat_id, MESSAGES["admin_only"])
        return
    
    # Send backup selection keyboard
    bot.send_message(
        chat_id,
        "📂 *Restaurar Backup*\n\nSelecione um arquivo de backup para restaurar:",
        parse_mode="Markdown",
        reply_markup=get_backup_selection_keyboard()
    )

@bot.message_handler(commands=['removeuser'])
def handle_remove_user(message):
    """Handle the /removeuser command."""
    chat_id = message.chat.id
    
    # Check if user is admin
    if str(chat_id) not in ADMIN_IDS:
        bot.send_message(chat_id, MESSAGES["admin_only"])
        return
    
    # Extract command parameters
    parts = message.text.split()
    if len(parts) < 2:
        bot.send_message(
            chat_id,
            "❓ Uso correto: /removeuser ID_DO_USUARIO"
        )
        return
    
    target_id = parts[1]
    
    # Try to remove user
    if db.remove_user(target_id):
        bot.send_message(chat_id, MESSAGES["user_removed"])
    else:
        bot.send_message(chat_id, MESSAGES["user_not_found"])

@bot.message_handler(commands=['listusers'])
def handle_list_users(message):
    """Handle the /listusers command."""
    chat_id = message.chat.id
    
    # Check if user is admin
    if str(chat_id) not in ADMIN_IDS:
        bot.send_message(chat_id, MESSAGES["admin_only"])
        return
    
    # Get users with keywords
    users = db.list_users(with_keywords=True)
    
    if not users:
        bot.send_message(chat_id, "Não há usuários registrados.")
        return
    
    # Format user list in chunks to avoid message length limits
    user_chunks = []
    current_chunk = ""
    
    for i, user in enumerate(users):
        # Format keywords
        keywords_str = ", ".join(user['keywords']) if 'keywords' in user and user['keywords'] else "None"
        
        # Create user entry
        user_entry = f"{i+1}. *{user['name']}*\n"
        user_entry += f"   ID: `{user['chat_id']}`\n"
        user_entry += f"   Email: {user['email']}\n"
        user_entry += f"   Interesses: {keywords_str}\n"
        user_entry += f"   Grupo: {user['group_id'] or 'Não atribuído'}\n\n"
        
        # Check if adding this entry would exceed message limit
        if len(current_chunk) + len(user_entry) > 4000:
            user_chunks.append(current_chunk)
            current_chunk = user_entry
        else:
            current_chunk += user_entry
    
    # Add the last chunk if not empty
    if current_chunk:
        user_chunks.append(current_chunk)
    
    # Send messages
    for i, chunk in enumerate(user_chunks):
        header = f"📋 *Lista de Usuários ({i+1}/{len(user_chunks)})*\n\n"
        bot.send_message(
            chat_id,
            header + chunk,
            parse_mode="Markdown"
        )

# Callback query handler for inline buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Handle callback queries from inline keyboards."""
    chat_id = call.message.chat.id
    
    # Check if it's a restore operation
    if call.data.startswith("restore_"):
        # Check if user is admin
        if str(chat_id) not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "Você não tem permissão para esta ação.")
            return
        
        # Extract backup filename
        backup_file = call.data.replace("restore_", "")
        backup_path = f"backups/{backup_file}"
        
        # Confirm restoration
        bot.edit_message_text(
            f"🔄 Restaurando banco de dados a partir de {backup_file}...",
            chat_id=chat_id,
            message_id=call.message.message_id
        )
        
        # Perform restoration
        success = db.restore_database(backup_path)
        
        if success:
            bot.edit_message_text(
                MESSAGES["restore_success"],
                chat_id=chat_id,
                message_id=call.message.message_id
            )
        else:
            bot.edit_message_text(
                MESSAGES["restore_failed"],
                chat_id=chat_id,
                message_id=call.message.message_id
            )
    
    elif call.data == "cancel_restore":
        bot.edit_message_text(
            "❌ Operação de restauração cancelada.",
            chat_id=chat_id,
            message_id=call.message.message_id
        )
    
    elif call.data == "no_backups":
        bot.answer_callback_query(call.id, "Não há backups disponíveis.")

# Handle text messages within conversations
@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_conversation(message):
    """Handle messages within a conversation state."""
    chat_id = message.chat.id
    state_info = user_states.get(chat_id)
    
    if not state_info:
        return
    
    current_state = state_info["state"]
    data = state_info["data"]
    
    # Admin conversation handling
    if current_state == ConversationState.AWAITING_ADMIN_COMMAND:
        handle_admin_conversation(message, data)
        return
    
    # Regular user conversation handling
    if current_state == ConversationState.AWAITING_NAME:
        # Process name
        name = message.text.strip()
        data["name"] = name
        
        # Move to next state
        state_info["state"] = ConversationState.AWAITING_EMAIL
        
        # Ask for email
        bot.send_message(chat_id, MESSAGES["ask_email"].format(name=name))
    
    elif current_state == ConversationState.AWAITING_EMAIL:
        # Process email
        email = message.text.strip()
        data["email"] = email
        
        # Move to next state
        state_info["state"] = ConversationState.AWAITING_INTENTION
        
        # Ask for intention
        bot.send_message(chat_id, MESSAGES["ask_intention"])
    
    elif current_state == ConversationState.AWAITING_INTENTION:
        # Process intention
        intention = message.text.strip()
        data["intention"] = intention
        
        # Move to next state
        state_info["state"] = ConversationState.AWAITING_INTERESTS
        
        # Ask for interests
        bot.send_message(chat_id, MESSAGES["ask_interests"])
    
    elif current_state == ConversationState.AWAITING_INTERESTS:
        # Process interests
        keywords = message.text.strip()
        data["keywords"] = keywords
        
        # If in update mode, update existing user
        if data.get("update_mode"):
            # Clear existing keywords and add new ones
            # This would need to be implemented in the database class
            user_id = data.get("user_id")
            
            # Send confirmation
            bot.send_message(
                chat_id,
                f"✅ Seus interesses foram atualizados para: {keywords}"
            )
            
            # Clear user state
            del user_states[chat_id]
            return
        
        # Regular registration flow
        user_id = db.add_user(
            str(chat_id),
            data["name"],
            data["email"],
            data["intention"],
            keywords
        )
        
        if user_id:
            # Send confirmation
            bot.send_message(
                chat_id,
                MESSAGES["registration_complete"].format(
                    name=data["name"],
                    email=data["email"],
                    intention=data["intention"],
                    keywords=keywords
                )
            )
        else:
            # Registration failed
            bot.send_message(
                chat_id,
                "❌ Ocorreu um erro ao salvar seus dados. Por favor, tente novamente mais tarde."
            )
        
        # Clear user state
        del user_states[chat_id]

def handle_admin_conversation(message, data):
    """Handle the admin conversation flow."""
    chat_id = message.chat.id
    text = message.text
    
    # Process based on admin command text
    if text == "📊 List Users":
        handle_list_users(message)
    
    elif text == "🔍 Find User":
        bot.send_message(
            chat_id,
            "Digite o ID do usuário ou nome que deseja encontrar:"
        )
        # Could set a more specific state here for searching users
    
    elif text == "🗑️ Remove User":
        bot.send_message(
            chat_id,
            "Digite o ID do usuário que deseja remover:"
        )
        # Could set a more specific state here for removing users
    
    elif text == "💾 Backup Database":
        handle_backup(message)
    
    elif text == "♻️ Restore Database":
        handle_restore(message)
    
    elif text == "❌ Cancel":
        # Clear state and send confirmation
        del user_states[chat_id]
        
        # Remove keyboard
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            chat_id,
            "🔙 Saindo do modo de administração.",
            reply_markup=markup
        )
    
    else:
        # Check if it's a user ID for removal
        if text.isdigit() or text.startswith("-") and text[1:].isdigit():
            if db.remove_user(text):
                bot.send_message(chat_id, MESSAGES["user_removed"])
            else:
                bot.send_message(chat_id, MESSAGES["user_not_found"])
        else:
            # Unknown admin command
            bot.send_message(
                chat_id, 
                "Comando não reconhecido. Por favor, selecione uma opção do menu.",
                reply_markup=get_admin_keyboard()
            )

# Fallback handler for unrecognized messages
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    """Handle unrecognized messages."""
    chat_id = message.chat.id
    bot.send_message(chat_id, MESSAGES["command_not_found"])
    send_help_message(chat_id)

# Function to send invite links to users
def send_invite(chat_id, invite_link):
    """Send a group invitation link to a user."""
    try:
        bot.send_message(
            chat_id,
            MESSAGES["group_invitation"].format(invite_link=invite_link)
        )
        logger.info(f"Invite sent to chat_id {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending invite to chat_id {chat_id}: {e}")
        return False

# Function to generate permanent invite links for groups
def generate_invite_link(group_id):
    """Generate a permanent invite link for a group."""
    try:
        invite_link = bot.create_chat_invite_link(
            group_id, 
            expire_date=None,
            member_limit=None
        ).invite_link
        
        logger.info(f"Generated invite link for group {group_id}: {invite_link}")
        return invite_link
    except Exception as e:
        logger.error(f"Error generating invite link for group {group_id}: {e}")
        return None

# Function to send a tweet to a group
def send_tweet_to_group(group_id, tweet_text, tweet_link):
    """Send a tweet notification to a group."""
    try:
        bot.send_message(
            group_id,
            MESSAGES["new_tweet"].format(
                tweet_text=tweet_text,
                tweet_link=tweet_link
            ),
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
        return True
    except Exception as e:
        logger.error(f"Error sending tweet to group {group_id}: {e}")
        return False