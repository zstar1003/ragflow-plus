# 자주 묻는 질문 (FAQ)

## 질문 1: RagflowPlus를 어떻게 배포하나요?

**답변:** Docker Compose 또는 소스 코드로 배포할 수 있습니다.

- **Docker Compose (권장):**
  - GPU 버전: `docker compose -f docker/docker-compose_gpu.yml up -d`
  - CPU 버전: `docker compose -f docker/docker-compose.yml up -d`
- **소스 코드 실행:** "빠른 시작" 부분을 참고하세요.

## 질문 2: RagflowPlus와 Ragflow를 동시에 사용할 수 있나요?

**답변:** RagflowPlus는 독립적인 프론트엔드 및 백엔드 시스템을 채택하고 있으며, 데이터는 Ragflow와 상호 운용되지만 동시에 사용하는 것은 권장하지 않습니다. 동시에 사용해야 하는 경우, 포트 수정/시작 방식 전환을 통해 구현할 수 있지만, 일부 인터페이스 불일치로 인한 위험은 감수해야 합니다.

## 질문 3: 백엔드 파싱 시 오류 발생: 버킷이 존재하지 않습니다:f62a03f61fdd11f0b1301a12a4193bf3.

**답변:** 이 문제는 파싱할 파일이 Ragflow의 원래 파일 시스템에서 업로드되었기 때문입니다. RagflowPlus는 파일 업로드 관련 인터페이스를 재구성했으므로, 새 파일을 파싱할 때는 RagflowPlus의 백엔드 관리 시스템을 통해 업로드하는 것을 권장합니다.

## 질문 4: 지원되는 문서 유형은 무엇인가요?

**답변:** 일반적인 문서 유형은 모두 지원됩니다: pdf, word, ppt, excel, txt, md, html, jpg, png, bmp.

## 질문 5: Docker 이미지가 ARM 플랫폼을 지원하나요?

**답변:** Ragflow가 ARM 플랫폼용 이미지를 유지보수하지 않는 점을 감안하여, RagflowPlus도 ARM 플랫폼용 이미지를 출시하거나 유지보수할 계획이 없습니다.

## 질문 6: ollama로 모델을 배포할 수 있나요?

**답변:** 가능합니다. ollama 및 온라인 API(실리콘 기반 유동 플랫폼)와 호환됩니다.

## 질문 7: 포트 충돌 오류는 어떻게 해결하나요?

```bash
(HTTP code 500) server error - Ports are not available: exposing port TCP 0.0.0.0:5455 -> 0.0.0.0:0: listen tcp 0.0.0.0:5455: bind: An attempt was made to access a socket in a way forbidden by its access permissions.s
```

**답변:** 이 문제는 Windows 네트워크 주소 변환 서비스(WinNAT) 때문입니다. 이 서비스는 Hyper-V, WSL2 또는 Docker와 같은 가상화 기술에 네트워크 주소 변환(NAT) 기능을 제공합니다. WinNAT는 실행 시 가상 네트워크에서 사용할 TCP/UDP 포트의 일부를 무작위로 예약합니다. 이러한 예약된 포트는 애플리케이션에 필요한 포트와 충돌할 수 있습니다.

다음 명령을 통해 서비스를 중지하고 예약된 포트를 해제하여 사용자가 일시적으로 사용할 수 있도록 할 수 있습니다.
```bash
net stop winnat
netsh int ipv4 add excludedportrange protocol=tcp startport=5455 numberofports=1
net start winnat
```

## 질문 8: MinerU GPU 가속이 첫 번째 그래픽 카드만 호출하는 것 같은데, 다른 그래픽 카드를 지정하려면 어떻게 해야 하나요?

**답변:** MinerU 1.x 자체는 특정 그래픽 카드를 지정할 수 없으며, 다중 그래픽 카드 배포를 지원하지 않습니다. 다음 방법을 통해 백엔드 컨테이너가 사용할 수 있는 그래픽 카드 ID를 제한할 수 있습니다.

`docker\docker-compose_gpu.yml` 수정:

```bash
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: [gpu]
          device_ids: ["2"]  # 인덱스 번호를 사용하여 ID가 2인 그래픽 카드 지정
```

## 질문 9: 로그에 경고 발생: RedisDB.queue_info rag_flow_svr_queue got exception:no such key

**답변:** Ragflow 네이티브 파서의 하트비트 트리거 문제이며, 정상적인 사용에는 영향을 미치지 않으므로 무시해도 됩니다. 공식 답변은 다음을 참조하세요: https://github.com/infiniflow/ragflow/issues/6700

## 질문 10: ollama를 추가할 때 왜 연결할 수 없나요?

**답변:** ollama는 모든 네트워크 인터페이스에 대해 개방되도록 미리 설정해야 합니다.

구성 파일 수정:
```bash
vim /etc/systemd/system/ollama.service
```

[Service] 아래에 추가:

```bash
Environment="OLLAMA_HOST=0.0.0.0"
```

구성 파일을 다시 로드하고 ollama를 다시 시작합니다.

```bash
systemctl daemon-reload
systemctl restart ollama
```

## 질문 11: 어떤 ragflow 및 MinerU 버전을 기반으로 2차 개발되었나요?

**답변:** ragflow v0.17.2 및 MinerU v1.3.12 버전을 기반으로 2차 개발되었습니다.

## 질문 12: 업스트림 콘텐츠 업데이트에 따라 계속해서 새 버전을 업데이트할 예정인가요?

**답변:** 아니요, 비즈니스 요구 사항이 이미 충족된 상황에서 버전을 업그레이드하는 것은 실질적인 의미가 없습니다.

--- 



*더 궁금한 점이 있으면 GitHub에 Issue를 제출하세요.*