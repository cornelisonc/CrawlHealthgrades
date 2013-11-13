from selenium import selenium
from selenium.selenium import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from healthgrades.items import HealthgradesItem
import time
import datetime
import re
import string

class HealthgradesSpider(CrawlSpider):
    name = "healthgrades"
    allowed_domains = ["healthgrades.com"]
    rules = (Rule(SgmlLinkExtractor(restrict_xpaths=('//a[contains(@href,"pagenumber=")]')), callback='parse_doctors_page', follow=True, ),)

    def __init__(self, crawl_state="Missouri", *args, **kwargs):
        super(HealthgradesSpider, self).__init__(*args, **kwargs)
        self.start_urls = ["http://www.healthgrades.com/provider-search-directory/search?q=&prof.type=provider&search.type=condition&loc=" + crawl_state + "&locIsSolrCity=false"]

    def parse_doctors_page(self, response):
        hxs = HtmlXPathSelector(response)

        doctors = hxs.select("//div[@class='listingInformationColumn']")

        for doctor in doctors:

            # Get name and degree
            doctor_name_link    = doctor.select(".//div[@class='listingHeader']/div[@class='listingHeaderLeftColumn']/h2/a[@class='providerSearchResultSelectAction']/@href").extract()

            name                = doctor.select(".//div[@class='listingHeader']/div[@class='listingHeaderLeftColumn']/h2/a[@class='providerSearchResultSelectAction']/text()").extract()
            split_text          = re.findall(r"[\w'|-]+", str(name))
            
            degree = split_text[-1]
            split_text.pop()
            
            name = ' '.join(split_text)
            name = re.sub(r"u'", "", name)

            doctor_name_link = (str(doctor_name_link[0]))
            doctor_name_link = doctor_name_link + "/appointment"
            doctor_name_link = "http://www.healthgrades.com" + doctor_name_link

            item = Request(url=doctor_name_link,
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
# 
    def get_hospital_information(self, response):
        root_url    = response.url
        old_item    = response.meta['item']
        hxs         = HtmlXPathSelector(response)

        hospitals = hxs.select("//div[@id='aboutHospitals2']/div[@class='componentPresentationLeftColumn']/div[@class='componentPresentationNav']/div/div[@class='positionRelative']").extract()
        other_hospitals = hxs.select("//div[@id='aboutHospitals2']/div[@class='componentPresentationLeftColumn']/div[@class='componentPresentationNav']/div/div[@class='positionRelative']/dl").extract()
        print("\n\nHospitals:")
        print(hospitals)
        print("Other Hospitals:")
        print(str(other_hospitals) + "\n\n")

        # If this page doesn't have the info, we need to send another request
        # if not hospitals:
        #     request = Request(url=root_url + '/hospital-quality', callback=self.get_internal_hospital_information)
        #     request.meta['item'] = old_item

        #     return request

        # else:
            # for hospital in hospitals:

        return old_item

    def get_internal_hospital_information(self, response):
        hxs = HtmlXPathSelector(response)
        old_item = response.meta['item']
        old_item['AffiliatedHospitals'] = []

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
        item['AffiliatedHospitals'].extend(hospital)
        print(item['AffiliatedHospitals'])
        print("\n\n")

        return item

# Helper Functions
def get_years_in_practice( doctor ):
    years = doctor.select(".//a[contains(text(), 'Years of Practice')]/text()").extract()
    
    if not years:
        return "Years not listed"

    years = re.findall(r'[0-9]{1,2}', str(years))
    return years[0]

def get_number_of_insurance_carriers( doctor ):
    num_carriers = doctor.select(".//a[contains(text(), 'Insurance Carriers')]/text()").extract()
    
    if not num_carriers:
        return "Insurance carriers not listed"

    num_carriers = re.findall(r"[0-9]{1,2}", str(num_carriers))
    return num_carriers[0]

def get_number_of_offices( doctor ):
    numOffices = doctor.select(".//a[contains(text(), 'Office Location')]/text()").extract()

    if not numOffices:
        return "Offices not listed"

    numOffices = re.findall(r"[0-9]{1,2}", str(numOffices))
    numOffices = numOffices[0]
    return numOffices

def get_office_addresses( doctor ):
    officeAddresses = ""

    for office in doctor.select(".//div[@class='addresses']/div[contains(@class, 'address')]/text()").extract():
        thisOffice = office.replace(' (less)','')
        officeAddresses += thisOffice
        officeAddresses += ";"

    return officeAddresses

def get_specialties( doctor ):
    specialties = doctor.select(".//div[@class='listingHeaderLeftColumn']/p/text()").extract()

    if not specialties:
        return "Specialties not listed"
    
    specialties = str(specialties).replace(', ', ';')
    return specialties

def get_hospital_affiliations( doctor ):

    affiliations = doctor.select(".//a[contains(text(), 'Hospital Affiliation')]/text()").extract()

    if not affiliations:
        return "Hospital affiliations not listed"

    affiliations = re.findall(r"[0-9]{1,2}", str(affiliations))
    affiliations = affiliations[0]
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
