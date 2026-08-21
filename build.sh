#!/bin/bash
set -e

mkdir -p data

CURL_OPTS="--retry 5 --retry-delay 3 --retry-all-errors --retry-max-time 300 -L -f --http1.1"

echo "📥 practice 레포에서 beauty_catalog.db 다운로드 중..."
curl $CURL_OPTS -o data/beauty_catalog.db https://github.com/seung602/practice/raw/main/beauty_catalog.db

echo "📥 daiy-trend-bot 레포에서 beauty_trends.db 다운로드 중..."
curl $CURL_OPTS -o data/beauty_trends.db https://github.com/seung602/daiy-trend-bot/raw/main/beauty_trends.db

echo "📦 패키지 설치 중..."
pip install -r requirements.txt

echo "✅ 빌드 완료!"
