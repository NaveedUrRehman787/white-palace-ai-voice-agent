#!/bin/bash

# White Palace Grill Database Population Script
# This script populates an existing RDS database with schema and seed data
# Designed for AWS RDS - does NOT create databases or users

set -e

# Database configuration - uses environment variables
DB_URL=${DATABASE_URL}

if [ -z "$DB_URL" ]; then
    echo "❌ Error: DATABASE_URL environment variable not set"
    echo "Please run: source .env"
    exit 1
fi

echo "🔧 Populating White Palace Grill database..."
echo "Database URL: $DB_URL"

# Test connection
echo "🔍 Testing database connection..."
psql "$DB_URL" -c "SELECT 1;" > /dev/null
echo "✅ Database connection successful"

# Run schema
echo "📋 Creating database schema..."
psql "$DB_URL" -f database/schema.sql

# Run seed data
echo "🌱 Seeding menu items..."
psql "$DB_URL" -f database/seed_menu_items.sql

# Verify tables were created
echo "🔍 Verifying tables..."
TABLE_COUNT=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo "✅ Created $TABLE_COUNT tables"

# Verify seed data
echo "🔍 Verifying seed data..."
MENU_COUNT=$(psql "$DB_URL" -t -c "SELECT COUNT(*) FROM menu_items;")
echo "✅ Seeded $MENU_COUNT menu items"

echo ""
echo "🎉 Database population complete!"
echo ""
echo "You can now start your application:"
echo "docker-compose up -d"
