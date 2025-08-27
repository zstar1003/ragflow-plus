# Docker 이미지 구축

이 섹션에서는 이미지를 구축하고, 오프라인 상황에서 이미지의 내보내기와 로드를 구현하는 방법을 소개합니다.

## 1. 이미지 구축

프론트엔드 이미지 구축:

```bash
docker build -t zstar1003/ragflowplus:v0.5.0 .
```

백엔드 이미지 구축:

백엔드 이미지 구축 전에, 먼저 모델 파일을 `management` 폴더에 배치해야 합니다.

다운로드 주소: https://pan.baidu.com/s/1aUV7ohieL9byrbbmjfu3pg?pwd=8888 추출 코드: 8888 

```bash
cd management
docker-compose build
```


## 2. 이미지 업로드

이미지를 공개 저장소에 업로드하여 다른 사람이 다운로드할 수 있도록 합니다:

프론트엔드 이미지 업로드:

```bash
docker tag zstar1003/ragflowplus:v0.5.0 zstar1003/ragflowplus:v0.5.0
docker push zstar1003/ragflowplus:v0.5.0
```

백엔드 이미지 업로드:
```bash
docker tag zstar1003/ragflowplus-management-web:v0.5.0 zstar1003/ragflowplus-management-web:v0.5.0
docker tag zstar1003/ragflowplus-management-server:v0.5.0 zstar1003/ragflowplus-management-server:v0.5.0
docker push zstar1003/ragflowplus-management-web:v0.5.0
docker push zstar1003/ragflowplus-management-server:v0.5.0
```

## 3. 이미지 내보내기

모든 이미지 파일을 내보내어 오프라인 상황에서 이미지 마이그레이션 설치를 구현할 수 있습니다.

```bash
docker save -o ragflowplus-images.tar zstar1003/ragflowplus-management-web:v0.5.0 zstar1003/ragflowplus-management-server:v0.5.0 zstar1003/ragflowplus:v0.5.0 valkey/valkey:8 quay.io/minio/minio:RELEASE.2023-12-20T01-00-02Z mysql:8.0.39 elasticsearch:8.11.3
```

## 4. 오프라인 이미지 설치

오프라인 서버에서 이미지를 설치합니다

```bash
docker load -i ragflowplus-images.tar
```