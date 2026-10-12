import os
import json
import requests
import datetime
import logging
from flask import Flask, render_template, request, jsonify, make_response, url_for
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_swagger_ui import get_swaggerui_blueprint

from agent import MetaAgent

meta_agent = MetaAgent()

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configure cache
cache_config = {
    "CACHE_TYPE": "SimpleCache",  # Simple in-memory cache
    "CACHE_DEFAULT_TIMEOUT": 300  # 5 minutes
}
cache = Cache(app, config=cache_config)

# Configure rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configure Swagger UI
SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "LLM Test"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

def configure_logging():
    """Configure application logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Configure Flask logger
    app.logger.setLevel(numeric_level)
    
    # Add a formatter to the handler
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)

@app.route('/')
def index():
    """Serves the chat web interface"""
    return render_template('index.html')

@app.route('/example')
def example():
    """Serves an example of structured formatting"""
    with open('static/examples/structured_response_example.md', 'r') as file:
        example_text = file.read()
    return jsonify({'response': example_text})

@app.route('/health')
def health_check():
    """Health check endpoint for container orchestration"""
    # Check if LLM API is accessible
    llm_status = "ok"
    try:
        # Simple check if the LLM endpoint is configured
        if not meta_agent.llm_endpoint:
            llm_status = "not_configured"
    except Exception as e:
        llm_status = "error"
        app.logger.error(f"Health check error: {e}")
    
    return jsonify({
        "status": "healthy",
        "llm_api": llm_status,
        "timestamp": datetime.datetime.now().isoformat()
    })

def validate_chat_request(data):
    """Validates and sanitizes chat API request data"""
    if not isinstance(data, dict):
        return False, "Invalid request format"
    
    message = data.get('message', '')
    if not message or not isinstance(message, str):
        return False, "Message is required and must be a string"
    
    if len(message) > 4000:  # Reasonable limit
        return False, "Message too long (max 4000 characters)"
    
    return True, message

@app.route('/api/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat_api():
    """Processes chat API requests"""
    data = request.json
    
    # Validate request
    valid, result = validate_chat_request(data)
    if not valid:
        return jsonify({'error': result}), 400
    
    message = result
    
    # Special command for getting model info
    if message == "!modelinfo":
        return jsonify({'model': meta_agent.model_name})
    
    # Call the LLM API
    try:
        response = meta_agent.request(message)
        return jsonify({'response': response})
    except Exception as e:
        app.logger.error(f"Error calling LLM API: {e}")
        return jsonify({'error': 'Failed to get response from LLM'}), 500



@app.after_request
def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com"
    return response

if __name__ == '__main__':
    # Configure logging
    configure_logging()
    
    # Validate environment
    port = int(os.getenv("KYZO_PORT", 8081))
    
    app.logger.info(f"Server starting on http://localhost:{port}")
    app.logger.info(f"Using LLM endpoint: {meta_agent.llm_endpoint}")
    app.logger.info(f"Using model: {meta_agent.model_name}")
    
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "false").lower() == "true")
