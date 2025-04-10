import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from threading import Event, Lock

# Setup logging
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for process control
current_process = None
stop_event = Event()
process_lock = Lock()

# Selenium functions
def wait_and_click(driver, by, value, timeout=10):
    if stop_event.is_set():
        return False
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        time.sleep(random.uniform(0.2, 0.7))
        driver.execute_script("arguments[0].click();", element)
        logger.info(f"Clicked on element: {value}")
        return True
    except Exception as e:
        logger.warning(f"Failed to click element {value}: {str(e)}")
        return False

def close_popup(driver):
    if stop_event.is_set():
        return False
    try:
        overlays = driver.find_elements(By.CLASS_NAME, 'overlay')
        for overlay in overlays:
            try:
                if overlay.is_displayed():
                    driver.execute_script("arguments[0].style.display = 'none';", overlay)
                    logger.info("Overlay removed")
                    time.sleep(0.5)
            except:
                continue

        popups = driver.find_elements(By.CLASS_NAME, 'popup')
        for popup in popups:
            try:
                if popup.is_displayed():
                    driver.execute_script("arguments[0].style.display = 'none';", popup)
                    logger.info("Popup removed")
                    time.sleep(0.5)
            except:
                continue

        close_btns = driver.find_elements(By.CLASS_NAME, 'close')
        for btn in close_btns:
            try:
                if btn.is_displayed():
                    btn.click()
                    logger.info("Popup closed using class 'close'")
                    time.sleep(0.5)
                    return True
            except:
                continue
    except Exception as e:
        logger.info(f"No popup found or error closing: {str(e)}")
    return False

def wait_countdown(driver):
    if stop_event.is_set():
        return
    try:
        countdown = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "tp-time"))
        )
        remaining = int(countdown.text.strip())
        logger.info(f"Detected dynamic countdown: {remaining} seconds remaining")
        
        while remaining > 0 and not stop_event.is_set():
            time.sleep(1)
            remaining = int(driver.find_element(By.ID, "tp-time").text.strip())
            logger.debug(f"Countdown: {remaining} seconds remaining")
        
        if not stop_event.is_set():
            time.sleep(1)
    except Exception as e:
        logger.warning(f"Using fallback countdown (10s): {str(e)}")
        if not stop_event.is_set():
            time.sleep(10)

def handle_page(driver, step_num):
    if stop_event.is_set():
        return False
    logger.info(f"Processing Step {step_num}/4")
    
    wait_countdown(driver)
    if stop_event.is_set():
        return False
    
    for _ in range(3):
        close_popup(driver)
        time.sleep(random.uniform(0.5, 1.5))
        if stop_event.is_set():
            return False
    
    success = False
    
    if not success:
        success = wait_and_click(driver, By.ID, "tp-snp2", timeout=5)
    
    if not success:
        success = wait_and_click(driver, By.XPATH, 
            "//button[contains(text(), 'Click here to proceed') or contains(text(), 'Proceed')]", 
            timeout=5)
    
    if not success and step_num < 4:
        try:
            form = driver.find_element(By.TAG_NAME, "form")
            driver.execute_script("arguments[0].submit();", form)
            logger.info("Form submitted via JavaScript")
            success = True
        except Exception as e:
            logger.warning(f"Failed to submit form: {str(e)}")
    
    if not stop_event.is_set():
        time.sleep(2)
    return success

def handle_final_page(driver):
    if stop_event.is_set():
        return None
    logger.info("Processing Final Page (Step 4/4)...")
    wait_countdown(driver)
    if stop_event.is_set():
        return None
    
    for _ in range(3):
        close_popup(driver)
        time.sleep(random.uniform(0.5, 1.5))
        if stop_event.is_set():
            return None
    
    final_url = None
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        if final_url or stop_event.is_set():
            break
        logger.info(f"Attempt {attempt} to get final link...")
        
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//a[contains(@href, '/includes/open.php')]//button[contains(text(), 'Get Link')] | "
                    "//button[contains(text(), 'Get Link')] | "
                    "//a[contains(text(), 'Get Link')]"))
            )
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            driver.execute_script("arguments[0].style.border='2px solid red';", button)
            time.sleep(0.5)
            
            driver.execute_script("arguments[0].click();", button)
            logger.info("Clicked 'Get Link' button")
            
            for wait_time in [2, 3, 5]:
                if stop_event.is_set():
                    return None
                time.sleep(wait_time)
                current_url = driver.current_url
                if "keedabankingnews.com" not in current_url and "adrinolinks.in" not in current_url:
                    final_url = current_url
                    logger.info(f"Successfully redirected to final URL: {final_url}")
                    break
            
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {str(e)}")
            time.sleep(3)
    
    if not final_url and not stop_event.is_set():
        try:
            link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/includes/open.php')]"))
            )
            final_url = link.get_attribute("href")
            logger.info(f"Extracted final URL from link: {final_url}")
            
            if final_url and ("t.me" in final_url or "telegram" in final_url):
                driver.get(final_url)
                time.sleep(3)
                final_url = driver.current_url
        except Exception as e:
            logger.error(f"Failed to extract final URL: {str(e)}")
    
    return final_url

async def bypass_adrinolink(start_url, update, context):
    global current_process
    logger.info(f"Starting bypass for URL: {start_url}")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)

    logger.info("Launching Chrome browser in headless mode...")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {str(e)}")
        await update.message.reply_text("Failed to initialize browser. Please try again later.")
        return
    
    current_process = driver
    stop_event.clear()
    
    final_url = None
    
    try:
        driver.set_page_load_timeout(30)
        driver.get(start_url)
        logger.info(f"Loaded initial URL: {start_url}")
        
        for step in range(1, 5):
            if stop_event.is_set():
                logger.info("Process stopped by user")
                await update.message.reply_text("Process stopped.")
                break
            if step < 4:
                if not handle_page(driver, step):
                    logger.error(f"Failed to process step {step}")
                    break
                time.sleep(random.uniform(1, 2))
            else:
                final_url = handle_final_page(driver)
        
        if final_url and not stop_event.is_set():
            await update.message.reply_text(f"Success! Final URL: {final_url}")
        elif not stop_event.is_set():
            await update.message.reply_text("Failed to bypass the link. Please check the URL or try again later.")
    
    except Exception as e:
        logger.error(f"Error during bypass: {str(e)}")
        if not stop_event.is_set():
            await update.message.reply_text("An error occurred during processing. Please try again.")
    
    finally:
        driver.quit()
        with process_lock:
            current_process = None

# Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "4: Hello! Send me an Adrino link (e.g., https://adrinolinks.in/HucM6) to bypass it. Use /stop to halt the current process."
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_process
    with process_lock:
        if current_process:
            stop_event.set()
            await update.message.reply_text("Stopping the current process...")
            logger.info("Stop command received, stopping process...")
        else:
            await update.message.reply_text("No process is currently running.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_process
    message_text = update.message.text
    
    if not message_text.startswith("https://adrinolinks.in/"):
        await update.message.reply_text("Please send a valid Adrino link (e.g., https://adrinolinks.in/HucM6).")
        return
    
    with process_lock:
        if current_process:
            await update.message.reply_text("One process is running, stop that to start a new one using /stop.")
            return
        
        await update.message.reply_text("Processing your link, please wait... (this may take up to a minute)")
        await bypass_adrinolink(message_text, update, context)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")
        return
    
    logger.info("Starting fresh deployment...")  # Added for debugging
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()