import os
import string
import re
import pandas as pd

import spacy
from spacy_langdetect import LanguageDetector
import en_core_web_lg
nlp = en_core_web_lg.load()
nlp.add_pipe(LanguageDetector(), name='language_detector', last=True)
import pl_core_news_lg
nlp_pl = pl_core_news_lg.load()

from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium .webdriver import ChromeOptions

from ipykernel import kernelapp as app
from tqdm import tqdm



def get_conditions():
    term = input('What would you like to read about?\n')
    term = term.replace(' ', '+')
    min_year = int(input('What is the oldest book you are interested in?\n'))
    min_length = 100
    max_length = 700
    return term, min_year, min_length, max_length

def next_or_break(driver):
    try:
        next_button = driver.find_element_by_link_text('Następne>')
        next_button.click()
        return True
    except: return 'no next'



class Book:
    interesting_books = set()
    all_authors = set()
    authors_to_scrape = set()

    def __init__(self, source):
        self.title = ''
        self.author = ''
        self.publisher = ''
        self.year = 0
        self.pages = 0
        self.WD_signature = ''
        self.storage = ''
        self.source = source

    def get_book_attributes(self, record):
        title = record.find_element_by_class_name('title').text
        self.title = re.sub(r' / .+', '', title)

        try: self.author = record.find_element_by_class_name('author').text
        except: pass

        if 'BUW Magazyn' in record.text: self.storage = 'magazyn'

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
                        if publisher:
                            self.publisher = publisher.group(1)
                            self.year = int(publisher.group(2))
            elif 'Opis fiz.' in info.text:
                pages = info.find_element_by_tag_name('span').text
                pages = re.sub(r'\[.+?\]', '', pages)
                if re.search(r'\d+', pages):
                    self.pages = int(re.search(r'\d+', pages).group(0))

    def check_quality(self):
        if self.year >= min_year and self.pages >= min_length and self.pages <= max_length:
            Book.interesting_books.add(self)

    def add_to_authors(self, record):
        if self in Book.interesting_books and len(self.author) > 0:
            if self.author in Book.all_authors:
                author = record.find_element_by_class_name('author')
                Book.authors_to_scrape.add(author.get_attribute('href'))
            else: Book.all_authors.add(self.author)



def get_books(driver, source, expand_set):
    records = driver.find_element_by_class_name('records').find_elements_by_tag_name('li')
    for record in records:
        too_old = 'not too old'

        if ('BUW Wolny Dostęp' in record.text or 'BUW Magazyn' in record.text) and 'Adres wyd.' in record.text and 'Opis fiz.' in record.text:
            book = Book(source)
            book.get_book_attributes(record)
            book.check_quality()
            if expand_set: book.add_to_authors(record)
            if book.year < min_year and book.year > 0:
                too_old = 'too old'
                break
    return too_old

def create_link_set(driver):
    links = set()
    while True:
        tags_from_page = driver.find_element_by_tag_name('tbody').find_elements_by_tag_name('a')
        for tag in tags_from_page:
            try: links.add(tag.get_attribute('href'))
            except: pass
        if next_or_break(driver) == 'no next': break
    return links

def get_books_from_links(link_set, source, driver, expand_set=True):
    for link in tqdm(link_set, desc=f'Scraping {len(link_set)} links for {source}'):
        driver.get(link)
        select = Select(driver.find_element_by_id('search_sort'))
        select.select_by_value('5')
        too_old = get_books(driver, source, expand_set)
        while too_old == 'not too old':
            if next_or_break(driver) == 'no next': break
            too_old = get_books(driver, source, expand_set)
    return True

def deduplicate_books(df):
    df.drop_duplicates(inplace=True)
    df.sort_values(by='year', ascending=False, inplace=True)
    return df.drop_duplicates(subset='title')


def scrape_tags_and_authors(term):
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome('chromedriver', options=options)
    driver.get(f'https://chamo.buw.uw.edu.pl/heading/search?match_1=MUST&field_1=heading&term_1={term}&facet_heading_type=subject&sort=heading')

    print('Creating initial link set')
    links = create_link_set(driver)
    get_books_from_links(links, 'tags', driver)
    len_from_tags = len(Book.interesting_books)
    get_books_from_links(Book.authors_to_scrape, 'authors', driver, False)
    driver.close()
    print(f'Scraped {len_from_tags} books from tags and {len(Book.interesting_books)-len_from_tags} books from authors.')

    interesting_books = [{'title':book.title, 'author':book.author, 'publisher':book.publisher, 'year':book.year, 'pages':book.pages, 'WD_signature':book.WD_signature, 'storage':book.storage, 'source':book.source} for book in Book.interesting_books]
    reading_df = pd.DataFrame(columns=['year', 'source', 'title','author', 'WD_signature', 'storage', 'publisher', 'pages'], data=interesting_books)
    reading_df = deduplicate_books(reading_df)
    print(f'Removing duplicates left {len(reading_df)} books.')
    return reading_df


def detect_language(df):
    language = []
    for doc in tqdm(nlp.pipe(df['title'].values, batch_size=1000), desc='Detecting language', total=len(df)):
        if doc.is_parsed:
            if doc._.language['language'] == 'en': language.append('en')
            else: language.append('pl')
        else: language.append('')

    df['language'] = language
    return df


def preprocess(input_df):
    preprocessed_df = pd.DataFrame()

    for lang in ['pl', 'en']:
        if lang == 'en': model = nlp
        elif lang == 'pl': model = nlp_pl

        df = input_df[input_df['language'] == lang]
        stopwords = model.Defaults.stop_words
        preprocessed = []
        for doc in tqdm(model.pipe(df['title'].values, batch_size=200), desc=f'Preprocessing {lang}', total=len(df)):
            if doc.is_parsed:
                tokens = [token.lemma_.lower() for token in doc if (token.text.lower() not in stopwords and token.text not in string.punctuation)]
                if len(tokens) > 0: preprocessed.append(tokens)
                else: preprocessed.append('preprocessing_fail')
            else: preprocessed.append('preprocessing_fail')

        df['tokens'] = preprocessed
        df = df[df['tokens'] != 'preprocessing_fail']
        preprocessed_df = preprocessed_df.append(df)
    return preprocessed_df


def calculate_similarity(preprocessed_df, tag_df):
    cat_sim = pd.DataFrame()
    for lang in ['pl', 'en']:
        df = preprocessed_df[preprocessed_df['language'] == lang]
        semantics = ' '.join(tag[tag['language'] == lang].tokens.str.join(' '))
        if lang == 'en': model = nlp
        elif lang == 'pl': model = nlp_pl
        semantics = model(semantics)

        similarity = []
        for doc in tqdm(model.pipe(df['title'].values, batch_size=200), desc=f'Calculating semantic similarity for {lang}', total=len(df)):
            if doc.is_parsed: similarity.append(semantics.similarity(doc))
            else: preprocessed.append('similarity_fail')
        df['similarity'] = similarity
        cat_sim = cat_sim.append(df)
    cat_sim.drop(cat_sim[cat_sim['similarity'] < 0.7].index, inplace=True)
    cat_sim.sort_values(by='similarity', inplace=True, ascending=False)
    cat_sim['source'] = 'similarity'
    cat_sim.drop(columns={'language', 'tokens'}, inplace=True)
    return cat_sim


if __name__ == '__main__':
    term, min_year, min_length, max_length = get_conditions()
    reading_list = scrape_tags_and_authors(term)
    cat = pd.read_json('/content/Library_search_for_topic/Library_catalogue.json')

    tag = detect_language(reading_list[reading_list['source'] == 'tags'])
    tag = preprocess(tag)
    tag['tokens'] = tag['tokens'].apply(lambda x: x+[term.replace('+', ' ')])
    for index, row in tag.iterrows():
        cat.drop(cat[cat['title'] == row['title']].index, inplace=True)

    cat_sim = calculate_similarity(cat, tag)
    reading_list = reading_list.append(cat_sim, ignore_index=True)
    reading_list.to_csv(f"{term.replace('+', '_')}_Bibliography.tsv", index=False, sep='\t')
    print(f'Found {len(reading_list)} books.')
