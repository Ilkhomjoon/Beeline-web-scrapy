import scrapy
import datetime
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose, Join
from w3lib.html import remove_tags


class Article(scrapy.Item):
    url = scrapy.Field()  # URL of the article
    title = scrapy.Field()  # Title of the article
    text = scrapy.Field()  # Text of the article
    access_date = scrapy.Field()  # Date when the article was accessed
    creation_date = scrapy.Field()  # Date when the article was created
    category = scrapy.Field()  # Category of the article


class ArticleLoader(ItemLoader):
    """A custom Scrapy ItemLoader for loading information about an article."""

    # Use the TakeFirst output processor as the default output processor
    default_output_processor = TakeFirst()

    # Define the input and output processors for the title field
    title_in = MapCompose(remove_tags, str.strip)
    title_out = TakeFirst()

    # Define the input and output processors for the text field
    text_in = MapCompose(remove_tags, str.strip)
    text_out = Join('\n')


class BeelineSpider(scrapy.Spider):
    name = 'beeline'
    page_no = 1
    per_page = 20
    base_single_page_follow_url = 'https://beeline.uz/msapi/web/event/single/'
    writing_systems = {
        'lat': 'uz',
        'eng': 'en',
        'rus': 'ru'
    }

    def __init__(self, ws='lat', **kwargs):

        self.ws = ws
        self.start_urls = [
            f'https://beeline.uz/msapi/web/event/news?page={self.page_no}&per_page={self.per_page}&locale={self.writing_systems[self.ws]}']
        super().__init__(**kwargs)

    def parse(self, response):
        data = response.json()
        status_code = data['status_code']
        slugs = []
        if status_code == 200:
            events = data['data']['events']
            for event in events:
                slugs.append(event['slug'])
            yield from response.follow_all(
                [f'{self.base_single_page_follow_url}{slug}?locale={self.writing_systems[self.ws]}' for slug in slugs],
                self.parse_item)
            self.page_no += 1
            yield from response.follow_all([
                                               f'https://beeline.uz/msapi/web/event/news?page={self.page_no}&per_page={self.per_page}&locale={self.writing_systems[self.ws]}'],
                                           self.parse)
        else:
            print('Error: ', status_code)

    def parse_item(self, response):
        data = response.json()['data']
        a = ArticleLoader(item=Article(), response=response)
        a.add_value('url', response.url)
        a.add_value('title', data['name'])
        a.add_value('text', data['content'])
        a.add_value('creation_date', data['created_at'])
        a.add_value('access_date', datetime.datetime.now())
        a.add_value('category', data['categories'][0]['name'])
        yield a.load_item()
