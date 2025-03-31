FROM tiangolo/uwsgi-nginx-flask:python3.10

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Copy the application code
COPY . .

# Expose the port
EXPOSE 5000

CMD ["python", "run.py"]
