# 1. Use an official Python runtime as a parent image
# Using 'slim' for a smaller image size
FROM python:3.10-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the requirements file into the container at /app
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
# --no-cache-dir makes the image smaller
# --upgrade pip ensures we have the latest version
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application's code into the container
COPY . .

# 6. Command to run the application
# This is the command that will be executed when the container starts
CMD ["python", "main.py"]