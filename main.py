import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from selenium.common.exceptions import TimeoutException, WebDriverException

# Setup logging
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Selenium functions
def wait_and_click(driver, by, value, timeout=30):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        driver.execute_script("arguments[0].click();", element)
        logger.info(f"Clicked on element: {value}")
        return True
    except TimeoutException:
        logger.warning(f"Timeout waiting for element {value} to be clickable")
        return False
    except Exception as e:
        logger.warning(f"Failed to click element {value}: {str(e)}")
        return False

def close_popup(driver):
    try:
        close_btns = driver.find_elements(By.CLASS_NAME, 'close')
        for btn in close_btns:
            try:
                if btn.is_displayed():
                    btn.click()
                    logger.info("Popup closed using class 'close'")
                    time.sleep(1)
                    return True
            except:
                continue

        overlays = driver.find_elements(By.CLASS_NAME, 'overlay')
        for overlay in overlays:
            try:
                if overlay.is_displayed():
                    driver.execute_script("arguments[0].style.display = 'none';", overlay)
                    logger.info("Overlay removed")
                    time.sleep(1)
            except:
                continue

        popups = driver.find_elements(By.CLASS_NAME, 'popup')
        for popup in popups:
            try:
                if popup.is_displayed():
                    driver.execute_script("arguments[0].style.display = 'none';", popup)
                    logger.info("Popup removed")
                    time.sleep(1)
            except:
                continue
    except Exception as e:
        logger.info(f"No popup found or error closing: {str(e)}")
    return False

def wait_countdown(driver, seconds=15):
    logger.info(f"Waiting for countdown (default {seconds} seconds)...")
    try:
        countdown = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "tp-time"))
        )
        remaining = int(countdown.text)
        logger.info(f"Detected dynamic countdown: {remaining} seconds remaining")
        time.sleep(remaining + 1)
        return True
    except TimeoutException:
        logger.info(f"No dynamic countdown found, waiting default {seconds} seconds")
        time.sleep(seconds + 1)
        return True
    except Exception as e:
        logger.warning(f"Countdown wait failed: {str(e)}")
        return False

def handle_page(driver, step_num):
    logger.info(f"Processing Step {step_num}/4")
    
    if not wait_countdown(driver):
        return False
    
    for _ in range(3):
        close_popup(driver)
        time.sleep(1)
    
    success = False
    
    if not success:
        success = wait_and_click(driver, By.ID, "tp-snp2", timeout=10)
    
    if not success:
        success = wait_and_click(driver, By.XPATH, "//button[contains(text(), 'Click here to proceed') or contains(text(), 'Proceed')]", timeout=10)
    
    if not success and step_num < 4:
        try:
            form = driver.find_element(By.TAG_NAME, "form")
            driver.execute_script("arguments[0].submit();", form)
            logger.info("Form submitted via JavaScript")
            success = True
        except Exception as e:
            logger.warning(f"Failed to submit form: {str(e)}")
    
    time.sleep(3)
    return success

def handle_final_page(driver):
    logger.info("Processing Final Page (Step 4/4)...")
    if not wait_countdown(driver):
        return None
    
    for _ in range(3):
        close_popup(driver)
        time.sleep(1)
    
    final_url = None
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts and not final_url:
        attempt += 1
        logger.info(f"Attempt {attempt} to get final link...")
        
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//a[contains(@href, '/includes/open.php')]//button[contains(text(), 'Get Link')] | "
                    "//button[contains(text(), 'Get Link')] | "
                    "//a[contains(text(), 'Get Link')]"))
            )
            
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(1)
            
            driver.execute_script("arguments[0].click();", button)
            logger.info("Clicked 'Get Link' button")
            
            time.sleep(5)
            
            current_url = driver.current_url
            if "keedabankingnews.com" not in current_url:
                final_url = current_url
                logger.info(f"Successfully redirected to final URL: {final_url}")
                break
            else:
                logger.warning("Still on the same domain after click, trying again...")
                
        except TimeoutException:
            logger.warning(f"Attempt {attempt} timed out waiting for 'Get Link' button")
            time.sleep(3)
        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {str(e)}")
            time.sleep(3)
    
    if not final_url:
        try:
            link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, 
                    "//a[contains(@href, '/includes/open.php')]"))
            )
            final_url = link.get_attribute("href")
            logger.info(f"Extracted final URL from link: {final_url}")
            
            if final_url:
                driver.get(final_url)
                time.sleep(3)
                final_url = driver.current_url
                logger.info(f"Final URL after direct visit: {final_url}")
                
        except Exception as e:
            logger.error(f"Failed to extract final URL: {str(e)}")
    
    return final_url

def bypass_adrinolink(start_url):
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
    except WebDriverException as e:
        logger.error(f"Failed to launch Chrome: {str(e)}")
        return None
    
    final_url = None
    
    try:
        driver.set_page_load_timeout(30)  # Timeout for page loads
        driver.get(start_url)
        logger.info(f"Loaded initial URL: {start_url}")
        
        for step in range(1, 5):
            if step < 4:
                if not handle_page(driver, step):
                    logger.error(f"Failed to process step {step}")
                    break
                time.sleep(2)
            else:
                final_url = handle_final_page(driver)
        
    except TimeoutException:
        logger.error("Page load timeout occurred")
    except Exception as e:
        logger.error(f"Error during bypass: {str(e)}")
    
    finally:
        driver.quit()
    
    return final_url

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
    
    final_url = bypass_adrinolink(message_text)
    
    if final_url:
        await update.message.reply_text(f"Success! Final URL: {final_url}")
    else:
        await update.message.reply_text("Failed to bypass the link. Please check the URL or try again later.")

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