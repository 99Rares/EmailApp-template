# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app

COPY requirements.txt .
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN addgroup --system app && adduser --system --ingroup app app && mkdir -p /app/data && chown -R app:app /app
USER app

# Expose port 5000 for the Flask app
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=production

# Run the Flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]

