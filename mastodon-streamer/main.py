import os
import sys
import time
import json
from mastodon import Mastodon, StreamListener
from kafka import KafkaProducer

# --- Configuration ---
# It's better to get credentials from environment variables in a Docker container
API_BASE_URL = os.getenv("MASTODON_API_BASE_URL")
ACCESS_TOKEN = os.getenv("MASTODON_ACCESS_TOKEN")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")

# --- Basic Validation ---
if not all([API_BASE_URL, ACCESS_TOKEN, KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC]):
    print("Error: One or more environment variables are not set.")
    sys.exit(1)
# --- Kafka Producer Setup ---
producer = None
retries = 10
delay = 5

for i in range(retries):
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Successfully connected to Kafka.")
        break  # Exit loop if connection is successful
    except Exception as e:
        print(f"Failed to connect to Kafka: {e}. Retrying in {delay} seconds... ({i+1}/{retries})")
        time.sleep(delay)

if producer is None:
    print("Could not connect to Kafka after several retries. Exiting.")
    sys.exit(1)

# --- Mastodon API Setup ---
try:
    mastodon = Mastodon(
        access_token=ACCESS_TOKEN,
        api_base_url=API_BASE_URL
    )
    print(f"Successfully connected to Mastodon instance at {API_BASE_URL}.")
except Exception as e:
    print(f"Failed to initialize Mastodon client: {e}")
    sys.exit(1)


# --- Define a listener for real-time updates ---
class MyStreamListener(StreamListener):
    def on_update(self, status):
        """Called when a new post (status) is received."""
        # We only care about original posts (not boosts) from non-bot accounts
        if status['reblog'] is None and status['account']['bot'] is False:
            # We will extract only the fields we need
            post_data = {
                'id': status['id'],
                'created_at': status['created_at'].isoformat(),
                'content': status['content'],
                'account': {
                    'id': status['account']['id'],
                    'username': status['account']['username'],
                    'acct': status['account']['acct']
                }
            }
            try:
                # Send the data to the Kafka topic
                producer.send(KAFKA_TOPIC, value=post_data)
                print(f"Sent post {post_data['id']} to Kafka topic '{KAFKA_TOPIC}'")
            except Exception as e:
                print(f"Failed to send post to Kafka: {e}")

    def on_error(self, error):
        """Called when a stream error occurs."""
        print(f"Stream error: {error}", file=sys.stderr)

# --- Start Streaming ---
print("Initializing Mastodon stream...")
listener = MyStreamListener()

try:
    mastodon.stream_public(listener, run_async=False, reconnect_async=True)
except Exception as e:
    print(f"An unexpected error occurred during streaming: {e}", file=sys.stderr)
    sys.exit(1)
