from scrapy.spider import BaseSpider

class HealthgradesSpider(BaseSpider):
	name = "healthgrades"
	allowed_domains = ["healthgrades.com"]
	start_urls = [
		"http://www.healthgrades.com/find-a-doctor"
	]

	def parse(self, response):
		filename = response.url.split("/")[-2]
		open(filename, 'wb').write(response.body)