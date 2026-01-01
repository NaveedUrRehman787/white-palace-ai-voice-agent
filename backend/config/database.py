"""
Database configuration and connection management
PostgreSQL connection pool for White Palace Grill
"""

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database connection parameters
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'white_palace_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

# Create connection pool
try:
    connection_pool = SimpleConnectionPool(
        minconn=1,
        maxconn=20,
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    logger.info('✅ Database connection pool created')
except Exception as e:
    logger.error(f'❌ Failed to create connection pool: {str(e)}')
    connection_pool = None

def init_db():
    """Initialize database connection and test it"""
    try:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        cursor.execute('SELECT NOW()')
        result = cursor.fetchone()
        cursor.close()
        connection_pool.putconn(conn)
        logger.info(f'✅ Database connection successful at {result}')
        return True
    except Exception as e:
        logger.error(f'❌ Database connection failed: {str(e)}')
        raise

@contextmanager
def get_db_cursor(dict_cursor=False):
    """
    Context manager for database cursor
    Usage:
        with get_db_cursor() as cursor:
            cursor.execute(...)
    """
    conn = connection_pool.getconn()
    try:
        cursor_class = RealDictCursor if dict_cursor else psycopg2.cursor
        cursor = conn.cursor(cursor_factory=cursor_class)
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f'Database error: {str(e)}')
        raise
    finally:
        cursor.close()
        connection_pool.putconn(conn)

def execute_query(sql, params=None, fetch_one=False, fetch_all=True):
    """
    Execute a SQL query and return results
    
    Args:
        sql: SQL query string
        params: Query parameters (tuple or dict)
        fetch_one: Return single row
        fetch_all: Return all rows
    
    Returns:
        Query result(s)
    """
    try:
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                return cursor.rowcount
    except Exception as e:
        logger.error(f'Query execution error: {str(e)}')
        raise

def close_db():
    """Close all connections in the pool"""
    if connection_pool:
        connection_pool.closeall()
        logger.info('Database pool closed')

# Legacy function for compatibility
def get_db():
    """Get database connection"""
    return connection_pool.getconn()

