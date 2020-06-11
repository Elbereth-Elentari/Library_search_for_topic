from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import pandas as pd
import re

driver = webdriver.Chrome()
driver.get('https://chamo.buw.uw.edu.pl/heading/search?match_1=MUST&field_1=heading&term_1=python&facet_heading_type=subject&sort=heading')

def next_or_break(driver):
    try:
        next_button = driver.find_element_by_link_text('Następne>')
        next_button.click()
        return True
    except NoSuchElementException:
        return 'no next'

def get_links(elements_with_links, list_of_links):
    for element in elements_with_links:
        try:
            link = element.get_attribute('href')
            if link not in list_of_links:
                list_of_links.append(link)
        except StaleElementReferenceException:
            pass
    return list_of_links

links = []
while True:
    tags_from_page = driver.find_element_by_tag_name('tbody').find_elements_by_tag_name('a')
    links = get_links(tags_from_page, links)
    if next_or_break(driver) == 'no next': break

def get_books(driver, list_of_books):
    books_on_page = driver.find_element_by_class_name('records').find_elements_by_class_name('title')
    return get_links(books_on_page, list_of_books)

books = []
for link_to_tag in links:
    driver.get(link_to_tag)
    books = get_books(driver, books)
    while True:
        if next_or_break(driver) == 'no next': break
        books = get_books(driver, books)

reading_list = pd.DataFrame(columns=['title', 'English', 'WD_signature', 'storage', 'author', 'publisher', 'year', 'pages', 'tags', 'link'])
for link_to_book in books:
    driver.get(link_to_book)
    page_text = driver.find_element_by_id('main').text
    if 'BUW Wolny Dostęp' in page_text or 'BUW Magazyn' in page_text:
        book = {}
        book['link'] = link_to_book
        if 'BUW Magazyn' in page_text:
            book['storage'] = 'magazyn'

        title = driver.find_element_by_class_name('title').text
        book['title'] = re.sub(r' / .+', '', title)

        try:
            book['author'] = driver.find_element_by_class_name('author').text
        except NoSuchElementException:
            book['author'] = ''

        rows = driver.find_element_by_class_name('itemFields').find_elements_by_tag_name('tr')

        for row in rows:
            if 'Tytuł ujednolicony' in row.text:
                English = row.find_element_by_tag_name('a').text
                book['English'] = English.replace(' (pol.)', '')
            elif 'Klasyfikacja WD' in row.text:
                book['WD_signature'] = row.find_element_by_tag_name('a').text
            elif 'Adres wyd.' in row.text:
                publisher = row.find_element_by_tag_name('span').text
                publisher = re.search(r'.+ : (.+),.*(\d{4})', publisher)
                book['publisher'] = publisher.group(1)
                book['year'] = publisher.group(2)
            elif 'Opis fiz.' in row.text:
                pages = row.find_element_by_tag_name('span').text
                pages = re.sub(r'\[.+?\]', '', pages)
                book['pages'] = re.search(r'\d+', pages).group(0)
            elif 'Temat polski' in row.text:
                tags_container = row.find_elements_by_tag_name('a')
                tags = []
                for tag in tags_container:
                    tag = tag.get_attribute('href')
                    tags.append(tag)
                book['tags'] = tags
        reading_list = reading_list.append(book, ignore_index=True)

driver.close()
reading_list.to_excel('reading_list.xlsx', index=False)
