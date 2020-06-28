import pandas as pd
import spacy
import string

cat = pd.read_csv('Library_catalogue.tsv', sep='\t')
preprocessed_cat = pd.DataFrame()

for lang in ['en', 'pl']:
    print(f'Preprocessing {lang}')
    if lang == 'en':
        nlp = spacy.load('en_core_web_sm')
    elif lang == 'pl':
        nlp = spacy.load('pl_core_news_sm')

    df = cat[cat['language'] == lang]
    stopwords = nlp.Defaults.stop_words

    preprocessed = []
    for index, doc in enumerate(nlp.pipe(df['title'].values, batch_size=200)):
        if index % 100 == 0:
            print('Progress:', index/len(df))
        if doc.is_parsed:
            tokens = [token.lemma_.lower() for token in doc if (token.text.lower() not in stopwords and token.text not in string.punctuation)]
            if len(tokens) > 0:
                preprocessed.append(tokens)
            else:
                preprocessed.append('preprocessing_fail')
        else:
            print('Preprocessing failed')
            preprocessed.append('preprocessing_fail')

    df['tokens'] = preprocessed
    df = df[df['tokens'] != 'preprocessing_fail']
    preprocessed_cat = preprocessed_cat.append(df)

preprocessed_cat.to_csv('Preprocessed_catalogue.tsv', index=False, sep='\t')
