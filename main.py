import os
import pickle
import time
import threading
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup


class CookieClickerBot:
    SAVE_FILE_COOKIES = "cookies.pkl"
    SAVE_FILE_STORAGE = "storage.json"
    GAME_URL = "https://orteil.dashnet.org/cookieclicker/"

    SYMBOLS = {
        "thousand": 10**3,
        "million": 10**6,
        "billion": 10**9,
        "trillion": 10**12,
        "quadrillion": 10**15,
        "quintillion": 10**18,
        "sextillion": 10**21,
        "septillion": 10**24,
        "octillion": 10**27,
        "nonillion": 10**30,
    }

    POPUP_SELECTORS = {
        "consent": ".fc-button-label",
        "language": "#langSelect-PL",
        "ads": ".cc_btn_accept_all",
    }

    def __init__(self):
        self.driver = webdriver.Chrome()
        self.driver.get(self.GAME_URL)
        self.wait = WebDriverWait(self.driver, 10)
        self.short_wait = WebDriverWait(self.driver, 1)
        self.big_cookie = None
        self.stop_thread = False

    def load_game_state(self):
        """Loads previously saved cookies and local storage."""
        if os.path.isfile(self.SAVE_FILE_COOKIES):
            with open(self.SAVE_FILE_COOKIES, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)

        if os.path.isfile(self.SAVE_FILE_STORAGE):
            with open(self.SAVE_FILE_STORAGE, "r") as file:
                storage = json.load(file)
                for key, value in storage.items():
                    self.driver.execute_script(f"localStorage.setItem('{key}', '{value}');")

    def save_game_state(self):
        """Saves the game state by exporting cookies and local storage."""
        with open(self.SAVE_FILE_STORAGE, "w") as file:
            json.dump(self.driver.execute_script("return { ...localStorage }"), file)
        with open(self.SAVE_FILE_COOKIES, "wb") as file:
            pickle.dump(self.driver.get_cookies(), file)
        print("Game state saved.")

    def dismiss_popups(self):
        """Handles popups that interfere with gameplay."""
        for selector in self.POPUP_SELECTORS.values():
            try:
                element = self.short_wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                element.click()
            except TimeoutException:
                continue

    def parse_cookie_count(self, cookie_text):
        """Parses the cookie count from the display text."""
        for symbol, multiplier in self.SYMBOLS.items():
            if symbol in cookie_text:
                return float(cookie_text.replace(symbol, "").replace(",", "").strip()) * multiplier
        return int(cookie_text.replace(",", "").split()[0])

    def get_current_cookies(self):
        """Fetches the current number of cookies available."""
        cookies_text = self.driver.find_element(By.CSS_SELECTOR, "#cookies").text
        return int(self.parse_cookie_count(cookies_text))

    def find_best_purchase(self, unlocked_items):
        """Finds the most cost-effective item to purchase based on production-to-price ratio."""
        best_ratio = 0
        best_item = None

        for item in unlocked_items:
            tooltip_html = self.driver.execute_script(
                f"return Game.ObjectsById[{item.get_attribute('id')[-1]}].tooltip()"
            )
            soup = BeautifulSoup(tooltip_html, "html.parser")
            
            production = float(soup.find("div", {"class": "descriptionBlock"}).find("b").text.split()[0].replace(",", ""))
            price = self.parse_cookie_count(item.find_element(By.CSS_SELECTOR, ".price").text)
            
            ratio = production / price if price else 0
            if ratio > best_ratio:
                best_ratio = ratio
                best_item = item

        return best_item

    def buy_items(self):
        """Continuously purchases the most cost-effective items."""
        while not self.stop_thread:
            current_cookies = self.get_current_cookies()
            unlocked_items = self.driver.find_elements(By.CSS_SELECTOR, ".product.unlocked")

            if not unlocked_items:
                continue

            for item in unlocked_items:
                price = self.parse_cookie_count(item.find_element(By.CSS_SELECTOR, ".price").text)
                if current_cookies >= price:
                    item.click()

            best_item = self.find_best_purchase(unlocked_items)
            if best_item:
                price = self.parse_cookie_count(best_item.find_element(By.CSS_SELECTOR, ".price").text)
                if current_cookies >= price:
                    best_item.click()

    def collect_upgrades(self):
        """Purchases available upgrades when enabled."""
        upgrades = self.driver.find_elements(By.CSS_SELECTOR, ".upgrade.enabled")
        for upgrade in upgrades:
            try:
                upgrade.click()
            except Exception:
                pass

    def main_loop(self):
        """Main gameplay loop for clicking the big cookie and managing upgrades."""
        try:
            while True:
                # Click big cookie
                self.big_cookie.click()

                # Collect golden cookies
                shimmer = self.driver.find_elements(By.CSS_SELECTOR, ".shimmer")
                if shimmer:
                    shimmer[0].click()

                # Buy upgrades
                self.collect_upgrades()

                # Periodically save the game state
                if time.time() % 10 < 0.1:
                    self.save_game_state()
        except KeyboardInterrupt:
            print("Stopping the bot...")
        finally:
            self.stop_thread = True

    def run(self):
        """Runs the bot by initializing components and starting the gameplay."""
        self.load_game_state()
        self.dismiss_popups()

        self.big_cookie = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#bigCookie"))
        )

        buy_thread = threading.Thread(target=self.buy_items)
        buy_thread.start()

        self.main_loop()
        buy_thread.join()
        self.driver.quit()


if __name__ == "__main__":
    bot = CookieClickerBot()
    bot.run()