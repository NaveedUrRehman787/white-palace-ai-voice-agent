#!/bin/bash

# White Palace Grill Database Initialization Script
# This script sets up the PostgreSQL database with proper permissions

set -e

# Database configuration
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-white_palace_db}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-password}
WP_USER=${WP_USER:-white_palace_user}
WP_PASSWORD=${WP_PASSWORD:-wp_password_2024}

echo "🔧 Setting up White Palace Grill database..."

# Create database if it doesn't exist
echo "📦 Creating database..."
createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME 2>/dev/null || echo "Database already exists"

# Create application user if it doesn't exist
echo "👤 Creating application user..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d postgres -c "DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$WP_USER') THEN
      CREATE USER $WP_USER WITH PASSWORD '$WP_PASSWORD';
   END IF;
END
\$\$;"

# Grant permissions to the application user
echo "🔑 Granting permissions..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $WP_USER;"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $WP_USER;"

# Run schema
echo "📋 Running schema..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f schema.sql

# Grant additional permissions that might be needed
echo "🔐 Granting additional permissions..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
-- Grant permissions on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $WP_USER;

-- Grant permissions on all sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $WP_USER;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO $WP_USER;

-- Make sure the user can create and modify tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $WP_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $WP_USER;
"

# Run seed data
echo "🌱 Seeding data..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f seed_menu_items.sql

echo "✅ Database setup complete!"
echo ""
echo "Database: $DB_NAME"
echo "User: $WP_USER"
echo "Host: $DB_HOST:$DB_PORT"
echo ""
echo "You can now run the application with:"
echo "export DB_USER=$WP_USER"
echo "export DB_PASSWORD=$WP_PASSWORD"
echo "python backend/app.py"
