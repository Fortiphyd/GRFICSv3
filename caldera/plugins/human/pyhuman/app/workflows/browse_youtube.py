from time import sleep
import os
import random

# from soupsieve import select

from ..utility.base_workflow import BaseWorkflow
from ..utility.webdriver_helper import WebDriverHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import ElementNotInteractableException

WORKFLOW_NAME = 'YoutubeBrowser'
WORKFLOW_DESCRIPTION = 'Browse Youtube'

DEFAULT_INPUT_WAIT_TIME = 2
MIN_WATCH_TIME = 2 # Minimum amount of time to watch a video, in seconds
MAX_WATCH_TIME = 150 # Maximum amount of time to watch a video, in seconds
MIN_WAIT_TIME = 2 # Minimum amount of time to wait after searching, in seconds
MAX_WAIT_TIME = 5 # Maximum amount of time to wait after searching, in seconds
MAX_SUGGESTED_VIDEOS = 10

SEARCH_LIST = 'browse_youtube.txt'

def load():
    driver = WebDriverHelper()
    return YoutubeSearch(driver=driver)


class YoutubeSearch(BaseWorkflow):

    def __init__(self, driver, input_wait_time=DEFAULT_INPUT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION, driver=driver)

        self.input_wait_time = input_wait_time
        self.search_list = self._load_search_list()

    def action(self, extra=None):
        self._search_web()

    """ PRIVATE """

    def _search_web(self):
        random_search = self._get_random_search()

        # Navigate to youtube
        self.driver.driver.get('https://www.youtube.com')
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        # Perform a youtube search
        search_element = self.driver.driver.find_element(By.CSS_SELECTOR, 'input#search') # search bar
        search_element.send_keys(random_search)
        search_element.submit()
        sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))

        # Click on a random video from the search results
        WebDriverWait(self.driver.driver, 10).until(EC.presence_of_all_elements_located((By.ID, "video-title")))
        search_results = self.driver.driver.find_elements(By.ID, "video-title")
        search_results[random.randrange(0, len(search_results)-1)].click()
        sleep(random.randrange(MIN_WATCH_TIME, MAX_WATCH_TIME))

        # Click on a random video from the suggested videos
        for _ in range(0,random.randrange(0,MAX_SUGGESTED_VIDEOS)):
            sleep(random.randrange(MIN_WAIT_TIME, MAX_WAIT_TIME))
            suggested_videos = self.driver.driver.find_elements(By.ID, "video-title")
            try:
                suggested_videos[random.randrange(0,len(suggested_videos)-1)].click()
            except ElementNotInteractableException as e:
                pass

    def _get_random_search(self):
        search_term = random.choice(self._load_search_list()).rstrip('\n')
        return search_term

    @staticmethod
    def _load_search_list():
        with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                               'data', SEARCH_LIST))) as f:
            wordlist = f.readlines()
        return wordlist

