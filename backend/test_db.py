import os
import sys

# 프로젝트 루트 디렉토리 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# 환경 변수 강제 재로드
load_dotenv(override=True)

# .env 파일에서 직접 DATABASE_URL 읽기 (UTF-8 인코딩 사용)
env_file_path = os.path.join(os.path.dirname(__file__), ".env")
print(f".env 파일 경로: {env_file_path}")

if os.path.exists(env_file_path):
    try:
        with open(env_file_path, "r", encoding="utf-8") as f:
            env_content = f.read()
    except UnicodeDecodeError:
        # UTF-8 실패 시 다른 인코딩 시도
        with open(env_file_path, "r", encoding="cp1252") as f:
            env_content = f.read()
    
    print(".env 파일 내용:")
    print(env_content)
    
    # DATABASE_URL 직접 추출
    for line in env_content.splitlines():
        if line.startswith("DATABASE_URL="):
            db_url_from_file = line.split("=", 1)[1].strip()
            print(f"\n.env 파일에서 추출한 DATABASE_URL: {db_url_from_file}")
            # 환경 변수 강제 설정
            os.environ["DATABASE_URL"] = db_url_from_file

# DATABASE_URL 확인
db_url = os.environ.get("DATABASE_URL")
print(f"\n환경 변수 DATABASE_URL: {db_url}")

# 간단한 연결 테스트
if db_url:
    try:
        from sqlalchemy import create_engine, text
        
        print(f"\nSQLAlchemy로 연결 테스트 중...")
        print(f"URL: {db_url}")
        
        # 엔진 생성
        engine = create_engine(db_url, pool_pre_ping=True)
        
        # 연결 시도
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ PostgreSQL 버전: {version}")
            
            # 테이블 확인
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"✅ 공개 스키마의 테이블: {tables}")
            
    except Exception as e:
        print(f"❌ 연결 실패: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ DATABASE_URL 환경 변수가 설정되지 않았습니다.")