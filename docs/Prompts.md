현재 저는 시사 이슈 자동 추적 서비스를 만들기 위해 Next.js(프론트엔드)와 Python FastAPI(백엔드)를 결합한 단일 프로젝트(Monorepo) 환경을 구축하려고 합니다. 

나중에 Vercel로 원클릭 배포가 가능하고, 로컬 개발 환경에서 프론트와 백엔드가 동시에 구동되는 가장 표준적인 'Next.js + Python FastAPI 내장 구조'의 프로젝트 초기 세팅 코드와 폴더 가이드를 작성해 주세요. 

다음 요구사항을 충족하도록 완벽한 파일들을 생성해 주세요:

1. [전체 폴더 구조 가이드]: 프로젝트의 루트(Root) 폴더 구조를 트리 형태로 명확히 보여주세요. (프론트는 루트 또는 /app 폴더, 파이썬 백엔드는 루트의 /api 폴더에 위치)

2. [next.config.js 설정]: 프론트엔드에서 '/api/:path*'로 요청을 보내면, 내부적으로 파이썬 FastAPI 서버(예: http://127.0.0.1:8000)로 주소를 매핑(Rewrites)해 주어 CORS 에러가 나지 않도록 설정을 짜주세요.

3. [package.json]: 로컬에서 명령어 하나(예: npm run dev)만 입력하면 프론트엔드 서버와 파이썬 FastAPI 서버가 동시에 켜지도록 'concurrently' 등을 활용한 개발 스크립트(scripts) 설정을 작성해 주세요.

4. [api/requirements.txt]: 파이썬 환경에 필요한 필수 패키지 목록을 작성해 주세요. (fastapi, uvicorn, openai, langchain-community, tavily-python 필수 포함)

5. [api/index.py]: 가장 기초적인 FastAPI 엔드포인트를 구현해 주세요. Next.js 프론트엔드가 호출할 수 있는 `@app.get("/api/health")`와 테스트용 셈플 데이터를 주는 라우트를 포함해 주세요.

6. [app/page.tsx (또는 page.js)]: React/Next.js 화면에서 `useEffect`나 버튼 클릭 이벤트를 통해 파이썬 백엔드의 "/api/health"를 fetch로 호출하고, 받아온 데이터를 화면에 띄우는 프론트엔드 예시 코드를 보여주세요.

모든 코드는 주석을 친절하게 달아주고, 터미널에 입력해야 하는 초기 라이브러리 설치 명령어까지 한 번에 정리해 주세요.
