# Library search for topic

An improved search engine for the University of Warsaw Library (BUW). <b>You don't need any knowledge of python or programming to run it!</b>

<h2>How to run</h2>
Open Library_search_for_topic.ipynb on Google Colab and run the single cell. This will install all the required modules in the required versions, clone this repo to the session storage, download large spaCy models for English and Polish, and run the search engine. The output is a single TSV file with the search results.

<h2>How the engine works</h2>
<ol>
<li>After the initial installation (about 7 minutes on Google Colab), <b>the engine will ask you 2 questions</b>: (1) What would you like to read about? and (2) What is the oldest book you're interested in? Answer the first question with a topic name or a partial topic name (good topic examples: python, object-oriented, Asperger's syndrome, etc.). Answer the second question with a year.</li>
<li>The engine will then scrape the Library catalogue with Selenium, first performing an automated topic search directly on the catalogue, and then further scraping books by authors that appeared at least twice in the initial scrape results. The former will have 'tags' in the 'source' column of the output, while the latter - 'authors'.</li>
<li>Now, the engine will access a scraped version of part of the entire catalogue, preprocess it, and - for each book - calculate its semantic similarity to the initial search results (source == 'tags'). The results will be ordered by similarity and appended to the initial results.</li>
<li>Finally, <b>the engine will save the result as a TSV file</b> directly in the session storage (remember to download it!). The TSV will have the following columns: source, title, author, WD_signature (the shelf address for open stacks), storage ('magazyn' if the book is in the main storage, empty otherwise), publisher, year (of publication), pages (length of the book).</li>
  </ol>
