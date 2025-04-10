import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import telebot
from telebot import types

# Setup logging
logging.basicConfig(
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    level=logging.INFO
)

# Initialize bot
bot = telebot.TeleBot('7710211536:AAG4ursFUqa4jzQEcVjk9vn4a-yVHYBcYII')  # Replace with your bot token

# Same helper functions as in your original code
def wait_and_click(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        time.sleep(random.uniform(0.2, 0.7))
        driver.execute_script("arguments[0].click();", element)
        logging.info(f"Clicked on element: {value}")
        return True
    except Exception as e:
        logging.warning(f"Failed to click element {value}: {str(e)}")
        return False

def close_popup(driver):
    # Same implementation as original
    try:
        overlays = driver.find_elements(By.CLASS_NAME, 'overlay')
        for overlay in overlays:
            if overlay.is_displayed():
                driver.execute_script("arguments[0].style.display = 'none';", overlay)
                logging.info("Overlay removed")
                time.sleep(0.5)
                
        popups = driver.find_elements(By.CLASS_NAME, 'popup')
        for popup in popups:
            if popup.is_displayed():
                driver.execute_script("arguments[0].style.display = 'none';", popup)
                logging.info("Popup removed")
                time.sleep(0.5)
                
        close_btns = driver.find_elements(By.CLASS_NAME, 'close')
        for btn in close_btns:
            if btn.is_displayed():
                btn.click()
                logging.info("Popup closed using class 'close'")
                time.sleep(0.5)
                return True
    except Exception as e:
        logging.info(f"No popup found or error closing: {str(e)}")
    return False

def wait_countdown(driver):
    # Same implementation as original
    try:
        countdown = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "tp-time"))
        )
        remaining = int(countdown.text.strip())
        while remaining > 0:
            time.sleep(1)
            remaining = int(driver.find_element(By.ID, "tp-time").text.strip())
        time.sleep(1)
    except:
        time.sleep(10)

def handle_page(driver, step_num):
    # Same implementation as original
    wait_countdown(driver)
    for _ in range(3):
        close_popup(driver)
        time.sleep(random.uniform(0.5, 1.5))
    
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
            success = True
        except:
            pass
    time.sleep(2)
    return success

def handle_final_page(driver):
    # Same implementation as original
    wait_countdown(driver)
    for _ in range(3):
        close_popup(driver)
        time.sleep(random.uniform(0.5, 1.5))
    
    final_url = None
    max_attempts = 3
    
    for attempt in range(1, max_attempts + 1):
        if final_url:
            break
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//a[contains(@href, '/includes/open.php')]//button[contains(text(), 'Get Link')] | "
                    "//button[contains(text(), 'Get Link')] | "
                    "//a[contains(text(), 'Get Link')]"))
            )
            driver.execute_script("arguments[0].click();", button)
            for wait_time in [2, 3, 5]:
                time.sleep(wait_time)
                current_url = driver.current_url
                if "keedabankingnews.com" not in current_url and "adrinolinks.in" not in current_url:
                    final_url = current_url
                    break
        except:
            time.sleep(3)
    
    if not final_url:
        try:
            link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/includes/open.php')]"))
            )
            final_url = link.get_attribute("href")
            if final_url and ("t.me" in final_url or "telegram" in final_url):
                driver.get(final_url)
                time.sleep(3)
                final_url = driver.current_url
        except:
            pass
    return final_url

def bypass_adrinolink(start_url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Headless mode for server
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    final_url = None
    try:
        driver.get(start_url)
        for step in range(1, 5):
            if step < 4:
                if not handle_page(driver, step):
                    break
                time.sleep(random.uniform(1, 2))
            else:
                final_url = handle_final_page(driver)
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        driver.quit()
    
    return final_url

# Telegram bot handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Send me an Adrinolinks URL (like https://adrinolinks.in/HucM6) and I'll get you the final Telegram link.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    url = message.text.strip()
    if not url.startswith('https://adrinolinks.in/'):
        bot.reply_to(message, "Please send a valid Adrinolinks URL starting with 'https://adrinolinks.in/'")
        return
    
    bot.reply_to(message, "Processing your link, please wait...")
    final_url = bypass_adrinolink(url)
    
    if final_url:
        bot.reply_to(message, f"✅ Final Telegram Link: {final_url}")
    else:
        bot.reply_to(message, "❌ Failed to retrieve the final link.")

# Run the bot
if __name__ == "__main__":
    bot.polling(none_stop=True)