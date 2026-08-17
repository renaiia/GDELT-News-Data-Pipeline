from newspaper import Article, ArticleException
from zipfile import ZipFile
from io import BytesIO
import pandas as pd
import requests
import spacy
import sqlite3

nlp = spacy.load("en_core_web_sm")
 
# scraping layer
def scraper():
    """DataFrame of the latest GDELT data.
Returns:
    pd.DataFrame: Latest news articles from the most recent GDELT update (typically updated every 15 minutes).
"""
    file_url = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
    pointer_lines = requests.get(file_url).text.splitlines()
    zip_resp = requests.get(pointer_lines[0].split()[2]).content
    zip_data = BytesIO(zip_resp)

    with ZipFile(zip_data) as zf:
        csv_file = zf.namelist()[0]
        with zf.open(csv_file) as f:
            df = pd.read_csv(f, sep="\t", header=None)
    
    return df

# transformation layer
def transform(url, nlp):
    """Extracts article content and metadata and returns it as a dictionary.

Args:
    url(str): URL of the news article to process.
    nlp(Language): spaCy language pipeline used to analyze the article summary.

Returns:
    dict: title(str), publish_date(datetime or None), authors(list), article(str), summary(str), url(str), keywords(list), entities[text, start_char, end_char, label]
"""
    article = Article(url)
    article.download()
    article.parse()   
    article.nlp()   
        
    art_sum = nlp(article.summary)
    
    temp_dict = {}
    temp_sum_ent = []

    for ent in art_sum.ents:
        temp_sum_ent.append([ent.text, ent.start_char, ent.end_char, ent.label_])

    temp_dict.update({"title": article.title})
    temp_dict.update({"publish_date": article.publish_date})
    temp_dict.update({"authors": article.authors})
    temp_dict.update({"article": article.text})
    temp_dict.update({"summary": article.summary})
    temp_dict.update({"url": url})
    temp_dict.update({"keywords": article.keywords})
    temp_dict.update({"entities":temp_sum_ent})

    return temp_dict

# database layer 
def change_database(cursor, connection, action, values = None):
    """Creates or connects to a db. file. And executes actions according to the provided sql. 
     
Args:
    cursor: SQLite cursor used to execute the SQL statement.
    connection: SQLite database connection used to commit changes.
    action (str): SQL statement to execute.
    values: Optional values supplied to a parameterized SQL statement.

Returns:
    int: The ID of the last inserted row, when available
    """
    try:
        if values == None:   # for create table
            result = cursor.execute(action).fetchall()       
        else: 
            result = cursor.execute(action, values)   # for select/injecting information into database
            connection.commit()
            return result.lastrowid  

        connection.commit()
  
    except Exception as error:
        print (error)

def insert_data (cursor, db_connection, article, table, table_column, value=None):
    """Inserts data into SQLite database.
Args:
    cursor: SQLite cursor used to execute the insertion.
    db_connection: SQLite database connection.
    article (dict): Dictionary containing the processed article data.
    table (str): Name of the database table receiving the data.
    table_column (tuple): Database columns into which the values are inserted.
    value: Optional value or list of values to insert directly.

Returns:
    int: The ID of the inserted row.
"""
    question_mark = ((len(table_column)-1)*"?, ")+"?"   # creates SQL placeholders for insert data
    temp_val = []

    if value is not None:   #use provided values
        if type(value) == tuple:
            temp_val = value
        else: 
            temp_val.append(value)
    else:  
        for column in table_column: 
            if column in list(article.keys()):   # Checks if row is a key and saves the corresponding information
                temp_val.append(article[column]) 

    temp_id = change_database (cursor, 
                        db_connection, 
                        f"INSERT INTO {table} ({", ".join(table_column)}) VALUES ({question_mark})", 
                        temp_val
                        )
    return temp_id

def insert_list_data (cursor, db_connection, article, table, table_column):
    """
Args:
    cursor: SQLite cursor used to execute the insertions.
    db_connection: SQLite database connection.
    article (dict): Dictionary containing the article data and associated list values.
    table (str): Name of the database table receiving the list values.
    table_column (tuple): Database columns into which the values are inserted.

Returns:
    list: IDs of the rows inserted into the database.
""" 
    temp_id = []

    for name in article[table]:
        author_id = insert_data (cursor, db_connection, article, table, table_column, name)   
        temp_id.append(author_id)

    return temp_id
    
# Pipeline layer
def run_pipeline(nlp):
    """Runs the scraping and transformation stages of the application.

Args:
    nlp: spaCy language pipeline passed to the transformation stage.

Returns:
    list: A list of dictionaries containing the processed article information.
"""
    visited_urls = set()
    sum_ent = [] 
    fail = 0

    df = scraper()

    for url in df[60][:3]:   # Currently limited to 3 articles while developing/testing.
        if url not in visited_urls:
            visited_urls.add(url)
            try:
                sum_ent.append(transform(url,nlp))
            except ArticleException:
                fail +=1
            except requests.exceptions.ConnectionError: 
                fail +=1
            except requests.exceptions.Timeout: 
                fail +=1
            except requests.exceptions.TooManyRedirects: 
                fail +=1
    print (fail)
    
    return sum_ent

def run_db_pipeline(values, create_tables=False):
    """Runs the database stage of the pipeline.
Args:
    values (list): List of dictionaries containing processed article information.
    create_tables (bool): Determines whether the database tables should be created before inserting data.

Returns:
    None.
"""
    db_connection = sqlite3.connect("Latest GDELT articles.db")
    cursor = db_connection.cursor()

    if create_tables == True:
        change_database(cursor, db_connection, """CREATE TABLE IF NOT EXISTS articles (
                    article_id INTEGER PRIMARY KEY,
                    title Text, 
                    url TEXT UNIQUE,
                    publish_date TEXT,
                    article TEXT,
                    summary TEXT
                )""")

        change_database(cursor, db_connection, """CREATE TABLE IF NOT EXISTS authors (
                    author_id INTEGER PRIMARY KEY,
                    name TEXT
                )""")

        change_database(cursor, db_connection, """CREATE TABLE IF NOT EXISTS keywords (
                    keyword_id TEXT PRIMARY KEY
                )""")

        change_database(cursor, db_connection, """CREATE TABLE IF NOT EXISTS entities (
                    entity TEXT Primary KEY,
                    label TEXT
                )""")

        change_database(cursor, db_connection, """CREATE TABLE IF NOT EXISTS articlesAuthors (
                    article_id INTEGER,
                    author_id INTEGER,
                    FOREIGN KEY (article_id) REFERENCES articles(article_id),
                    FOREIGN KEY (author_id) REFERENCES authors(author_id)
                )""")

        change_database(cursor, db_connection, """CREATE TABLE IF NOT EXISTS articlesKeyword (
                    article_id TEXT,
                    keyword TEXT,
                    FOREIGN KEY (article_id) REFERENCES articles(article_id),
                    FOREIGN KEY (keyword) REFERENCES keywords(keyword)
                )""")

        change_database(cursor, db_connection, """CREATE TABLE IF NOT EXISTS articlesEntities (
                    article_id TEXT,
                    entity TEXT,
                    FOREIGN KEY (article_id) REFERENCES articles(article_id),
                    FOREIGN KEY (entity) REFERENCES entities(entity)
                )""")

    for article in values:
        article_id = insert_data (cursor, db_connection, article, "articles", ("title","publish_date","article","summary","url"))
        author_id = insert_list_data (cursor, db_connection, article, "authors", ("name",))

        for i in author_id:
            insert_data (cursor, db_connection, article, "articlesAuthors",("article_id", "author_id"),(article_id, i))

    # insert_data (cursor, db_connection, values, "keywords", ("keyword_id"))
    # insert_data (cursor, db_connection, values, "entities", ("entity","label"))
              
    db_connection.close()

def run(data = False, change = False, query = False):
    """Controls which stage of the application pipeline is executed based on the supplied options.
Args:
    data (bool): Determines whether the scraping, transformation, and database insertion pipeline is executed.
    change (bool): Reserved for database modification functionality.
    query (bool): Reserved for database querying functionality.

Returns:
    None.
"""
    if data == True: 
        article_inf = run_pipeline(nlp)
        run_db_pipeline(article_inf, True)
    if query == True: 
        None

run (data=True)