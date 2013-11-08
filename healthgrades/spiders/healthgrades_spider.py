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

        while current_page <= 1: #no_pages:

            doctors = []
            doctors.extend(driver.find_elements_by_xpath("//div[@class='listingInformationColumn']"))

            for doctor in doctors:

                # Get name and degree
                doctor_name_link    = doctor.find_element_by_xpath(".//div[@class='listingHeader']/div[@class='listingHeaderLeftColumn']/h2/a[@class='providerSearchResultSelectAction']")
                
                name                = doctor_name_link.text
                split_text          = re.findall(r"[\w'|-]+", name)
                
                degree = split_text[-1]
                split_text.pop()
                
                name = ' '.join(split_text)

                # Expand all the office links
                try:
                    doctor.find_element_by_partial_link_text("more)").click()
                except NoSuchElementException:
                    pass

                # Get doctor hash for inner pages
                doctor_hash = doctor_name_link.get_attribute("href")
                doctor_hash = doctor_hash.replace('http://www.healthgrades.com/physician/', '')

                get_insurance_accepted(doctor_hash)

                # Create and yield item
                item                    = HealthgradesItem()
                item['Name']            = name
                item['Degree']          = degree
                item['YearsInPractice'] = get_years_in_practice(doctor)
                item['NumOffices']      = get_number_of_offices(doctor)
                item['OfficeLocations'] = get_office_addresses(doctor)

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

# Helper Functions
def get_years_in_practice( doctor ):
    try:
        years = doctor.find_element_by_partial_link_text("Years of Practice").text
        years = re.findall(r"[\w'|-]+", years)
        return years[0]
    except NoSuchElementException:
        return "Years not listed"

def get_number_of_offices( doctor ):
    try:
        numOffices = doctor.find_element_by_partial_link_text("Office Location").text
        numOffices = re.findall(r"[\w'|-]+", numOffices)
        numOffices = numOffices[0]
    except NoSuchElementException:
        numOffices = "Offices not listed"

    return numOffices

def get_office_addresses( doctor ):
    officeAddresses = ""
    for office in doctor.find_elements_by_xpath(".//div[@class='addresses']/div[contains(@class, 'address')]"):
        thisOffice = office.text.replace(' (less)','')
        officeAddresses += thisOffice
        officeAddresses += ";"

    return officeAddresses
    