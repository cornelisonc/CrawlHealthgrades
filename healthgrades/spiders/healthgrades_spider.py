from selenium import selenium
from selenium.selenium import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from healthgrades.items import HealthgradesItem
import time
import datetime
import re
import string

class HealthgradesSpider(BaseSpider):
    name = "healthgrades"
    allowed_domains = ["healthgrades.com"]
    start_urls = [
        "http://www.healthgrades.com/find-a-doctor"
    ]

    def __init__(self, **kwargs):
        self.driver = webdriver.Firefox()
        driver = self.driver
        driver.implicitly_wait(30)
        driver.get("http://www.healthgrades.com/find-a-doctor")

        state_form_entry = driver.find_element_by_id('multi_search_location_textbox')
        state_form_entry.click()
        state_form_entry.send_keys("Missouri")

        driver.find_element_by_xpath("//span[@class='hgSearchTable']/span[@class='hgSearchTableRow']/button[@class='buttonHeaderSearch']").click()
        
        super(HealthgradesSpider, self).__init__()

    def parse(self, response):
        driver = self.driver

        no_pages = driver.find_element_by_xpath("//span[@class='pagination']/span[3]")
        no_pages = re.findall(r'\d+', no_pages.text)
        no_pages = int(no_pages[0])
        print no_pages
