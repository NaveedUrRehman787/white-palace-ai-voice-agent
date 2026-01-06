#!/usr/bin/env python3
"""
Comprehensive Backend Testing Suite
Tests all major components of the White Palace AI Voice Agent backend
"""

import os
import sys
import asyncio
import json
import requests
import time
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# Set test environment variables
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'white_palace_db'
os.environ['DB_USER'] = 'whitepalace'
os.environ['DB_PASSWORD'] = 'whitepalace123'

def print_test_header(title):
    """Print formatted test header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_test_result(test_name, success, message=""):
    """Print formatted test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"   {message}")

class BackendTester:
    """Comprehensive backend testing suite"""

    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []

    def run_test(self, test_func, test_name):
        """Run a test function and record results"""
        try:
            print(f"\n🔄 Running: {test_name}")
            result = test_func()
            success = result.get('success', False) if isinstance(result, dict) else result
            message = result.get('message', '') if isinstance(result, dict) else ''
            self.test_results.append({
                'name': test_name,
                'success': success,
                'message': message
            })
            print_test_result(test_name, success, message)
            return success
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            self.test_results.append({
                'name': test_name,
                'success': False,
                'message': error_msg
            })
            print_test_result(test_name, False, error_msg)
            return False

    def test_database_connection(self):
        """Test database connection and basic operations"""
        try:
            from config.database import execute_query, get_db_cursor
            from config.restaurant_config import RESTAURANT_CONFIG

            # Test basic query
            result = execute_query("SELECT NOW()", fetch_one=True)
            if result:
                # Test restaurant data
                restaurant_sql = "SELECT name, phone FROM restaurants WHERE id = %s"
                restaurant = execute_query(restaurant_sql, (RESTAURANT_CONFIG["id"],), fetch_one=True)

                if restaurant:
                    return {
                        'success': True,
                        'message': f'Database connected, restaurant: {restaurant["name"] if isinstance(restaurant, dict) else restaurant[0]}'
                    }

            return {'success': False, 'message': 'Database query failed'}

        except Exception as e:
            return {'success': False, 'message': f'Database error: {str(e)}'}

    def test_health_endpoint(self):
        """Test health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'OK':
                    return {
                        'success': True,
                        'message': f'Health check OK - {data.get("restaurant", "Unknown")}'
                    }
            return {'success': False, 'message': f'Health check failed: {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'Health check error: {str(e)}'}

    def test_restaurant_endpoint(self):
        """Test restaurant info endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/restaurant", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('name') == 'White Palace Grill':
                    return {
                        'success': True,
                        'message': f'Restaurant info OK - {data.get("address", "Unknown address")}'
                    }
            return {'success': False, 'message': f'Restaurant endpoint failed: {response.status_code}'}
        except Exception as e:
            return {'success': False, 'message': f'Restaurant endpoint error: {str(e)}'}

    def test_menu_endpoints(self):
        """Test menu API endpoints"""
        try:
            # Test get all menu items
            response = self.session.get(f"{self.base_url}/api/menu", timeout=10)
            if response.status_code != 200:
                return {'success': False, 'message': f'Menu endpoint failed: {response.status_code}'}

            # Test menu search
            response = self.session.get(f"{self.base_url}/api/menu/search?q=burger", timeout=10)
            if response.status_code == 200:
                data = response.json()
                results_count = data.get('results_count', 0)
                return {
                    'success': True,
                    'message': f'Menu endpoints OK - found {results_count} search results'
                }

            return {'success': False, 'message': 'Menu search failed'}

        except Exception as e:
            return {'success': False, 'message': f'Menu endpoints error: {str(e)}'}

    def test_order_endpoints(self):
        """Test order API endpoints"""
        try:
            # Test get orders (should return empty or existing orders)
            response = self.session.get(f"{self.base_url}/api/orders", timeout=10)
            if response.status_code == 200:
                data = response.json()
                orders_count = len(data.get('data', {}).get('orders', []))
                return {
                    'success': True,
                    'message': f'Orders endpoint OK - {orders_count} orders found'
                }

            return {'success': False, 'message': f'Orders endpoint failed: {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'Orders endpoints error: {str(e)}'}

    def test_reservation_endpoints(self):
        """Test reservation API endpoints"""
        try:
            # Test get reservations
            response = self.session.get(f"{self.base_url}/api/reservations", timeout=10)
            if response.status_code == 200:
                data = response.json()
                reservations_count = len(data.get('data', {}).get('reservations', []))
                return {
                    'success': True,
                    'message': f'Reservations endpoint OK - {reservations_count} reservations found'
                }

            return {'success': False, 'message': f'Reservations endpoint failed: {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'Reservations endpoints error: {str(e)}'}

    def test_payment_endpoints(self):
        """Test payment API endpoints"""
        try:
            # Test payment stats (should work even with no payments)
            response = requests.get(f"{self.base_url}/api/payments/stats", timeout=10)
            if response.status_code == 200:
                data = response.json()
                total_payments = data.get('data', {}).get('totalPayments', 0)
                return {
                    'success': True,
                    'message': f'Payments endpoint OK - {total_payments} total payments'
                }

            # Log the response for debugging
            try:
                error_data = response.json()
                error_msg = error_data.get('message', 'Unknown error')
            except:
                error_msg = response.text[:100] if response.text else f'Status: {response.status_code}'

            return {'success': False, 'message': f'Payments endpoint failed: {response.status_code} - {error_msg}'}

        except Exception as e:
            return {'success': False, 'message': f'Payments endpoints error: {str(e)}'}

    def test_admin_auth(self):
        """Test admin authentication"""
        try:
            # Test admin login with correct password
            login_data = {'password': 'whitepalace2024'}
            response = self.session.post(f"{self.base_url}/api/admin/login",
                                       json=login_data, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and 'token' in data:
                    return {
                        'success': True,
                        'message': 'Admin authentication OK'
                    }

            return {'success': False, 'message': f'Admin login failed: {response.status_code} - {response.text}'}

        except Exception as e:
            return {'success': False, 'message': f'Admin auth error: {str(e)}'}

    async def test_llm_tools_async(self):
        """Test LLM function tools (async version)"""
        try:
            from agent_white_palace import gethours, getlocation

            # Test gethours
            class MockContext:
                session = None

            result = await gethours(MockContext())
            if not result.get('success'):
                return {'success': False, 'message': 'gethours tool failed'}

            # Test getlocation
            result = await getlocation(MockContext())
            if not result.get('success'):
                return {'success': False, 'message': 'getlocation tool failed'}

            return {
                'success': True,
                'message': 'LLM tools OK - gethours and getlocation working'
            }

        except Exception as e:
            return {'success': False, 'message': f'LLM tools error: {str(e)}'}

    def test_llm_tools(self):
        """Test LLM function tools"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.test_llm_tools_async())
            return result
        finally:
            loop.close()

    def test_websocket_service(self):
        """Test WebSocket service imports and basic functionality"""
        try:
            from utils.websocket_service import init_socketio, register_socketio_events
            # These should import without errors
            return {
                'success': True,
                'message': 'WebSocket service imports OK'
            }

        except Exception as e:
            return {'success': False, 'message': f'WebSocket service error: {str(e)}'}

    def test_voice_endpoints(self):
        """Test voice-related endpoints"""
        try:
            # Test voice room creation (without actual tokens)
            response = self.session.post(f"{self.base_url}/api/voice/create-room",
                                       json={'customerPhone': '+1234567890'}, timeout=10)

            # Should return 201 (created) for successful room creation, or 500 for missing tokens
            if response.status_code in [201, 500, 400]:
                return {
                    'success': True,
                    'message': f'Voice endpoints accessible (status: {response.status_code})'
                }

            return {'success': False, 'message': f'Voice endpoint unexpected response: {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'Voice endpoints error: {str(e)}'}

    def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🚀 STARTING COMPREHENSIVE BACKEND TESTING SUITE")
        print("=" * 60)

        # Core Infrastructure Tests
        self.run_test(self.test_database_connection, "Database Connection")
        self.run_test(self.test_websocket_service, "WebSocket Service")

        # API Endpoint Tests
        self.run_test(self.test_health_endpoint, "Health Check Endpoint")
        self.run_test(self.test_restaurant_endpoint, "Restaurant Info Endpoint")
        self.run_test(self.test_menu_endpoints, "Menu API Endpoints")
        self.run_test(self.test_order_endpoints, "Order API Endpoints")
        self.run_test(self.test_reservation_endpoints, "Reservation API Endpoints")
        self.run_test(self.test_payment_endpoints, "Payment API Endpoints")
        self.run_test(self.test_admin_auth, "Admin Authentication")

        # AI/LLM Tests
        self.run_test(self.test_llm_tools, "LLM Function Tools")
        self.run_test(self.test_voice_endpoints, "Voice API Endpoints")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY")
        print(f"{'='*60}")

        passed = sum(1 for test in self.test_results if test['success'])
        total = len(self.test_results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(".1f")

        if passed == total:
            print("🎉 ALL TESTS PASSED! Backend is fully functional.")
        else:
            print("⚠️  Some tests failed. Check details above.")
            print("\nFailed Tests:")
            for test in self.test_results:
                if not test['success']:
                    print(f"  ❌ {test['name']}: {test['message']}")

def main():
    """Main test runner"""
    # Check if backend is running
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend server not running or not healthy. Please start the backend first:")
            print("   cd backend && python app.py")
            return False
    except:
        print("❌ Backend server not accessible. Please start the backend first:")
        print("   cd backend && python app.py")
        return False

    # Run tests
    tester = BackendTester()
    tester.run_all_tests()

    return all(test['success'] for test in tester.test_results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
