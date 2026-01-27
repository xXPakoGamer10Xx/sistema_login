#!/bin/bash
set -e

# Initialize configuration and database tables
echo "Running system initialization..."
python init_config.py

# specific migration scripts if needed (optional, safer to rely on init_config for now)
# python migrate_add_grupos.py

echo "Starting Gunicorn server on port 5001..."
# using 4 workers, customize as needed
exec gunicorn --bind 0.0.0.0:5001 --timeout 600 app:app
