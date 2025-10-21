import os
import ssl
import urllib.request
import json
import random
import requests
from bs4 import BeautifulSoup
from random import choice
from time import sleep

from ..utility.base_workflow import BaseWorkflow


WORKFLOW_NAME = 'DownloadFiles'
WORKFLOW_DESCRIPTION = 'Download files'

DEFAULT_INPUT_WAIT_TIME = 2


def load():
    return DownloadFiles()


class DownloadFiles(BaseWorkflow):

    def __init__(self, input_wait_time=DEFAULT_INPUT_WAIT_TIME):
        super().__init__(name=WORKFLOW_NAME, description=WORKFLOW_DESCRIPTION)
        self.input_wait_time = input_wait_time

    def action(self, extra=None):
        self._download_files()


    """ PRIVATE """

    def _download_files(self):
        random_function_selector = [self._download_xkcd, self._download_wikipedia, self._download_nist]
        directory = os.path.join(os.path.expanduser("~"), "Downloads")
        random.choice(random_function_selector)(directory)
        sleep(self.input_wait_time)

    def _download_wikipedia(self, directory):
        url = "https://en.wikipedia.org/wiki/Special:Random"
        try:
            request = requests.get(url, verify=False)
        except urllib.error.URLError:
            return
        file_name = "wiki" + str(random.randint(1, 100000)) + ".html"
        open(os.path.join(directory, file_name), 'wb').write(request.content)

    def _download_xkcd(self, directory):
        # Disable certificate verification. Will display warning when run.
        ssl._create_default_https_context = ssl._create_unverified_context
        xkcd_url = "https://xkcd.com/" + str(random.randint(1, 1000)) + "/info.0.json"
        try:
            request = urllib.request.urlopen(xkcd_url)
        except urllib.error.URLError:
            return
        pic_url = json.load(request)['img']
        pic_name = pic_url.split("https://imgs.xkcd.com/comics/", 1)[1]
        try:
            urllib.request.urlretrieve(pic_url, os.path.join(directory, pic_name))
        except urllib.error.URLError:
            return

    def _download_nist(self, directory):
        # Get random page of NIST search results
        nist_search_url = "https://www.nist.gov/publications/search?k=&t=&a=&ps=All&n=&d[min]=&d[max]=&page=" + str(random.randint(1, 2000))
        nist_search_request = requests.get(nist_search_url).text
        nist_search_soup = BeautifulSoup(nist_search_request, features="lxml")
        publications_links = (nist_search_soup.select('a[href^="/publications"]'))

        # Download random publication from the NIST search page
        random_publication = choice(publications_links[1:])
        publication_url = "https://www.nist.gov" + random_publication.get('href')
        publication_page_text = requests.get(publication_url).text
        publication_page_soup = BeautifulSoup(publication_page_text, features="lxml")
        publication_download_link = publication_page_soup.find('a', href=True, text='Local Download')
        if publication_download_link is not None:
            file_url = (publication_download_link.get('href'))
            file_name = publication_url.split("https://www.nist.gov/publications/", 1)[1] + ".pdf"
            try:
                urllib.request.urlretrieve(file_url,  os.path.join(directory, file_name))
            except urllib.error.URLError:
                return

