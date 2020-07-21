import pandas as pd
import spacy
from spacy_langdetect import LanguageDetector
import os
import random

from get_books_by_category import deduplicate_books


def detect_language(df):
    nlp = spacy.load('en_core_web_sm')
    nlp.add_pipe(LanguageDetector(), name='language_detector', last=True)

    language = []
    for index, doc in enumerate(nlp.pipe(df['title'].values, batch_size=1000)):
        if index % 100 == 0:
            print('Progress:', index/len(df['title']))
        if doc.is_parsed:
            if doc._.language['language'] == 'en':
                language.append('en')
            else:
                language.append('pl')
        else:
            language.append('')

    df['language'] = language
    return df


if __name__ == '__main__':
    cat = pd.DataFrame()
    data_path = '../data/'
    for file in os.listdir(data_path):
        if file.endswith('.tsv'):
            c = pd.read_csv(data_path + file, sep='\t')
            cat = cat.append(c, ignore_index=True)

    cat = deduplicate_books(cat)
    cat = detect_language(cat)

    for language in cat.language.unique():
        sample = random.sample(list(cat[cat['language'] == language].index), 20)
        print(f'{language} sample')
        for row in cat[cat.index.isin(sample)].itertuples():
            print(row.title)

    cat.to_csv('../data/Library_catalogue.tsv', sep='\t', index=False)
