# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source code
# Correct paths to include the backend/ directory
COPY backend/api/ /app/api
COPY backend/db/ /app/db
COPY backend/etl/ /app/etl
COPY backend/data/ /app/data

EXPOSE 5000

# Set environment variables for the database
ENV DB_HOST=db \
    DB_PORT=3306 \
    DB_USER=root \
    DB_PASSWORD=root_password \
    DB_NAME=joy_of_painting

ENTRYPOINT ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "api.app:app"]
