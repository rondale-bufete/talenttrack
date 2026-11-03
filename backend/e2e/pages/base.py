"""
Page Object Model (POM).

Each page class knows HOW to find things on one screen; tests only say WHAT to do
("create a job", "advance Ana"). If the HTML changes, you fix one page class instead
of every test. Interviewers often ask about this pattern.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def tid(test_id):
    """Locator for data-testid attributes, which don't break when CSS or text changes."""
    return By.CSS_SELECTOR, f'[data-testid="{test_id}"]'


class BasePage:
    path = "/"

    def __init__(self, driver, base_url, timeout=10):
        self.driver = driver
        self.base_url = base_url
        # Explicit wait: poll until a condition is true. Never use time.sleep in UI tests.
        self.wait = WebDriverWait(driver, timeout)

    def open(self):
        self.driver.get(self.base_url + self.path)
        return self

    def find(self, locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def find_all(self, locator):
        return self.driver.find_elements(*locator)

    def click(self, locator):
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def type(self, locator, text):
        el = self.find(locator)
        el.clear()
        el.send_keys(str(text))

    def text_of(self, locator):
        return self.find(locator).text

    def wait_for_text(self, locator, text):
        self.wait.until(EC.text_to_be_present_in_element(locator, text))
