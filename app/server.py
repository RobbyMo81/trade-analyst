"""Flask server for handling OAuth callbacks and health checks"""

import logging
from flask import Flask, request, jsonify, redirect, url_for
from urllib.parse import parse_qs
from .auth import AuthManager
from .config import Config
from .healthcheck import HealthChecker

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # TODO: Move to config

# Initialize components
config = Config()
auth_manager = AuthManager(config)
health_checker = HealthChecker(config)


@app.route('/')
def index():
    """Root endpoint with basic information"""
    return jsonify({
        'service': 'Trade Analyst API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'callback': '/callback',
            'auth_status': '/auth/status'
        }
    })


@app.route('/health')
async def health():
    """Health check endpoint"""
    try:
        logger.info("Health check requested")
        
        # Run health checks
        health_status = await health_checker.check_all()
        
        status_code = 200 if health_status.is_healthy else 503
        
        response = {
            'status': 'healthy' if health_status.is_healthy else 'unhealthy',
            'timestamp': health_status.timestamp,
            'checks': [
                {
                    'name': check.name,
                    'status': check.status,
                    'message': check.message,
                    'error': check.error
                }
                for check in health_status.checks
            ]
        }
        
        return jsonify(response), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/callback')
async def oauth_callback():
    """OAuth callback endpoint"""
    try:
        logger.info("OAuth callback received")
        
        # Get authorization code and state from query parameters
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        provider = request.args.get('provider', 'default')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return jsonify({
                'status': 'error',
                'error': error,
                'error_description': request.args.get('error_description', '')
            }), 400
        
        if not code:
            logger.error("No authorization code received")
            return jsonify({
                'status': 'error',
                'error': 'missing_code',
                'message': 'Authorization code not provided'
            }), 400
        
        # Handle the callback
        success = await auth_manager.handle_callback(code, state, provider)
        
        if success:
            logger.info("OAuth callback handled successfully")
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful',
                'provider': provider
            })
        else:
            logger.error("OAuth callback handling failed")
            return jsonify({
                'status': 'error',
                'error': 'callback_failed',
                'message': 'Failed to process OAuth callback'
            }), 400
            
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return jsonify({
            'status': 'error',
            'error': 'internal_error',
            'message': str(e)
        }), 500


@app.route('/auth/status')
async def auth_status():
    """Get authentication status"""
    try:
        logger.info("Authentication status requested")
        
        # Check authentication status for all providers
        providers = config.get('auth_providers', ['default'])
        status = {}
        
        for provider in providers:
            token = await auth_manager.get_access_token(provider)
            status[provider] = {
                'authenticated': token is not None,
                'has_token': token is not None
            }
        
        return jsonify({
            'status': 'success',
            'providers': status
        })
        
    except Exception as e:
        logger.error(f"Auth status check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/auth/login/<provider>')
async def auth_login(provider):
    """Initiate authentication for a provider"""
    try:
        logger.info(f"Authentication login requested for provider: {provider}")
        
        success = await auth_manager.login(provider)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Authentication initiated for {provider}',
                'provider': provider
            })
        else:
            return jsonify({
                'status': 'error',
                'error': 'login_failed',
                'message': f'Failed to initiate authentication for {provider}'
            }), 400
            
    except Exception as e:
        logger.error(f"Auth login error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/config')
def get_config():
    """Get application configuration (non-sensitive parts)"""
    try:
        safe_config = {
            'version': '1.0.0',
            'environment': config.get('environment', 'development'),
            'features': {
                'quotes': config.get('enable_quotes', True),
                'historical': config.get('enable_historical', True),
                'options': config.get('enable_options', True),
                'timesales': config.get('enable_timesales', True)
            },
            'rate_limits': {
                'quotes_per_minute': config.get('quotes_rate_limit', 100),
                'historical_per_minute': config.get('historical_rate_limit', 50),
                'options_per_minute': config.get('options_rate_limit', 30)
            }
        }
        
        return jsonify(safe_config)
        
    except Exception as e:
        logger.error(f"Config retrieval failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'status': 'error',
        'error': 'not_found',
        'message': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'error': 'internal_error',
        'message': 'An internal error occurred'
    }), 500


@app.before_request
def log_request():
    """Log all requests"""
    logger.info(f"{request.method} {request.path} from {request.remote_addr}")


@app.after_request
def log_response(response):
    """Log response status"""
    logger.info(f"Response: {response.status_code}")
    
    # Add CORS headers if needed
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    return response


def create_app(config_object=None):
    """Application factory"""
    if config_object:
        app.config.from_object(config_object)
    
    return app


if __name__ == '__main__':
    # Development server
    app.run(host='127.0.0.1', port=5000, debug=True)
