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
        driver.implicitly_wait(5)
        driver.get("http://www.healthgrades.com/find-a-doctor")

        state_form_entry = driver.find_element_by_id('multi_search_location_textbox')
        state_form_entry.click()
        state_form_entry.send_keys("Missouri")

        driver.find_element_by_xpath("//span[@class='hgSearchTable']/span[@class='hgSearchTableRow']/button[@class='buttonHeaderSearch']").click()
        
        super(HealthgradesSpider, self).__init__()

    def parse(self, response):
        driver = self.driver

        # Get number of pages to flip through pagination
        no_pages = driver.find_element_by_xpath("//span[@class='pagination']/span[3]")
        no_pages = re.findall(r'\d+', no_pages.text)
        no_pages = int(no_pages[0])
        
        current_page = 1
        next_page = 2

        while current_page <= 5: #no_pages:

            # First doctor listing must be handled seperately

            # Get name and degree
            try:
                name = driver.find_element_by_xpath("//div[@class='listing first']/div[@class='listingInformationColumn']/div[@class='listingHeader']/div[@class='listingHeaderLeftColumn']/h2/a[@class='providerSearchResultSelectAction']").text
            except NoSuchElementException: 
                name = driver.find_element_by_xpath("//div[@class='listing enhancedlisting first']/div[@class='listingOuter']/div[@class='listingInner']/div[@class='listingInformationColumn']/div[@class='listingHeader']/div[@class='listingHeaderLeftColumn']/h2/a[@class='providerSearchResultSelectAction']").text

            split_text = re.findall(r"[\w'|-]+", name)
            degree = split_text[-1]

            split_text.pop()
            name = ' '.join(split_text)


            # Get years in practice
            try:
                years = driver.find_element_by_xpath("//div[@class='listing first']/div[@class='listingInformationColumn']/div[@class='listingBody clearfix']/div[@class='listingCenterColumn']/div[@class='listingProfileContent']/ul/li[@class='dataDebug yearsOfPractice']/a").text
            except NoSuchElementException:
                years = driver.find_element_by_xpath("//div[@class='listing enhancedlisting first']/div[@class='listingOuter']/div[@class='listingInner']/div[@class='listingInformationColumn']/div[@class='listingBody clearfix']/div[@class='listingCenterColumn']/div[@class='listingProfileContent']/ul/li[@class='dataDebug'][1]/a").text

            years = re.findall(r"[\w'|-]+", years)
            years = years[0]


            # Create and yield item
            item = HealthgradesItem()
            item['Name'] = name
            item['Degree'] = degree
            item['YearsInPractice'] = years

            yield item

            doctors = []
            listing = 1
            enhancedlisting = 1

            doctors.extend(driver.find_elements_by_xpath("//div[@class='listingInformationColumn']"))
            doctors.pop(0) # Doctor 0 will be first doc, already scraped

            for doctor in doctors:
                isenhanced = False

                try:
                    name = driver.find_element_by_xpath("//div[@class='listing'][" + str(listing) + "]/div[@class='listingInformationColumn']/div[@class='listingHeader']/div[@class='listingHeaderLeftColumn']/h2/a[@class='providerSearchResultSelectAction']")
                    isenhanced = False
                    listing += 1
                except NoSuchElementException:
                    name = driver.find_element_by_xpath("//div[@class='listing enhancedlisting'][" + str(enhancedlisting) + "]/div[@class='listingOuter']/div[@class='listingInner']/div[@class='listingInformationColumn']/div[@class='listingHeader']/div[@class='listingHeaderLeftColumn']/h2/a[@class='providerSearchResultSelectAction']")
                    isenhanced = True
                    enhancedlisting += 1

                # Get name and degree
                text = name.text

                split_text = re.findall(r"[\w'|-]+", text)
                degree = split_text[-1]

                split_text.pop()
                name = ' '.join(split_text)


                # Get years in practice
                years = driver.find_element_by_xpath("//li[@class='dataDebug yearsOfPractice']/a").text
                years = re.findall(r"[\w'|-]+", years)
                years = years[0]


                # Create and yield item
                item = HealthgradesItem()
                item['Name'] = name
                item['Degree'] = degree
                item['YearsInPractice'] = years

                yield item

            if current_page == no_pages:
                driver.quit()

            if no_pages > 1 and current_page != no_pages:
                next_page_link = driver.find_element_by_xpath("//a[@class='paginationRight']")

            if current_page != no_pages:
                next_page_link.click()
            
            current_page = next_page
            next_page += 1

        driver.quit()
            
