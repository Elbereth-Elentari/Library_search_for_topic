from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium .webdriver import ChromeOptions
from bs4 import BeautifulSoup

import pandas as pd
import re
from get_books_by_category import next_or_break, deduplicate_books


class Book:
    interesting_books = set()

    def __init__(self):
        self.title = ''
        self.author = ''
        self.publisher = ''
        self.year = 0
        self.pages = 0
        self.WD_signature = ''
        self.storage = ''

    def get_book_attributes(self, record):
        title = record.find(class_='title').text
        self.title = re.sub(r' / .+', '', title)

        try:
            self.author = record.find(class_='author').text
        except:
            pass

        if 'BUW Magazyn' in record.text:
            self.storage = 'magazyn'

        infos = record.find_all('tr')
        for info in infos:
            if 'Klasyfikacja WD' in info.text:
                self.WD_signature = info.find('a').text
            elif 'Adres wyd.' in info.text:
                publisher = info.find('span')
                publisher_with_colon = re.search(r'.+ : ?(.+),?.*(\d{4})', publisher.text)
                if publisher_with_colon:
                    publisher = publisher_with_colon
                else:
                    publisher = re.search(r'.+? (.+),?.*(\d{4})', publisher.text)
                self.publisher = publisher.group(1)
                self.year = int(publisher.group(2))
            elif 'Opis fiz.' in info.text:
                pages = info.find('span').text
                pages = re.sub(r'\[.+?\]', '', pages)
                self.pages = int(re.search(r'\d+', pages).group(0))

    def check_quality(self, record):
        if self.pages >= min_length and self.pages <= max_length:
            Book.interesting_books.add(self)


def save_batch(counter):
    interesting_books = [{'title':book.title, 'author':book.author, 'publisher':book.publisher, 'year':book.year, 'pages':book.pages, 'WD_signature':book.WD_signature, 'storage':book.storage} for book in Book.interesting_books]

    reading_list = pd.DataFrame(columns=['title','author', 'WD_signature', 'storage', 'publisher', 'year', 'pages'], data=interesting_books)

    reading_list = deduplicate_books(reading_list)
    reading_list.to_csv('BUW_catalogue_{}.tsv'.format(counter), index=False, sep='\t')
    Book.interesting_books.clear()
    return True


def get_books(driver):
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    all = soup.find('div', class_='resultCount').span.text
    all = re.search(r' z (\d+)', all).group(1)
    all = int(all)
    print('Scrapeable catalogue size', all)
    record_counter = 320831
    while record_counter < all:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        records = soup.find(class_='records').find_all('li')
        for record in records:
            if 'Adres wyd.' in record.text and 'Opis fiz.' in record.text:
                book = Book()
                book.get_book_attributes(record)
                book.check_quality(record)
            if record_counter % 100 == 0:
                print('Scraping progress:', record_counter/all)

            if len(Book.interesting_books) % 1000 == 0 and len(Book.interesting_books) > 0:
                save_batch(record_counter)

            record_counter += 1
        if next_or_break(driver) == 'no next': break
    return True


if __name__ == '__main__':
    min_length = 100
    max_length = 700

    options = ChromeOptions()
    options.add_argument('--headless')
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome('../install/chromedriver', options=options)
    driver.get('https://chamo.buw.uw.edu.pl/search/query?filter_date=1.201.2018&filter_date=1.201.2017&filter_date=1.202.2020&filter_date=1.201.2019&filter_date=1.201.2014&filter_date=1.201.2013&filter_date=1.201.2016&filter_date=1.202.2021&filter_date=1.201.2015&filter_date=1.200.2009&filter_date=1.201.2010&filter_date=1.201.2012&filter_date=1.201.2011&filter_date=1.200.2001&filter_date=1.200.2002&filter_date=1.200.2003&filter_date=1.200.2004&filter_date=1.200.2005&filter_date=1.200.2006&filter_date=1.200.2007&filter_date=1.200.2008&filter_date=1.200.2000&filter_format=book&filter_lang=pol&filter_lang=eng&filter_loc=10000&filter_loc=10002&sort=dateNewest&pageNumber=32083&theme=system')

    get_books(driver)
    driver.close()
    save_batch('final_batch')
