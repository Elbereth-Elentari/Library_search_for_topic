import pandas as pd
import spacy
from spacy_langdetect import LanguageDetector
import os
import random

from get_books_by_category import deduplicate_books


cat = pd.DataFrame()
for file in os.listdir('./'):
    if file.endswith('.tsv'):
        c = pd.read_csv(file, sep='\t')
        cat = cat.append(c, ignore_index=True)

cat = deduplicate_books(cat)

nlp = spacy.load('en_core_web_sm')
nlp.add_pipe(LanguageDetector(), name='language_detector', last=True)

language = []
for index, doc in enumerate(nlp.pipe(cat['title'].values, batch_size=1000)):
    if index % 100 == 0:
        print('Progress:', index/len(cat['title']))
    if doc.is_parsed:
        if doc._.language['language'] == 'en':
            language.append('en')
        else:
            language.append('pl')
    else:
        language.append('')

cat['language'] = language

for language in cat.language.unique():
    sample = random.sample(list(cat[cat['language'] == language].index), 20)
    print(f'{language} sample')
    for row in cat[cat.index.isin(sample)].itertuples():
        print(row.title)

cat.to_csv('Library_catalogue.tsv', sep='\t', index=False)
