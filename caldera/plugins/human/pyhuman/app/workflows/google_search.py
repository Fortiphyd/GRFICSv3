from time import sleep
import os
import random

from ..utility.base_workflow import BaseWorkflow
from ..utility.webdriver_helper import WebDriverHelper
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

WORKFLOW_NAME = 'GoogleSearcher'
WORKFLOW_DESCRIPTION = 'Search for something on Google'
DEFAULT_WAIT_TIME = 2
MAX_PAGES = 5
MAX_NAVIGATION_CLICKS = 5
SEARCH_LIST = 'google_searches.txt'


def load():
    driver = WebDriverHelper()
    return GoogleSearch(driver=driver)


class GoogleSearch(BaseWorkflow):

    def __init__(self, driver, input_wait_time=DEFAULT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)

        self.input_wait_time = input_wait_time
        self.search_list = self._load_search_list()

    def action(self, extra=None):
        self._search_web()

    """ PRIVATE """

    def _search_web(self):
        random_search = self._get_random_search()
        try:
            # Navigate to google.com
            self.driver.driver.get('https://www.google.com')
            assert 'Google' in self.driver.driver.title
            sleep(DEFAULT_WAIT_TIME)

            # Randomly choose whether to google a search term or click lucky button
            chosen_action = random.choice(["search-term", "lucky"])

            if chosen_action == "search-term":
                self._google_search(random_search)
                sleep(DEFAULT_WAIT_TIME)
                self._browse_search_results()
                sleep(DEFAULT_WAIT_TIME)
                self._click_on_search_result()
            elif chosen_action == "lucky":
                self._hover_click_feeling_lucky()
            
            sleep(DEFAULT_WAIT_TIME)
            # Randomly navigate on the current website
            self._navigate_webpage()

        except Exception as e:
            print('Error performing google search %s: %s' % (random_search.rstrip(), e))

    def _click_on_search_result(self):
        print(".... Clicking on search  result")
        search_result = WebDriverWait(self.driver.driver, 15).until(EC.visibility_of_any_elements_located((By.CLASS_NAME, "yuRUbf")))[0]
        ActionChains(self.driver.driver).move_to_element(search_result).click(search_result).perform()

    def _browse_search_results(self):
        # Click through search result pages
        print(".... Browsing search results")
        for _ in range(0,random.randint(0,MAX_PAGES)):
            next_button = WebDriverWait(self.driver.driver, 15).until(EC.visibility_of_any_elements_located((By.LINK_TEXT, "Next")))[0]
            ActionChains(self.driver.driver).move_to_element(next_button).click(next_button).perform()
            sleep(DEFAULT_WAIT_TIME)

    def _google_search(self, random_search):
        print(".... Googling:", random_search.rstrip())
        elem = self.driver.driver.find_element(By.NAME,'q')
        elem.clear()
        sleep(self.input_wait_time)
        elem.send_keys(random_search)
        self.driver.driver.execute_script("window.scrollTo(0, document.body.Height)")

    def _hover_click_feeling_lucky(self):
        print(".... Hovering & clicking 'I'm Feeling lucky' button")
        element = WebDriverWait(self.driver.driver, 15).until(EC.visibility_of_any_elements_located((By. CSS_SELECTOR, '[name="btnI"][type="submit"]')))[0]
        ActionChains(self.driver.driver).move_to_element(element).click(element).perform()

    def _navigate_webpage(self):
        # Navigate webpage
        navigation_clicks = random.randrange(0, MAX_NAVIGATION_CLICKS)
        print(".... Navigating and highlighting web page", navigation_clicks, "times")
        for _ in range(0, navigation_clicks):
            clickables = self.driver.driver.find_elements(By.TAG_NAME, ("a"))
            if len(clickables) == 0:
                return
            clickable = random.choice(clickables)
            try:
                self._highlight(clickable)
                self.driver.driver.execute_script("arguments[0].target='_self';", clickable)
                clickable.click()
                print("........ successful navigation")
            except:
                print("........ X unsuccessful navigation")
                pass

    def _get_random_search(self):
        return random.choice(self.search_list)

    def _highlight(self, element):
        driver = element._parent
        def apply_style(s):
            driver.execute_script("arguments[0].setAttribute('style', arguments[1]);",
                                element, s)
        original_style = element.get_attribute('style')
        apply_style("border: 10px solid red;")
        sleep(DEFAULT_WAIT_TIME)
        apply_style(original_style)

    @staticmethod
    def _load_search_list():
        with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                               'data', SEARCH_LIST))) as f:
            wordlist = f.readlines()
        return wordlist

