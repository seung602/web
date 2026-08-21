#!/bin/bash
set -e

# data 디렉토리 생성
mkdir -p data

# 재시도 옵션: HTTP/2 에러 시 HTTP/1.1로 fallback + 5회 재시도
CURL_OPTS="--retry 5 --retry-delay 3 --retry-all-errors --retry-max-time 300 -L -f --http1.1"

echo "📥 Info 레포에서 beauty_catalog.db 다운로드 중..."
curl $CURL_OPTS -o data/beauty_catalog.db https://github.com/seung602/Info/raw/main/beauty_catalog.db

echo "📥 daiy-trend-bot 레포에서 beauty_trends.db 다운로드 중..."
curl $CURL_OPTS -o data/beauty_trends.db https://github.com/seung602/daiy-trend-bot/raw/main/beauty_trends.db

echo "📦 패키지 설치 중..."
pip install -r requirements.txt

echo "✅ 빌드 완료!"
