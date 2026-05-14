"""
cache.py — Flask-Caching instance shared across the app.

Initialised in app.py via cache.init_app(server, config={...}).
Used in edgar.py and models.py via @cache.memoize().
"""

from flask_caching import Cache

cache = Cache()
