import sqlite3
import google.generativeai as genai
from flask import Flask, request, jsonify
import os

app = Flask(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def expand_keywords(query):
    """다국어 검색어를 한국어 동의어 및 성분명으로 확장"""
    prompt = f"""
    You are a K-Beauty search engine. Convert the user's query into Korean keywords for SQLite LIKE search.
    - Include synonyms and spelling variations (e.g., 'sunstick' -> '선스틱', '썬스틱', '선크림스틱').
    - If it's an ingredient (e.g., 'Niacinamide', 'واقي شمس'), return the Korean ingredient name or matching product category.
    - Output ONLY a comma-separated list of Korean keywords (e.g., "선스틱,썬스틱,선크림스틱").
    Query: "{query}"
    """
    response = model.generate_content(prompt)
    return [k.strip() for k in response.text.strip().split(',') if k.strip()]

@app.route('/api/search')
def search_products():
    query = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    limit = 20
    offset = (page - 1) * limit

    if not query:
        return jsonify({"products": [], "has_more": False})

    # 1. Gemini로 키워드 확장 (다국어 -> 한국어 동의어 리스트)
    keywords = expand_keywords(query)
    
    # 2. DB 연결
    # Info 레포에서 생성한 DB와 자체 랭킹 테이블이 있다고 가정
    db_path = 'path/to/beauty_catalog.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 3. 동적 WHERE 절 생성 (상품명, 브랜드, 카테고리, 성분 검색)
    conditions = []
    params = []
    for k in keywords:
        conditions.append("(p.product_name LIKE ? OR p.category LIKE ? OR p.ingredients LIKE ? OR p.brand LIKE ?)")
        params.extend([f'%{k}%', f'%{k}%', f'%{k}%', f'%{k}%'])

    where_clause = " OR ".join(conditions)

    # 4. 자체 제작 랭킹 테이블(custom_rankings)과 JOIN하여 인기순 정렬
    # (랭킹 테이블 이름은 실제 사용하시는 이름으로 변경하세요)
    sql = f"""
        SELECT p.product_id, p.source, p.brand, p.product_name, p.category, 
               p.current_price, p.product_url, cr.rank_num
        FROM products p
        JOIN custom_rankings cr ON p.product_id = cr.product_id
        WHERE {where_clause}
        ORDER BY cr.rank_num ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    cursor.execute(sql, params)
    products = [dict(row) for row in cursor.fetchall()]
    
    # 더보기 버튼 숨김 처리를 위해 다음 페이지 데이터 존재 여부 확인
    has_more = len(products) == limit 
    
    conn.close()
    return jsonify({
        "keywords": keywords,
        "products": products,
        "has_more": has_more
    })
