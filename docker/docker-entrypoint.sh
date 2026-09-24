#!/bin/bash
set -e

# If database is not initialized, initialize it
if [ ! -s "/var/lib/postgresql/data/PG_VERSION" ]; then
    echo "Initializing database..."
    # Run initdb as postgres user
    gosu postgres initdb -D /var/lib/postgresql/data --auth=trust
    
    # Copy custom pg_hba.conf
    cp /pg_hba.conf.custom /var/lib/postgresql/data/pg_hba.conf
    
    # Start postgres temporarily to create database and user
    gosu postgres pg_ctl -D /var/lib/postgresql/data -w start
    
    # Create database and user
    gosu postgres psql -v ON_ERROR_STOP=1 --username postgres <<-EOSQL
        CREATE DATABASE globalrisk;
        ALTER USER postgres PASSWORD 'postgres';
EOSQL
    
    # Enable pgvector extension
    gosu postgres psql -v ON_ERROR_STOP=1 --username postgres -d globalrisk <<-EOSQL
        CREATE EXTENSION IF NOT EXISTS vector;
EOSQL
    
    # Stop temporary server
    gosu postgres pg_ctl -D /var/lib/postgresql/data -w stop
fi

# Ensure pg_hba.conf is correct
cp /pg_hba.conf.custom /var/lib/postgresql/data/pg_hba.conf

# Start postgres as postgres user
exec gosu postgres postgres