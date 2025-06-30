import os
import json
import psycopg2
from flask import Flask, jsonify, render_template

# --- App Setup ---
app = Flask(__name__)

# --- Database Connection ---
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    return conn

# --- API Route ---
@app.route('/api/data')
def get_data():
    conn = get_db_connection()
    cur = conn.cursor()

    # Query for sentiment counts
    cur.execute("SELECT sentiment, COUNT(*) FROM sentiment_results GROUP BY sentiment;")
    sentiment_counts = dict(cur.fetchall())

    # Query for recent posts
    cur.execute("SELECT content, sentiment, compound_score FROM sentiment_results ORDER BY created_at DESC LIMIT 20;")
    recent_posts_raw = cur.fetchall()
    recent_posts = [{"content": row[0], "sentiment": row[1], "compound_score": row[2]} for row in recent_posts_raw]
    
    cur.close()
    conn.close()

    # Ensure all sentiment categories are present
    for sentiment in ['Positive', 'Negative', 'Neutral']:
        if sentiment not in sentiment_counts:
            sentiment_counts[sentiment] = 0

    response_data = {
        "sentiment_counts": sentiment_counts,
        "recent_posts": recent_posts
    }
    return jsonify(response_data)

# --- Main Page Route ---
@app.route('/')
def index():
    # render_template will look for the file in the 'templates' folder
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)