from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

from .base_driver import BaseDriverHelper

DRIVER_NAME = 'ChromeWebDriver'

class WebDriverHelper(BaseDriverHelper):

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")

    def __init__(self):
        super().__init__(name=DRIVER_NAME)
        self._driver_path = ChromeDriverManager().install()
        self._driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)

    @property
    def driver(self):
        return self._driver
    
    def cleanup(self):
        self._driver.quit()

    """ PRIVATE """

    def check_valid_driver_connection(self):
        try:
            driver = webdriver.Chrome(self._driver_path)
            driver.quit()
            return True
        except Exception as e:
            print('Could not load ChromeDriver: %s'.format(e))
            return False
