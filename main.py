import os
import requests
import time
from bs4 import BeautifulSoup
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Set up logging for debugging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
        })
        self.short_url = short_url
        self.base_url = "https://keedabankingnews.com"
        self.final_url = None
    
    def get_hidden_input(self, soup, name):
        input_tag = soup.find('input', {'name': name})
        return input_tag['value'] if input_tag else None
    
    def handle_countdown(self, soup):
        countdown_button = soup.find('button', {'id': 'countdown'}) or soup.find('div', {'id': 'countdown'})
        if countdown_button:
            time_span = countdown_button.find('span', {'id': 'tp-time'})
            seconds = 15  # Default wait time
            if time_span and time_span.text.strip():
                try:
                    seconds = int(time_span.text.strip())
                except ValueError:
                    logger.warning("Could not parse countdown time, defaulting to 15 seconds")
            logger.info(f"Waiting {seconds} seconds for countdown...")
            time.sleep(seconds + 2)  # Extra 2 seconds to account for popup loading
            return True
        return False
    
    def process_page(self, url, step, total_steps, form_data_name=None):
        logger.info(f"Processing step {step}/{total_steps} at {url}")
        
        # Fetch the page
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page: {e}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Handle countdown and wait for popup
        if self.handle_countdown(soup):
            try:
                response = self.session.get(url, timeout=20)  # Reload after countdown
                soup = BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to reload page after countdown: {e}")
                return None
        
        # Verify step
        step_text = soup.find(string=re.compile(f"You are currently on step {step}/{total_steps}"))
        if not step_text:
            logger.warning(f"Step {step} verification failed, proceeding anyway...")
        
        # Step 4: Look for "Get Link" button
        if step == total_steps:
            get_link = soup.find('a', href=re.compile(r'/includes/open\.php\?id='))
            if get_link:
                final_path = get_link['href']
                if not final_path.startswith('http'):
                    final_path = f"{self.base_url}{final_path}"
                self.final_url = final_path
                logger.info(f"Found final link path: {self.final_url}")
                try:
                    final_response = self.session.get(self.final_url, allow_redirects=False, timeout=20)
                    if final_response.status_code in [301, 302, 303, 307, 308]:
                        telegram_url = final_response.headers['Location']
                        logger.info(f"Success! Final Telegram URL: {telegram_url}")
                        return telegram_url
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to access final link: {e}")
                return None
            logger.warning("No 'Get Link' button found on final step")
            return None
        
        # Steps 1-3: Find and submit the form
        form = soup.find('form', {'name': 'tp'})
        if not form:
            logger.warning("No form found to proceed")
            return None
        
        form_data = {}
        if form_data_name:
            hidden_value = self.get_hidden_input(soup, form_data_name)
            if hidden_value:
                form_data[form_data_name] = hidden_value
            else:
                logger.warning(f"No hidden input found for {form_data_name}")
        
        action_url = form.get('action', '')
        if not action_url.startswith('http'):
            action_url = f"{self.base_url}{action_url}"
        
        logger.info(f"Submitting form to: {action_url} with data: {form_data}")
        try:
            response = self.session.post(action_url, data=form_data, allow_redirects=False, timeout=20)
            if response.status_code in [301, 302, 303, 307, 308]:
                next_url = response.headers['Location']
                logger.info(f"Redirected to: {next_url}")
                return next_url
            return response.url
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to submit form: {e}")
            return None
    
    def bypass(self):
        logger.info(f"Starting bypass for {self.short_url}")
        
        # Step 0: Initial redirect from short URL
        try:
            response = self.session.get(self.short_url, allow_redirects=False, timeout=20)
            if response.status_code in [301, 302, 303, 307, 308]:
                current_url = response.headers['Location']
                logger.info(f"Initial redirect to: {current_url}")
            else:
                current_url = self.short_url
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to access short URL: {e}")
            return None
        
        # Define steps based on your structure
        steps = [
            (1, 'tp2'),  # Step 1
            (2, 'tp3'),  # Step 2
            (3, 'tp4'),  # Step 3
            (4, None),   # Step 4 (Get Link)
        ]
        
        # Process each step
        for step, form_data_name in steps:
            result = self.process_page(current_url, step, 4, form_data_name)
            if isinstance(result, str) and result.startswith('http'):
                current_url = result
            elif result is None:
                logger.error(f"Failed at step {step}")
                return None
            elif step == 4 and result:  # Final Telegram URL
                return result
        
        logger.error("Failed to extract final URL after all steps")
        return None

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send me an Adrino link (e.g., https://adrinolinks.in/HucM6) and I'll bypass it for you!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    
    if not message_text.startswith("https://adrinolinks.in/"):
        await update.message.reply_text("Please send a valid Adrino link (e.g., https://adrinolinks.in/HucM6).")
        return
    
    await update.message.reply_text("Processing your link, please wait... (this may take up to a minute)")
    
    bypasser = AdrinoBypass(message_text)
    final_url = bypasser.bypass()
    
    if final_url:
        await update.message.reply_text(f"Success! Final URL: {final_url}")
    else:
        await update.message.reply_text("Failed to bypass the link. The link might be invalid or the site structure has changed.")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")
        return
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()