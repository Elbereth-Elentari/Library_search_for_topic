import pandas as pd
import spacy
from preprocessing import preprocess


prep = pd.read_csv('Preprocessed_catalogue.tsv', sep='\t')
term = 'object-oriented'
tag = preprocess(f'{term}_reading_list.tsv')
tag_en = tag[tag['language'] == 'en']
tag_en['tokens'] = tag_en['tokens'].apply(lambda x: x+[term])


en = prep[prep['language'] == 'en']

for index, row in tag_en.iterrows():
    en.drop(en[en['title'] == row['title']].index, inplace=True)

nlp = spacy.load('en_core_web_sm')
topic = ' '.join([' '.join(tokens) for tokens in tag_en['tokens']])
topic = nlp(topic)

similarity = []
for index, doc in enumerate(nlp.pipe(en['title'].values, batch_size=200)):
    if index % 100 == 0:
        print('Progress:', index/len(en))
    if doc.is_parsed:
        similarity.append(topic.similarity(doc))
    else:
        print('Similarity failed')
        preprocessed.append('similarity_fail')

en['similarity'] = similarity
en.sort_values(by='similarity', inplace=True, ascending=False)

for row in en[:5].itertuples():
    print(row.title, row.similarity)
