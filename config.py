import os
import logging
from logging.handlers import RotatingFileHandler
import json
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN_HERE")

# Webhook settings
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-webhook-url.com/webhook")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 5000))

# Database settings
DATABASE_FILE = os.getenv("DATABASE_FILE", "bot_database.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")

# Admin settings
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[]"))  # List of admin chat IDs

# Performance settings
DB_POLL_INTERVAL = int(os.getenv("DB_POLL_INTERVAL", 60))  # Seconds

# Message templates
MESSAGES = {
    "welcome": "👋 Bem-vindo ao Bot de Notificações! Vamos configurar suas preferências para enviar atualizações personalizadas.",
    "ask_name": "Para começarmos, por favor, informe seu nome completo:",
    "ask_email": "Obrigado, {name}! Agora, por favor, informe seu e-mail para contato:",
    "ask_intention": "Ótimo! Agora, conte-nos qual é a sua intenção ao usar nosso serviço:",
    "ask_interests": "Por último, informe seus interesses utilizando palavras-chave separadas por vírgula (exemplo: tecnologia, marketing, startups):",
    "registration_complete": "✅ Cadastro concluído com sucesso!\n\nSeu perfil foi registrado com os seguintes dados:\n\n👤 Nome: {name}\n📧 E-mail: {email}\n🎯 Intenção: {intention}\n🔑 Interesses: {keywords}\n\nVocê receberá um link para o seu grupo em breve. Obrigado por se cadastrar!",
    "group_invitation": "🚀 Seu grupo foi criado!\n\nClique no link abaixo para entrar no seu grupo personalizado de notificações:\n\n{invite_link}\n\nLá você receberá apenas notificações relacionadas aos seus interesses.",
    "new_tweet": "🔔 *Nova Notificação Encontrada!*\n\n{tweet_text}\n\n🔗 [Ver no Twitter/X]({tweet_link})",
    "error": "😕 Ocorreu um erro inesperado. Por favor, tente novamente ou entre em contato com o suporte.",
    "command_not_found": "Comando não reconhecido. Use /help para ver os comandos disponíveis.",
    "admin_only": "Este comando está disponível apenas para administradores.",
    "help": "📚 *Comandos Disponíveis:*\n\n/start - Iniciar ou reiniciar o bot\n/status - Ver seu status atual\n/update - Atualizar suas preferências\n/help - Exibir esta mensagem de ajuda\n\nSe precisar de suporte adicional, use o comando /support.",
    "backup_success": "✅ Backup do banco de dados criado com sucesso!\nArquivo: {backup_file}",
    "restore_success": "✅ Banco de dados restaurado com sucesso!",
    "restore_failed": "❌ Falha ao restaurar o banco de dados.",
    "user_removed": "✅ Usuário removido com sucesso!",
    "user_not_found": "❌ Usuário não encontrado.",
}

# Setup logging
def setup_logging():
    """Configure logging for the application."""
    # Ensure logs directory exists
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler - with rotation
    file_handler = RotatingFileHandler(
        "logs/bot.log", maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Set higher log level for some verbose libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telebot").setLevel(logging.WARNING)
    
    return logger