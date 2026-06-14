#!/bin/bash

# Build script for Render deployment
# This script is used by Render to build the Django application

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate
