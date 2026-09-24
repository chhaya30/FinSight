#!/bin/bash
# Custom entrypoint that fixes pg_hba.conf for host trust authentication

# Start postgres in background with the standard entrypoint
/usr/local/bin/docker-entrypoint.sh postgres &

# Wait for postgres to be ready
until pg_isready -U postgres; do
  sleep 1
done

# Fix pg_hba.conf to allow trust auth for all connections (dev only)
# Change the catch-all scram-sha-256 to trust
sed -i "s/host all all all scram-sha-256/host all all all trust/" /var/lib/postgresql/data/pg_hba.conf

# Also ensure the password is set correctly
psql -U postgres -c "ALTER USER postgres PASSWORD 'postgres';"

# Reload postgres configuration
psql -U postgres -c "SELECT pg_reload_conf();"

# Keep the container running
wait