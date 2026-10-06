# Clip Search

Clip Search는 CLIP 기반 임베딩과 벡터 검색을 활용해 영상의 장면을 관리하고 검색하는 애플리케이션입니다. React 프런트엔드, FastAPI 백엔드, Celery 비동기 작업자를 구성해 영상 업로드부터 프레임 추출과 임베딩 생성까지의 처리 흐름을 구현했습니다.

## 주요 기능

- 쿠키 기반 인증을 통한 회원가입 및 로그인
- 영상 업로드와 처리 진행 상태 확인
- S3에 영상 및 추출 프레임 저장
- FFmpeg를 이용한 영상 프레임 추출
- MariaDB에 영상·프레임 메타데이터 저장
- `openai/clip-vit-base-patch32` 모델을 이용한 이미지·텍스트 임베딩 생성
- Qdrant에 벡터 저장 및 유사도 검색
- Redis를 이용한 영상 처리 상태와 비동기 검색 작업 상태 관리

## 기술 구성

| 구성 요소 | 위치 | 역할 |
| --- | --- | --- |
| 프런트엔드 | `frontend/` | React, TypeScript, Vite 기반 사용자 인터페이스 |
| API 서버 | `backend/main.py`, `backend/routes/` | FastAPI 애플리케이션 및 HTTP API |
| 서비스 계층 | `backend/services/` | 애플리케이션 흐름과 비즈니스 로직 조정 |
| 비동기 작업자 | `backend/workers/tasks/` | Celery 기반 프레임 추출 및 임베딩 작업 |
| 데이터베이스 | `backend/infra/db/` | MariaDB 모델, 연결 및 저장소 |
| 벡터 검색 | `backend/infra/qdrant/` | Qdrant 연결 및 벡터 검색 |
| 작업 상태 관리 | `backend/infra/redis/` | Redis 기반 영상 진행 상태와 검색 작업 데이터 관리 |
| 배포 설정 | `k8s/` | Kubernetes 리소스 설정 |

## 영상 처리 흐름

1. API 서버가 업로드된 영상의 메타데이터를 MariaDB에 저장하고 영상 파일을 S3에 업로드합니다.
2. Celery 프레임 추출 작업이 FFmpeg로 프레임을 추출하고, 프레임 메타데이터를 MariaDB에 기록한 뒤 프레임 파일을 S3에 저장합니다.
3. 임베딩 작업자가 CLIP 이미지 임베딩을 생성해 Qdrant에 저장합니다.
4. Redis가 프레임 추출 및 임베딩 진행 상태를 관리하고, API 서버는 Server-Sent Events(SSE)로 상태를 전달합니다.
5. 텍스트 임베딩 작업은 검색 문장을 벡터로 변환해 Qdrant에서 해당 영상의 유사 프레임을 검색합니다.

## 사전 준비

- Python 3.13
- Node.js 및 npm
- FFmpeg
- MariaDB
- Redis
- Qdrant
- S3 버킷과 객체 업로드·다운로드·삭제 권한을 가진 AWS 자격 증명
- GPU는 선택 사항이며, CPU에서도 CLIP 모델을 실행할 수 있습니다.

백엔드 Dockerfile은 `python:3.13-slim`을 사용합니다. CLIP 모델은 Hugging Face에서 처음 사용할 때 내려받으며, `MODEL_CACHE_DIR` 경로에 캐시됩니다.

## 환경 변수 설정

백엔드는 `backend/.env`에서 환경 변수를 읽습니다. 아래 예시를 참고해 로컬 환경에 맞는 파일을 생성하세요. 실제 자격 증명이나 비밀 키를 Git에 추가하지 마세요.

```dotenv
# API
LOCAL_VIDEO_STORAGE=./videos/
ALLOW_ORIGINS=http://localhost:9002,http://127.0.0.1:9002

# CLIP 모델
PRETRAINED_MODEL=openai/clip-vit-base-patch32
MODEL_CACHE_DIR=.cache/models

# Qdrant
QDRANT_IP=127.0.0.1
QDRANT_PORT=6333
FRAME_COLLECTION=Frame
DEMENSION=512

# Redis 및 Celery
REDIS_URL=127.0.0.1
BROKER_URL=redis://127.0.0.1:6379/0

# MariaDB
MARIADB_URL=127.0.0.1
MARIADB_PORT=3306
MARIADB_DATABASE=CLIP
MARIADB_USER=clip_user
MARIADB_PASSWORD=PASSWORD

# 인증
JWT_SECRET=충분히_긴_임의의_비밀_키
HASH_ALGO=HS256
ACCESS_TOKEN_EXPIRE=900
REFRESH_TOKEN_EXPIRE=1296000

# S3
S3_ACCESS_KEY=AWS_액세스_키
S3_ACCESS_SECRET_KEY=AWS_시크릿_키
CLIP_BUCKET_NAME=사용할_S3_버킷_이름
```

현재 설정 키 이름은 코드와의 호환성을 위해 `DEMENSION`으로 유지되어 있습니다. S3 클라이언트의 리전은 코드에서 `us-west-2`로 지정합니다.

프런트엔드의 API 주소는 `frontend/.env.local`에 설정합니다.

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

## 로컬 실행

### 1. 기반 서비스 실행

MariaDB, Redis, Qdrant를 로컬에서 실행하거나 접근 가능한 서버를 준비합니다. 애플리케이션은 여기에 더해 S3를 사용하며, Celery 브로커와 결과 백엔드에는 Redis를 사용합니다.

### 2. 백엔드 API 실행

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

개발 환경에서는 API가 시작될 때 현재 SQLAlchemy 모델을 기준으로 MariaDB 테이블을 생성합니다. API 문서는 <http://localhost:8000/docs>에서 확인할 수 있습니다.

### 3. Celery 작업자 실행

별도의 터미널에서 실행합니다.

```bash
cd backend
source .venv/bin/activate
celery -A workers.worker.celery_app worker \
  -Q extraction_queue,embedding_queue,text_queue \
  --concurrency=1 \
  --loglevel=info
```

작업자는 `backend/workers/tasks/`의 작업 모듈을 불러옵니다. CLIP 모델의 최초 다운로드에는 시간이 걸릴 수 있습니다. 작업자 시작 시 모델을 미리 불러오려면 환경에 따라 `DEVICE_TYPE=FRAME_EMBEDDING` 또는 `DEVICE_TYPE=TEXT_EMBEDDING`을 설정할 수 있습니다.

### 4. 프런트엔드 실행

별도의 터미널에서 실행합니다.

```bash
cd frontend
npm ci
npm run dev
```

Vite 개발 서버는 <http://localhost:9002>에서 실행됩니다.

## 현재 API

현재 `backend/main.py`에 등록된 라우터가 제공하는 주요 엔드포인트입니다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/auth/register` | 계정 등록 |
| `POST` | `/auth/login` | 로그인 및 인증 쿠키 발급 |
| `POST` | `/video/upload` | 영상 업로드 및 프레임 추출 작업 등록 |
| `GET` | `/video/list` | 로그인한 사용자의 영상 목록 조회 |
| `DELETE` | `/video/{video_uuid}` | 영상 및 관련 데이터 삭제 |
| `GET` | `/video/progress/{video_uuid}` | SSE를 이용한 영상 처리 상태 스트리밍 |

텍스트 기반 CLIP 검색 라우터는 `backend/routes/clip.py`에 구현되어 있지만 현재 `backend/main.py`에 등록되어 있지 않습니다. 따라서 라우터를 등록하기 전까지는 실행 중인 FastAPI 애플리케이션에서 검색 엔드포인트를 사용할 수 없습니다.

## 유용한 명령

```bash
# 데이터베이스 마이그레이션
cd backend
alembic upgrade head

# 프런트엔드 프로덕션 빌드 및 린트
cd frontend
npm run build
npm run lint
```

마이그레이션을 실행하기 전에 `backend/alembic.ini`의 `sqlalchemy.url`을 사용할 MariaDB 주소로 설정해야 합니다. 현재 파일에는 배포 환경용 주소가 포함되어 있습니다. 개발 환경에서 API는 시작 시 SQLAlchemy 모델을 기준으로 테이블을 생성합니다.

## 참고 사항

- `.env` 파일, AWS 자격 증명, JWT 비밀 키, 데이터베이스 비밀번호는 저장소에 추가하지 마세요.
- 영상 진행 상태와 검색 작업 정보는 만료 시간이 있는 Redis에 저장됩니다. Redis가 재시작되면 진행 중 작업의 상태 데이터가 사라질 수 있습니다.
- `backend/docker-compose.yaml`과 `backend/docker-compose.dev.yaml`에 Compose 설정이 있습니다. 다만 실제 실행 명령과 필요한 환경 변수는 위 로컬 실행 절차를 참고하세요.
- `backend/test/`에는 수동 실행 스크립트와 탐색용 자료가 있습니다. 현재 저장소에서 자동화된 테스트 스위트는 확인되지 않았습니다.
