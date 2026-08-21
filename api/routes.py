from flask import Blueprint, jsonify, request
from .services import (
    get_daily_trends, get_weekly_trends, get_monthly_trends,
    get_theme_rollup, get_trend_delta, load_products,
    ranking_rows, get_ranking_change, get_search_suggestions,
    get_categories  # ✅ 신규 추가
)

api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/trends/daily')
def api_daily():
    return jsonify(get_daily_trends())

@api.route('/trends/weekly')
def api_weekly():
    limit = request.args.get('limit', 25, type=int)
    return jsonify(get_weekly_trends(limit))

@api.route('/trends/monthly')
def api_monthly():
    limit = request.args.get('limit', 30, type=int)
    return jsonify(get_monthly_trends(limit))

@api.route('/trends/themes')
def api_themes():
    days = request.args.get('days', 7, type=int)
    return jsonify(get_theme_rollup(days))

@api.route('/trends/delta')
def api_delta():
    period = request.args.get('period', 'weekly')
    return jsonify(get_trend_delta(period))

@api.route('/products')
def api_products():
    limit = request.args.get('limit', 80, type=int)
    offset = request.args.get('offset', 0, type=int)
    q = request.args.get('q')
    category = request.args.get('category')
    source = request.args.get('source')
    rows, latest = load_products(limit=limit, q=q, category=category, source=source, offset=offset)
    return jsonify({
        "items": rows,
        "latest_date": latest,
        "has_more": len(rows) == limit
    })

@api.route('/rankings')
def api_rankings():
    kind = request.args.get('kind', 'overall')
    limit = request.args.get('limit', 50, type=int)
    rows, latest = ranking_rows(kind, limit)
    return jsonify({
        "items": rows,
        "latest_date": latest
    })

@api.route('/rankings/change')
def api_change():
    limit = request.args.get('limit', 50, type=int)
    return jsonify(get_ranking_change(limit))

@api.route('/suggestions')
def api_suggestions():
    limit = request.args.get('limit', 40, type=int)
    return jsonify({"items": get_search_suggestions(limit)})

@api.route('/categories')  # ✅ 신규 추가
def api_categories():
    return jsonify(get_categories())
