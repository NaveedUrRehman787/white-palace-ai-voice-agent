"""
Menu API Routes
GET /api/menu - All menu items
GET /api/menu/<id> - Single item
GET /api/menu/category/<category> - Items by category
GET /api/menu/search?q=query - Search menu items
"""

from flask import Blueprint, jsonify, request
from config.database import execute_query, get_db_cursor
from config.constants import HTTP_STATUS, ERROR_MESSAGES, SUCCESS_MESSAGES
from config.restaurant_config import RESTAURANT_CONFIG
from middleware.error_handler import handle_exceptions, ValidationError
import logging

logger = logging.getLogger(__name__)

# Create blueprint
menu_bp = Blueprint('menu', __name__)

# ============================================
# GET ALL MENU ITEMS
# ============================================
@menu_bp.route('', methods=['GET'])
@handle_exceptions
def get_all_menu_items():
    """
    Get all menu items with optional pagination
    
    Query params:
        - category: Filter by category
        - available: Filter by availability (true/false)
        - limit: Items per page (default: 50)
        - offset: Pagination offset (default: 0)
    
    Returns:
        JSON array of menu items
    """
    try:
        # Get query parameters
        category = request.args.get('category', '')
        available = request.args.get('available', '')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Build query
        sql = 'SELECT * FROM menu_items WHERE restaurant_id = %s'
        params = [RESTAURANT_CONFIG['id']]
        
        # Filter by category
        if category:
            sql += ' AND LOWER(category) = LOWER(%s)'
            params.append(category)
        
        # Filter by availability
        if available.lower() in ['true', 'false']:
            availability = available.lower() == 'true'
            sql += ' AND availability = %s'
            params.append(availability)
        
        # Add ordering and pagination
        sql += ' ORDER BY category ASC, name ASC LIMIT %s OFFSET %s'
        params.extend([limit, offset])
        
        # Execute query
        items = execute_query(sql, tuple(params), fetch_all=True)
        
        # Get total count
        count_sql = 'SELECT COUNT(*) FROM menu_items WHERE restaurant_id = %s'
        count_params = [RESTAURANT_CONFIG['id']]
        
        if category:
            count_sql += ' AND LOWER(category) = LOWER(%s)'
            count_params.append(category)
        
        if available.lower() in ['true', 'false']:
            count_sql += ' AND availability = %s'
            count_params.append(available.lower() == 'true')
        
        count_result = execute_query(count_sql, tuple(count_params), fetch_one=True)
        # RealDictCursor returns dict; default cursor returns tuple
        if isinstance(count_result, dict):
            total_count = list(count_result.values())[0]
        else:
            total_count = count_result[0] if count_result else 0
        
        return jsonify({
            'status': 'success',
            'message': SUCCESS_MESSAGES['MENU_ITEMS_FETCHED'],
            'data': {
                'items': [format_menu_item(item) for item in items],
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'total': total_count,
                    'returned': len(items)
                }
            }
        }), HTTP_STATUS['OK']
    
    except Exception as e:
        logger.error(f'Error fetching menu items: {str(e)}')
        raise

# ============================================
# GET SINGLE MENU ITEM
# ============================================
@menu_bp.route('/<int:item_id>', methods=['GET'])
@handle_exceptions
def get_menu_item(item_id):
    """
    Get single menu item by ID
    
    Args:
        item_id: Menu item ID
    
    Returns:
        JSON menu item or 404
    """
    try:
        sql = """
            SELECT id, restaurant_id, name, description, price, category, 
                   availability, preparation_time, image_url, created_at, updated_at
            FROM menu_items 
            WHERE id = %s AND restaurant_id = %s
        """
        params = (item_id, RESTAURANT_CONFIG['id'])
        
        item = execute_query(sql, params, fetch_one=True)
        
        if not item:
            raise ValidationError(ERROR_MESSAGES['MENU_ITEM_NOT_FOUND'], HTTP_STATUS['NOT_FOUND'])
        
        return jsonify({
            'status': 'success',
            'data': format_menu_item(item)
        }), HTTP_STATUS['OK']
    
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f'Error fetching menu item {item_id}: {str(e)}')
        raise

# ============================================
# GET ITEMS BY CATEGORY
# ============================================
@menu_bp.route('/category/<category>', methods=['GET'])
@handle_exceptions
def get_by_category(category):
    """
    Get all items in a specific category
    
    Args:
        category: Category name (breakfast, burgers, sandwiches, etc.)
    
    Returns:
        JSON array of items in category
    """
    try:
        # Validate category exists
        valid_categories = RESTAURANT_CONFIG['categories']
        
        if category.lower() not in [c.lower() for c in valid_categories]:
            raise ValidationError(
                f'Invalid category. Valid options: {", ".join(valid_categories)}',
                HTTP_STATUS['BAD_REQUEST']
            )
        
        sql = """
            SELECT id, restaurant_id, name, description, price, category, 
                   availability, preparation_time, image_url, created_at, updated_at
            FROM menu_items 
            WHERE restaurant_id = %s AND LOWER(category) = LOWER(%s)
            ORDER BY name ASC
        """
        params = (RESTAURANT_CONFIG['id'], category)
        
        items = execute_query(sql, params, fetch_all=True)
        
        return jsonify({
            'status': 'success',
            'category': category.lower(),
            'count': len(items),
            'data': [format_menu_item(item) for item in items]
        }), HTTP_STATUS['OK']
    
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f'Error fetching category {category}: {str(e)}')
        raise

# ============================================
# SEARCH MENU ITEMS
# ============================================
@menu_bp.route('/search', methods=['GET'])
@handle_exceptions
def search_menu():
    """
    Search menu items by name or description
    
    Query params:
        - q: Search query (required)
        - category: Optional category filter
    
    Returns:
        JSON array of matching items
    """
    try:
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        
        if not query:
            raise ValidationError('Search query (q) is required', HTTP_STATUS['BAD_REQUEST'])
        
        if len(query) < 2:
            raise ValidationError('Search query must be at least 2 characters', HTTP_STATUS['BAD_REQUEST'])
        
        # Build search query
        sql = """
            SELECT id, restaurant_id, name, description, price, category, 
                   availability, preparation_time, image_url, created_at, updated_at
            FROM menu_items 
            WHERE restaurant_id = %s 
            AND (LOWER(name) LIKE LOWER(%s) OR LOWER(description) LIKE LOWER(%s))
        """
        params = [RESTAURANT_CONFIG['id'], f'%{query}%', f'%{query}%']
        
        # Add category filter if provided
        if category:
            sql += ' AND LOWER(category) = LOWER(%s)'
            params.append(category)
        
        sql += ' ORDER BY name ASC'
        
        items = execute_query(sql, tuple(params), fetch_all=True)
        
        return jsonify({
            'status': 'success',
            'search_query': query,
            'category_filter': category if category else None,
            'results_count': len(items),
            'data': [format_menu_item(item) for item in items]
        }), HTTP_STATUS['OK']
    
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f'Error searching menu: {str(e)}')
        raise

# ============================================
# GET CATEGORIES
# ============================================
@menu_bp.route('/categories', methods=['GET'])
@handle_exceptions
def get_categories():
    """
    Get all available menu categories with item counts
    
    Returns:
        JSON object with categories and counts
    """
    try:
        sql = """
            SELECT LOWER(category) as category, COUNT(*) as count
            FROM menu_items 
            WHERE restaurant_id = %s
            GROUP BY LOWER(category)
            ORDER BY category ASC
        """
        params = (RESTAURANT_CONFIG['id'],)
        
        results = execute_query(sql, params, fetch_all=True)
        
        categories = {}
        for row in results:
            if isinstance(row, dict):
                cat = row['category']
                cnt = row['count']
            else:
                cat = row[0]
                cnt = row[1]
            categories[cat] = cnt
        
        return jsonify({
            'status': 'success',
            'categories': categories,
            'total_categories': len(categories)
        }), HTTP_STATUS['OK']
    
    except Exception as e:
        logger.error(f'Error fetching categories: {str(e)}')
        raise

# ============================================
# UPDATE ITEM AVAILABILITY
# ============================================
@menu_bp.route('/<int:item_id>/availability', methods=['PUT'])
@handle_exceptions
def update_availability(item_id):
    """
    Update menu item availability (admin only)
    
    Args:
        item_id: Menu item ID
        
    JSON body:
        {
            "availability": true/false
        }
    
    Returns:
        Updated item
    """
    try:
        data = request.get_json() or {}
        
        if 'availability' not in data:
            raise ValidationError('availability field is required', HTTP_STATUS['BAD_REQUEST'])
        
        availability = bool(data['availability'])
        
        sql = """
            UPDATE menu_items 
            SET availability = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND restaurant_id = %s
            RETURNING id, restaurant_id, name, description, price, category, 
                      availability, preparation_time, image_url, created_at, updated_at
        """
        params = (availability, item_id, RESTAURANT_CONFIG['id'])
        
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
        
        if not result:
            raise ValidationError(ERROR_MESSAGES['MENU_ITEM_NOT_FOUND'], HTTP_STATUS['NOT_FOUND'])
        
        logger.info(f'Menu item {item_id} availability updated to {availability}')
        
        return jsonify({
            'status': 'success',
            'message': 'Availability updated',
            'data': format_menu_item(result)
        }), HTTP_STATUS['OK']
    
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f'Error updating availability: {str(e)}')
        raise

# ============================================
# HELPER FUNCTION
# ============================================
def format_menu_item(item):
    """
    Format menu item from database for JSON response
    
    Args:
        item: Database row (dict or tuple)
    
    Returns:
        Formatted dict
    """
    if isinstance(item, dict):
        return {
            'id': item.get('id'),
            'name': item.get('name'),
            'description': item.get('description'),
            'price': float(item.get('price', 0)),
            'category': item.get('category'),
            'available': item.get('availability', True),
            'preparationTime': item.get('preparation_time', 10),
            'imageUrl': item.get('image_url'),
            'createdAt': item.get('created_at').isoformat() if item.get('created_at') else None,
            'updatedAt': item.get('updated_at').isoformat() if item.get('updated_at') else None
        }
    else:
        # Tuple format (fallback)
        return {
            'id': item[0],
            'name': item[2],
            'description': item[3],
            'price': float(item[4]),
            'category': item[5],
            'available': item[6],
            'preparationTime': item[7],
            'imageUrl': item[8],
            'createdAt': item[9].isoformat() if item[9] else None,
            'updatedAt': item[10].isoformat() if item[10] else None
        }
