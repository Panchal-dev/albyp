import os
import requests
import time
from bs4 import BeautifulSoup
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# AdrinoBypass Class (same as yours, slightly modified for bot usage)
class AdrinoBypass:
    def __init__(self, short_url):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        })
        self.short_url = short_url
        self.base_url = "https://keedabankingnews.com"
        self.final_url = None
    
    def get_hidden_input(self, soup, name):
        input_tag = soup.find('input', {'name': name})
        return input_tag['value'] if input_tag else None
    
    def close_popup(self, soup):
        popup = soup.find('div', {'class': 'popup'})
        if popup and 'display: block;' in popup.get('style', '').lower():
            return True
        return False
    
    def handle_countdown(self, soup):
        countdown_div = soup.find('button', {'id': 'countdown'}) or soup.find('div', {'id': 'countdown'})
        if countdown_div:
            seconds = 10  # Default wait time
            time_span = countdown_div.find('span', {'id': 'tp-time'})
            if time_span:
                try:
                    seconds = int(time_span.text)
                except ValueError:
                    pass
            time.sleep(seconds)
            return True
        return False
    
    def process_page(self, url, step, expected_step, form_data_name=None):
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        self.handle_countdown(soup)
        self.close_popup(soup)
        
        if step == expected_step:
            get_link = soup.find('a', href=re.compile(r'/includes/open\.php'))
            if get_link:
                final_path = get_link['href']
                if not final_path.startswith('http'):
                    final_path = f"{self.base_url}{final_path}"
                self.final_url = final_path
                try:
                    final_response = self.session.get(self.final_url, allow_redirects=False, timeout=10)
                    if final_response.status_code in [301, 302, 303, 307, 308]:
                        return final_response.headers['Location']
                except requests.exceptions.RequestException:
                    return None
            return None
        
        form = soup.find('form', {'name': 'tp'})
        if not form:
            return None
        
        form_data = {}
        if form_data_name:
            hidden_value = self.get_hidden_input(soup, form_data_name)
            if hidden_value:
                form_data[form_data_name] = hidden_value
        
        action_url = form['action']
        if not action_url.startswith('http'):
            action_url = f"{self.base_url}{action_url}"
        
        try:
            response = self.session.post(action_url, data=form_data, allow_redirects=False, timeout=10)
            if response.status_code in [301, 302, 303, 307, 308]:
                return response.headers['Location']
            return response.url
        except requests.exceptions.RequestException:
            return None
    
    def bypass(self):
        try:
            response = self.session.get(self.short_url, allow_redirects=False, timeout=10)
            if response.status_code in [301, 302, 303, 307, 308]:
                current_url = response.headers['Location']
            else:
                current_url = self.short_url
        except requests.exceptions.RequestException:
            return None
        
        steps = [
            (1, 'tp2'),
            (2, 'tp3'),
            (3, 'tp4'),
            (4, None)
        ]
        
        for step, form_data_name in steps:
            result = self.process_page(current_url, step, 4, form_data_name)
            if isinstance(result, str) and result.startswith('http'):
                current_url = result
            elif result is None:
                return None
            elif step == 4 and result:
                return result
        
        return None

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me an Adrino link (e.g., https://adrinolinks.in/HucM6) and I'll bypass it for you!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    
    # Check if the message is an Adrino link
    if not message_text.startswith("https://adrinolinks.in/"):
        await update.message.reply_text("Please send a valid Adrino link (e.g., https://adrinolinks.in/HucM6).")
        return
    
    await update.message.reply_text("Processing your link, please wait...")
    
    # Bypass the link
    bypasser = AdrinoBypass(message_text)
    final_url = bypasser.bypass()
    
    if final_url:
        await update.message.reply_text(f"Success! Final URL: {final_url}")
    else:
        await update.message.reply_text("Failed to bypass the link. Please try again or check the URL.")

# Main function to run the bot
def main():
    # Get the bot token from environment variable (set in Railway)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not set in environment variables.")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()