FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The command to run the Flask development server
CMD ["flask", "--app", "main.py", "run", "--host=0.0.0.0"]