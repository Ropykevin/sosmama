# Use a base image with uWSGI, Nginx, and Flask
FROM tiangolo/uwsgi-nginx-flask:python3.10

# Set working directory inside the container
WORKDIR /app

# Copy requirements file
COPY requirements.txt /tmp/

# Set environment variables
ENV OAUTHLIB_INSECURE_TRANSPORT=0

# Install dependencies
RUN pip install --upgrade pip  # Ensure latest pip
RUN pip install -r /tmp/requirements.txt

# Copy project files into the container
COPY . /app

# Expose port 80 (default for Nginx)
EXPOSE 80

# Set permissions (if needed)
RUN chmod -R 755 /app

# Start the app (default CMD from the base image will run uWSGI and Nginx)
