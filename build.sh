#!/bin/bash
set -e

echo "📥 Info 레포에서 beauty_catalog.db 다운로드 중..."
curl -L -f -o beauty_catalog.db https://github.com/seung602/Info/raw/main/beauty_catalog.db

echo "📥 daiy-trend-bot 레포에서 beauty_trends.db 다운로드 중..."
curl -L -f -o beauty_trends.db https://github.com/seung602/daiy-trend-bot/raw/main/beauty_trends.db

echo "📦 패키지 설치 중..."
pip install -r requirements.txt

echo "✅ 빌드 완료!"
