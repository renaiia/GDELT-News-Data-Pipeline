# GDELT News Data Pipeline

## Work in progress

A Python project for collecting recent news data from GDELT, extracting article content and metadata, processing article summaries with NLP, and storing the processed data in an SQLite database.

The project is being developed incrementally, with the goal of building a complete data pipeline from data collection and processing to structured database storage and querying.

## Current functionality

* Retrieves the latest GDELT data
* Extracts article URLs
* Downloads and parses articles using newspaper3k
* Extracts titles, publication dates, authors, article text, summaries and keywords
* Processes article summaries using spaCy
* Extracts named entities
* Stores processed articles and authors in SQLite
* Uses relational tables to connect articles and authors
* Separates the application into scraping, transformation, database and pipeline stages

## Planned work

* Complete keyword and entity database relationships
* Add and expand database querying functionality
* Improve duplicate handling
* Improve error handling and logging
* Expand testing
* Refine the pipeline and database structure

## Technologies

* Python
* Pandas
* Requests
* newspaper3k
* spaCy
* SQLite
* SQL

## Installation

Install the required Python packages:
- pip install -r requirements.txt

The spaCy English language model is also required:
- python -m spacy download en_core_web_sm

## Development status

The project is currently under active development.

The scraping, article processing, and initial database storage functionality are implemented. Keyword and entity database relationships, database querying, and further testing are still being developed.

The pipeline is currently limited to a small number of articles during development and testing.
