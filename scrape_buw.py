from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException
from selenium.webdriver.support.ui import Select
from selenium .webdriver import ChromeOptions
import pandas as pd
import re

term = input('What would you like to read about? ')
term = term.replace(' ', '+')
min_year = int(input('What is the oldest book you are interested in? '))
min_length = 100
max_length = 700
max_books = int(input('How many books do you want? '))


options = ChromeOptions()
options.add_argument('--headless')
prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome('../install/chromedriver', options=options)
driver.get(f'https://chamo.buw.uw.edu.pl/heading/search?match_1=MUST&field_1=heading&term_1={term}&facet_heading_type=subject&sort=heading')

def next_or_break(driver):
    try:
        next_button = driver.find_element_by_link_text('Następne>')
        next_button.click()
        return True
    except (NoSuchElementException, ElementNotInteractableException):
        return 'no next'


links = set()
while True:
    tags_from_page = driver.find_element_by_tag_name('tbody').find_elements_by_tag_name('a')
    for tag in tags_from_page:
        try:
            links.add(tag.get_attribute('href'))
        except StaleElementReferenceException:
            pass
    if next_or_break(driver) == 'no next': break


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
    def check_quality(self):
        if self.year >= min_year and self.pages >= min_length and self.pages <= max_length:
            Book.interesting_books.add(self)


def get_book_attributes(book, record):
    title = record.find_element_by_class_name('title').text
    book.title = re.sub(r' / .+', '', title)

    try:
        book.author = record.find_element_by_class_name('author').text
    except NoSuchElementException:
        pass

    if 'BUW Magazyn' in record.text:
        book.storage = 'magazyn'

    infos = record.find_elements_by_tag_name('tr')
    for info in infos:
        if 'Klasyfikacja WD' in info.text:
            book.WD_signature = info.find_element_by_tag_name('a').text
        elif 'Adres wyd.' in info.text:
            publisher = info.find_element_by_tag_name('span').text
            publisher_with_colon = re.search(r'.+ : ?(.+),.*(\d{4})', publisher)
            if publisher_with_colon:
                publisher = publisher_with_colon
            else:
                publisher = re.search(r'.+? (.+),.*(\d{4})', publisher)
            book.publisher = publisher.group(1)
            book.year = int(publisher.group(2))
        elif 'Opis fiz.' in info.text:
            pages = info.find_element_by_tag_name('span').text
            pages = re.sub(r'\[.+?\]', '', pages)
            book.pages = int(re.search(r'\d+', pages).group(0))
    return book


def get_books(driver):
    records = driver.find_element_by_class_name('records').find_elements_by_tag_name('li')
    for record in records:
        too_old = 'not too old'

        if ('BUW Wolny Dostęp' in record.text or 'BUW Magazyn' in record.text) and 'Adres wyd.' in record.text and 'Opis fiz.' in record.text:
            book = Book()
            book = get_book_attributes(book, record)
            book.check_quality()
            if book.year < min_year and book.year > 0:
                too_old = 'too old'
                break
    return too_old


for link_to_tag in links:
    driver.get(link_to_tag)
    select = Select(driver.find_element_by_id('search_sort'))
    select.select_by_value('5')
    too_old = get_books(driver)
    while too_old == 'not too old':
        if next_or_break(driver) == 'no next': break
        too_old = get_books(driver)

driver.close()

interesting_books = [{
'title':book.title,
'author':book.author,
'publisher':book.publisher,
'year':book.year,
'pages':book.pages,
'WD_signature':book.WD_signature,
'storage':book.storage} for book in Book.interesting_books]

reading_list = pd.DataFrame(columns=['title','author', 'WD_signature', 'storage', 'publisher', 'year', 'pages'], data=interesting_books)

reading_list.drop_duplicates(inplace=True)
reading_list.sort_values(by='year', ascending=False, inplace=True)
reading_list.drop_duplicates('title', inplace=True)

for title in reading_list.title.unique():
    df = reading_list[reading_list['title'] == title]
    if len(df) > 1:
        max_len_for_title = max(df['pages'])
        reading_list.drop(reading_list[(reading_list['title'] == title) & (reading_list['pages'] < max_len_for_title)].index, inplace=True)

output_file = f'/home/arvala/Documents/Books/Reading_lists/{term}_reading_list.tsv'
reading_list[:min(len(reading_list), max_books)].to_csv(output_file, index=False, sep='\t')
