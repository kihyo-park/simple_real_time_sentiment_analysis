import os
import sys
import json
import time
import psycopg2
from kafka import KafkaConsumer
from nltk.sentiment import SentimentIntensityAnalyzer
from bs4 import BeautifulSoup

# --- Environment Variables ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# --- Database Connection with Retry ---
db_conn = None
retries = 10
delay = 5
for i in range(retries):
    try:
        db_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        print("Successfully connected to PostgreSQL.")
        break
    except psycopg2.OperationalError as e:
        print(f"Failed to connect to PostgreSQL: {e}. Retrying in {delay} seconds... ({i+1}/{retries})")
        time.sleep(delay)

if db_conn is None:
    print("Could not connect to PostgreSQL after several retries. Exiting.")
    sys.exit(1)

# --- Create Table If It Doesn't Exist ---
def create_table():
    with db_conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_results (
                id SERIAL PRIMARY KEY,
                post_id BIGINT UNIQUE NOT NULL,
                content TEXT,
                sentiment VARCHAR(10),
                compound_score FLOAT,
                positive_score FLOAT,
                neutral_score FLOAT,
                negative_score FLOAT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db_conn.commit()
        print("Table 'sentiment_results' is ready.")

create_table()

# --- Initialize Sentiment Analyzer ---
sia = SentimentIntensityAnalyzer()
print("Sentiment analyzer initialized.")

# --- Kafka Consumer Setup ---
try:
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        group_id='sentiment-analyzers'
    )
    print("Successfully connected to Kafka.")
except Exception as e:
    print(f"Could not connect to Kafka: {e}")
    sys.exit(1)

# --- Process Messages ---
print(f"Listening for messages on topic '{KAFKA_TOPIC}'...")
for message in consumer:
    post_data = message.value
    post_id = post_data.get('id')
    html_content = post_data.get('content', '')

    soup = BeautifulSoup(html_content, "html.parser")
    cleaned_text = soup.get_text().strip()

    if cleaned_text:
        scores = sia.polarity_scores(cleaned_text)
        compound_score = scores['compound']

        if compound_score >= 0.05: sentiment = "Positive"
        elif compound_score <= -0.05: sentiment = "Negative"
        else: sentiment = "Neutral"

        print(f"ANALYZED Post {post_id}: {sentiment} ({compound_score})")

        # Insert into database
        try:
            with db_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sentiment_results (post_id, content, sentiment, compound_score, positive_score, neutral_score, negative_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (post_id) DO NOTHING;
                """, (post_id, cleaned_text, sentiment, scores['compound'], scores['pos'], scores['neu'], scores['neg']))
                db_conn.commit()
        except Exception as e:
            print(f"Database insert failed for post {post_id}: {e}")
            db_conn.rollback()