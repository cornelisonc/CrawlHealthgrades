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

                item = Request(url=doctor_name_link.get_attribute("href") + "/appointment",
                    callback=self.get_accepted_insurance_carriers)
                item.meta['Name']                       = name
                item.meta['Degree']                     = degree
                item.meta['YearsInPractice']            = get_years_in_practice(doctor)
                item.meta['NumOffices']                 = get_number_of_offices(doctor)
                item.meta['OfficeLocations']            = get_office_addresses(doctor)
                item.meta['NumInsurers']                = get_number_of_insurance_carriers(doctor)
                item.meta['Specialties']                = get_specialties(doctor)
                item.meta['NumHospitalAffiliations']    = get_hospital_affiliations(doctor)

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

    def get_accepted_insurance_carriers(self, response):
        root_url = response.url.replace('/appointment', '')
        hxs = HtmlXPathSelector(response)

        insurance_carriers = hxs.select("///div[@id='appointmentsInsuranceAccepted']/div[@class='componentPresentationFull']/div[@class='componentPresentationContent']/ul/li").extract()

        if not insurance_carriers:
            insurance_carriers = hxs.select("//div[@class='insurancesAccepted']/ul[@class='noBottomMargin']/li").extract()

        more_insurance_carriers = hxs.select("///div[@class='insurancesAccepted']/div[@class='expand-section']/ul[@class='noBottomMargin noTopMargin']/li").extract()
        insurance_carriers.extend(more_insurance_carriers)

        if (insurance_carriers):
            semicolon_delimited = ''
            for insurance_carrier in insurance_carriers:
                if '<ul class="insurancePlanList"' in insurance_carrier:
                    insurance_carrier = clean_many_insurance_carriers(insurance_carrier)
                else:
                    insurance_carrier = insurance_carrier.replace('<li><span>', '')
                    insurance_carrier = insurance_carrier.replace('</span></li>', '')

                semicolon_delimited += str(insurance_carrier) + ';'

        else:
            semicolon_delimited = ("No insurance carriers listed")

        item                            = HealthgradesItem()
        item['Name']                    = response.meta['Name']
        item['Degree']                  = response.meta['Degree']
        item['YearsInPractice']         = response.meta['YearsInPractice']
        item['NumOffices']              = response.meta['NumOffices']
        item['OfficeLocations']         = response.meta['OfficeLocations']
        item['NumInsurers']             = response.meta['NumInsurers']
        item['Specialties']             = response.meta['Specialties']
        item['NumHospitalAffiliations'] = response.meta['NumHospitalAffiliations']
        item['AcceptedInsurers']        = semicolon_delimited

        request = Request(url=root_url + '/background-check', callback=self.get_background)
        request.meta['item'] = item

        return request

    def get_background(self, response):
        old_item     = response.meta['item']
        hxs         = HtmlXPathSelector(response)
        root_url    = response.url.replace('/background-check', '')

        schools = hxs.select("///div[@id='backgroundEducationAndTraining2']/div[@class='componentPresentationLeftColumn']/div[@class='componentPresentationNav']/div").extract()
        for school in schools:
            if "Medical School" in school:
                school_name = re.sub(r'(?s)<div>\s.*<dl><dt>', '', school)
                school_name = re.sub(r'(?s)</dt>\s.*', '', school_name)
                grad_year = re.findall(r'(?s)>([0-9]{4})<', school)
                if not grad_year:
                    grad_year = '0'
                old_item['MedicalSchool'] = school_name + ' (' + grad_year[0] + ')'
            elif "Internship" in school:
                school_name = re.sub(r'(?s)<div>\s.*<dl><dt>', '', school)
                school_name = re.sub(r'(?s)</dt>\s.*', '', school_name)
                grad_year = re.findall(r'(?s)>([0-9]{4})<', school)
                if not grad_year:
                    grad_year = '0'
                old_item['Internship'] = school_name + ' (' + grad_year[0] + ')'
            elif "Residency" in school:
                school_name = re.sub(r'(?s)<div>\s.*<dl><dt>', '', school)
                school_name = re.sub(r'(?s)</dt>\s.*', '', school_name)
                grad_year = re.findall(r'(?s)>([0-9]{4})<', school)
                if not grad_year:
                    grad_year = '0'
                old_item['Residency'] = school_name + ' (' + grad_year[0] + ')'

        request = Request(url=root_url, callback=self.get_hospital_information)
        request.meta['item'] = old_item

        return request

    def get_hospital_information(self, response):
        root_url    = response.url
        old_item    = response.meta['item']
        hxs         = HtmlXPathSelector(response)

        hospitals = hxs.select("//div[@id='aboutHospitals2']/div[@class='componentPresentationLeftColumn']/div[@class='componentPresentationNav']/div/div[@class='positionRelative']").extract()

        # If this page doesn't have the info, we need to send another request
        if not hospitals:
            request = Request(url=root_url + '/hospital-quality', callback=self.get_internal_hospital_information)
            request.meta['item'] = old_item

            return request

        # else:
            # for hospital in hospitals:

        return old_item

    def get_internal_hospital_information(self, response):
        hxs = HtmlXPathSelector(response)
        old_item = response.meta['item']

        hospitals = hxs.select("//div[@id='aboutHospitalCarousel']/ul/li").extract()

        for hospital in hospitals:
            hospital = re.findall(r'(?s)<li data-facility-id="(.*?)"', hospital)
            item = Request(url="http://www.healthgrades.com/ajax/facility/" + hospital[0] + "/tab/ProviderAboutFacility", callback=self.process_ajax_hospital_request)
            item.meta['item'] = old_item

        return item


    def process_ajax_hospital_request(self, response):
        hxs  = HtmlXPathSelector(response)
        item = response.meta['item']

        hospital = hxs.select("//h4/text()").extract()
        hospital_address = hxs.select("//p[@class='aboutFacilityContentHeaderContact']/strong/text()").extract()
        hospital.extend(", ")
        hospital.extend(hospital_address)
        hospital = ''.join(hospital)

        print("\n\n")        
        print(hospital)
        print("\n\n")
        return item

# Helper Functions
def get_years_in_practice( doctor ):
    try:
        years = doctor.find_element_by_partial_link_text("Years of Practice").text
        years = re.findall(r"[\w'|-]+", years)
        return years[0]
    except NoSuchElementException:
        return "Years not listed"

def get_number_of_insurance_carriers( doctor ):
    try:
        num_carriers = doctor.find_element_by_partial_link_text("Insurance Carriers").text
        num_carriers = re.findall(r"[\w'|-]+", num_carriers)
        return num_carriers[0]
    except NoSuchElementException:
        return "Insurance carriers not listed"

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

def get_specialties( doctor ):
    try:
        specialties = doctor.find_element_by_xpath(".//div[@class='listingHeaderLeftColumn']/p").text
        specialties = specialties.replace(', ', ';')
    except NoSuchElementException:
        specialties = "Specialties not listed"

    return specialties

def get_hospital_affiliations( doctor ):
    try:
        affiliations = doctor.find_element_by_partial_link_text('Hospital Affiliation').text
        affiliations = re.findall(r"[\w'|-]+", affiliations)
        affiliations = affiliations[0]
    except NoSuchElementException:
        affiliations = "Hospital affiliations not listed"

    return affiliations

def clean_many_insurance_carriers( insurance_carrier ):
    insurance_carrier = insurance_carrier.replace('</li></ul></li>', '')
    insurance_carrier = re.sub(r"</?a.*?>", "", insurance_carrier)
    insurance_carrier = insurance_carrier.replace('<li><span>', '').replace('</span></li>', '')
    insurance_carrier = insurance_carrier.replace('<ul class="insurancePlanList" style="display:none">', '').replace('</li>', '')
    split_html = insurance_carrier.split('<li>')
    split_html = split_html[2:]
    insurance_carrier = ";".join(split_html)

    return insurance_carrier        
