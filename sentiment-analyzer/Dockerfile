# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- NLTK Data Download ---
# This command runs a mini-script within the Docker build process
# to download the necessary VADER lexicon for sentiment analysis.
RUN python -c "import nltk; nltk.download('vader_lexicon')"

# Copy the rest of the application code
COPY . .

# Command to run the application when the container starts
CMD ["python", "main.py"]