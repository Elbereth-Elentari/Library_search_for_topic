from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium .webdriver import ChromeOptions
import pandas as pd
import re


def get_conditions():
    term = input('What would you like to read about? ')
    term = term.replace(' ', '+')
    min_year = int(input('What is the oldest book you are interested in? '))
    min_length = 100
    max_length = 700
    max_books = int(input('How many books do you want? '))
    return term, min_year, min_length, max_length, max_books


def next_or_break(driver):
    try:
        next_button = driver.find_element_by_link_text('Następne>')
        next_button.click()
        return True
    except:
        return 'no next'


class Book:
    interesting_books = set()
    all_authors = set()
    authors_to_scrape = set()

    def __init__(self):
        self.title = ''
        self.author = ''
        self.publisher = ''
        self.year = 0
        self.pages = 0
        self.WD_signature = ''
        self.storage = ''

    def get_book_attributes(self, record):
        title = record.find_element_by_class_name('title').text
        self.title = re.sub(r' / .+', '', title)

        try:
            self.author = record.find_element_by_class_name('author').text
        except:
            pass

        if 'BUW Magazyn' in record.text:
            self.storage = 'magazyn'

        infos = record.find_elements_by_tag_name('tr')
        for info in infos:
            if 'Klasyfikacja WD' in info.text:
                self.WD_signature = info.find_element_by_tag_name('a').text
            elif 'Adres wyd.' in info.text:
                publisher_candidates = info.find_elements_by_tag_name('span')
                for publisher in publisher_candidates:
                    if publisher.get_attribute('class') != 'highlight':
                        publisher_with_colon = re.search(r'.+ : ?(.+),?.*(\d{4})', publisher.text)
                        if publisher_with_colon:
                            publisher = publisher_with_colon
                        else:
                            publisher = re.search(r'.+? (.+),?.*(\d{4})', publisher.text)
                        self.publisher = publisher.group(1)
                        self.year = int(publisher.group(2))
            elif 'Opis fiz.' in info.text:
                pages = info.find_element_by_tag_name('span').text
                pages = re.sub(r'\[.+?\]', '', pages)
                self.pages = int(re.search(r'\d+', pages).group(0))

    def check_quality(self, record):
        if self.year >= min_year and self.pages >= min_length and self.pages <= max_length:
            Book.interesting_books.add(self)
            if len(self.author) > 0 and self.author in Book.all_authors:
                author = record.find_element_by_class_name('author')
                Book.authors_to_scrape.add(author.get_attribute('href'))
            elif len(self.author) > 0:
                Book.all_authors.add(self.author)



def get_books(driver):
    records = driver.find_element_by_class_name('records').find_elements_by_tag_name('li')
    for record in records:
        too_old = 'not too old'

        if ('BUW Wolny Dostęp' in record.text or 'BUW Magazyn' in record.text) and 'Adres wyd.' in record.text and 'Opis fiz.' in record.text:
            book = Book()
            book.get_book_attributes(record)
            book.check_quality(record)
            if book.year < min_year and book.year > 0:
                too_old = 'too old'
                break
    return too_old


def create_link_set(driver):
    links = set()
    while True:
        tags_from_page = driver.find_element_by_tag_name('tbody').find_elements_by_tag_name('a')
        for tag in tags_from_page:
            try:
                links.add(tag.get_attribute('href'))
            except:
                pass
        if next_or_break(driver) == 'no next': break
    return links


def get_books_from_links(link_set):
    for link in link_set:
        driver.get(link)
        select = Select(driver.find_element_by_id('search_sort'))
        select.select_by_value('5')
        too_old = get_books(driver)
        while too_old == 'not too old':
            if next_or_break(driver) == 'no next': break
            too_old = get_books(driver)
    return True


def deduplicate_books(df):
    df.drop_duplicates(inplace=True)
    df.sort_values(by='year', ascending=False, inplace=True)
    df.drop_duplicates(subset='title', inplace=True)
    return df

if __name__ == '__main__':
    term, min_year, min_length, max_length, max_books = get_conditions()

    options = ChromeOptions()
    #options.add_argument('--headless')
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome('../../install/chromedriver', options=options)
    driver.get(f'https://chamo.buw.uw.edu.pl/heading/search?match_1=MUST&field_1=heading&term_1={term}&facet_heading_type=subject&sort=heading')

    links = create_link_set(driver)
    get_books_from_links(links)
    get_books_from_links(Book.authors_to_scrape)
    driver.close()

    interesting_books = [{'title':book.title, 'author':book.author, 'publisher':book.publisher, 'year':book.year, 'pages':book.pages, 'WD_signature':book.WD_signature, 'storage':book.storage} for book in Book.interesting_books]

    reading_list = pd.DataFrame(columns=['title','author', 'WD_signature', 'storage', 'publisher', 'year', 'pages'], data=interesting_books)
    reading_list = deduplicate_books(reading_list)

    output_file = f'../results/{term}_reading_list.tsv'
    reading_list[:min(len(reading_list), max_books)].to_csv(output_file, index=False, sep='\t')
