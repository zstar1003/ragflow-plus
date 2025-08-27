# 고급 기술

이 모듈은 어느 정도 경험이 있는 개발자에게 적합한 몇 가지 고급 사용 기술을 소개합니다.

## 1. GPU 가속

이 프로젝트는 GPU 배포 방안을 제공하며, 독립 그래픽 카드를 통해 문서 파싱 속도를 크게 가속화할 수 있습니다. 예약된 여유 VRAM은 6GB 이상이어야 합니다.

Docker 시작:

```bash
docker compose -f docker/docker-compose_gpu.yml up -d
```

시작 후 컨테이너가 그래픽 카드 정보를 찾지 못하면 nvidia-container-runtime을 별도로 설치해야 합니다:

```bash
sudo apt install nvidia-container-runtime
```

위 방법으로 해결되지 않으면 다음 대체 방안을 고려할 수 있습니다:

```bash
# 575는 특정 버전 번호이며, 특정 GPU 모델에 따라 적절한 버전을 선택할 수 있습니다
sudo apt install nvidia-cuda-toolkit
sudo apt install nvidia-container-toolkit
sudo apt install nvidia-fabricmanager-575
sudo apt install libnvidia-nscq-575
sudo systemctl start nvidia-fabricmanager
sudo systemctl enable nvidia-fabricmanager
sudo systemctl status nvidia-fabricmanager
```

## 2. 소스 코드로 시작

Docker 외에도 이 프로젝트는 소스 코드를 사용하여 프론트엔드와 백엔드를 시작하는 것을 지원합니다.

### 1. 미들웨어 시작

Docker를 사용하여 미들웨어 시작:

```bash
docker start ragflow-es-01
docker start ragflow-mysql
docker start ragflow-minio
docker start ragflow-redis
```

동시에 `docker\.env`의 `MINIO_HOST`를 `localhost`로 수정합니다.

### 2. 프론트엔드 환경 시작

백엔드 의존성 설치

```bash
pip install -r requirements.txt
```

백엔드 시작
```bash
python -m api.ragflow_server
```

프론트엔드 의존성 설치

```bash
cd web
pnpm i
```

프론트엔드 시작

```bash
pnpm dev
```

### 3. 백엔드 환경 시작

백엔드 의존성 설치

```bash
cd management/server
pip install -r requirements.txt
```

백엔드 시작
```bash
python app.py
```

프론트엔드 의존성 설치

```bash
cd management/web
pnpm i
```

프론트엔드 시작

```bash
pnpm dev
```

> [!NOTE]
> 소스 코드 배포 시 주의사항: MinerU 백엔드로 파싱하는 경우, MinerU 문서를 참조하여 모델 파일을 다운로드하고 LibreOffice를 설치한 후 환경 변수를 구성하여 pdf 이외의 파일 유형을 지원하도록 해야 합니다.

## 3. 백엔드 시스템 관리자 계정 및 비밀번호 수정

`docker\.env` 파일에서 다음 두 매개변수를 수정할 수 있습니다:
```bash
# 관리 시스템 사용자 이름 및 비밀번호
MANAGEMENT_ADMIN_USERNAME=admin
MANAGEMENT_ADMIN_PASSWORD=12345678
```

수정 후 컨테이너를 다시 시작합니다.

## 4. 이미지 액세스 IP 주소 수정

서버 배포 시, minio 액세스 주소를 서버 IP로 수정하여 사용자 단에서 이미지가 정상적으로 액세스되도록 할 수 있습니다.

`docker\.env` 파일에서 다음 매개변수를 수정할 수 있습니다:
```bash
# minio 파일 표시 시 IP 주소, 로컬 네트워크/공용 네트워크 액세스가 필요한 경우 로컬 네트워크/공용 네트워크 IP 주소로 수정할 수 있습니다
MINIO_VISIT_HOST=localhost
```

## 5. 제목 및 로고 교체

### 1. 백엔드 시스템 로고 및 제목 수정

1. 로고 수정

로고 파일은 `management\web\src\common\assets\images\layouts` 경로에 있으며, 세 개의 .png 파일에 해당합니다. 각각 홈페이지 로고와 로그인 페이지 로고(다른 테마에 따라 표시)입니다.

2. 제목 수정

제목은 `management\web\.env`에 있으며, `VITE_APP_TITLE` 매개변수를 수정합니다.

3. 워터마크 제거

관리 시스템 홈페이지에서 프로젝트 워터마크를 제거하려면 `management\web\src\layouts\components\Footer\index.vue` 파일을 수정할 수 있습니다.

4. dist 파일 패키징

`management/web` 경로로 이동하여 dist 파일을 패키징합니다:

```c
cd management/web
pnpm run build
```

5. 컨테이너에 들어가 기존 `/usr/share/nginx/html` 파일을 삭제합니다
```c
docker exec -it ragflowplus-management-frontend /bin/sh
rm -rf /usr/share/nginx/html
```

6. 패키징된 `dist` 파일을 컨테이너에 복사합니다
```c
docker cp dist ragflowplus-management-frontend:/usr/share/nginx/html
```

### 프론트엔드 시스템 로고 및 제목 수정

1. 로고 수정

로고 파일은 `web\public` 경로에 있으며, 로고 파일 형식은 svg입니다. 다른 파일 형식인 경우 해당 형식으로 변환해야 합니다.

2. 제목 수정

제목은 `web\src\conf.json`에 있으며, `appName` 매개변수를 수정합니다.

3. 로그인 페이지 제목 수정

로그인 페이지 제목을 수정하려면 `web\src\locales\zh.ts` 파일의 `title` 매개변수를 수정합니다.

4. dist 파일 패키징

`web` 경로로 이동하여 dist 파일을 패키징합니다:

```c
cd web
pnpm run build
```

5. 컨테이너에 들어가 기존 `/ragflow/web/dist` 파일을 삭제합니다
```c
docker exec -it ragflowplus-server /bin/sh
rm -rf /ragflow/web/dist
```

6. 패키징된 `dist` 파일을 컨테이너에 복사합니다
```c
docker cp dist ragflowplus-server:/ragflow/web/
```

수정 후, 브라우저에서 캐시를 지우고 새로고침하여 효과를 확인해야 합니다.