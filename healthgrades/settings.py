# Scrapy settings for healthgrades project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'healthgrades'

SPIDER_MODULES = ['healthgrades.spiders']
NEWSPIDER_MODULE = 'healthgrades.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'healthgrades (+http://www.yourdomain.com)'
