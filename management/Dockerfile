# Use the official sglang image
FROM zstar1003/ragflowplus-management-server:v0.5.0

WORKDIR /app
# 백엔드 코드 복사
COPY server /app

# huggingface 캐시 디렉토리 생성 및 모델 복사
RUN mkdir -p /root/.cache/huggingface/hub/
# Install mineru latest
RUN python3 -m pip install -U 'mineru[core]' --break-system-packages

# # Download models and update the configuration file
RUN /bin/bash -c "mineru-models-download -s huggingface -m all"

RUN ["python", "-c", "import nltk; nltk.download('punkt_tab'); nltk.download('wordnet')" ]
# 백엔드 포트 노출
EXPOSE 5000
CMD ["python", "app.py"]
