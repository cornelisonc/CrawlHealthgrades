# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field

class HealthgradesItem(Item):
    Name                    = Field()
    Degree                  = Field()
    YearsInPractice         = Field()
    NumOffices              = Field()
    OfficeLocations         = Field()
    NumInsurers             = Field()
    AcceptedInsurers        = Field()
    Specialties             = Field()
    NumHospitalAffiliations = Field()
    AffiliatedHospitals     = Field()
    MedicalSchool           = Field()
    Internship              = Field()
    Residency               = Field()
    pass
