<div align="center">
  <img src="docs/images/ragflow-plus.png" width="400" alt="Ragflow-Plus">
</div>

<div align="center">
  <a href="https://github.com/zstar1003/ragflow-plus/stargazers"><img src="https://img.shields.io/github/stars/zstar1003/ragflow-plus?style=social" alt="stars"></a>
  <img src="https://img.shields.io/badge/version-0.5.0-blue" alt="version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL3.0-green" alt="license"></a>
  <a href="https://hub.docker.com/r/zstar1003/ragflowplus/tags"><img src="https://img.shields.io/docker/pulls/zstar1003/ragflowplus" alt="docker pulls"></a>

  <h4>
    <a href="README.md">🇨🇳 중국어</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 영어</a>
    <span> | </span>
    <a href="README_CN.md">🇨🇳 중국어</a>
  </h4>
</div>

---

## 🌟 소개

**Ragflow-Plus**는 **Ragflow**를 기반으로 한 2차 개발 프로젝트로, 실제 애플리케이션의 일부 문제를 해결하는 것을 목표로 합니다.
주요 기능은 다음과 같습니다:

- **관리 모드**
  사용자 관리, 팀 관리, 구성 관리, 파일 관리 및 지식 베이스 관리를 지원하는 추가 관리자 패널입니다.
- **권한 회수**
  프론트엔드 시스템은 단순화된 인터페이스를 위해 사용자 권한을 제한합니다.
- **향상된 파싱**
  DeepDoc 알고리즘을 MinerU로 대체하여 이미지 파싱을 포함한 더 나은 문서 파싱 결과를 제공합니다.
- **텍스트-이미지 출력**
  모델 응답에서 참조된 텍스트 블록에 연결된 관련 이미지를 표시하는 것을 지원합니다.
- **문서 작성 모드**
  완전히 새로운 문서 모드 인터랙티브 경험을 제공합니다.

**요약:** Ragflow-Plus는 중국어 애플리케이션 시나리오를 위한 Ragflow의 "산업별 솔루션"입니다.

## 📥 사용법

비디오 데모 및 튜토리얼:

[![Ragflow-Plus 소개 및 사용자 가이드](https://i0.hdslb.com/bfs/archive/f7d8da4a112431af523bfb64043fe81da7dad8ee.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1UJLezaEEE)

프로젝트 문서: [xdxsb.top/ragflow-plus](https://xdxsb.top/ragflow-plus)

Docker로 빠른 시작:
```bash
docker compose -f docker/docker-compose.yml up -d
````

## ❓ 자주 묻는 질문 (FAQ)

* 일반적인 문제는 [FAQ](docs/question/README.md)를 확인하거나 GitHub 이슈 섹션을 검색하세요.
* 해결되지 않으면 [DeepWiki](https://deepwiki.com/zstar1003/ragflow-plus) 또는 [zread](https://zread.ai/zstar1003/ragflow-plus)를 사용하여 AI 어시스턴트와 상호작용해 보세요. 대부분의 일반적인 문제를 해결할 수 있습니다.
* 문제가 지속되면 GitHub 이슈를 제출하세요. AI 어시스턴트가 자동으로 응답할 것입니다.

## 🛠️ 기여 방법

1.  이 GitHub 저장소를 **포크(Fork)** 하세요.
2.  로컬에 포크한 저장소를 복제하세요:

   ```bash
   git clone git@github.com:<your-username>/ragflow-plus.git
   ```
3.  새 브랜치를 만드세요:

   ```bash
   git checkout -b my-branch
   ```
4.  설명적인 메시지와 함께 커밋하세요:

   ```bash
   git commit -m '명확하고 설명적인 커밋 메시지를 제공하세요'
   ```
5.  변경 사항을 GitHub에 푸시하세요:

   ```bash
   git push origin my-branch
   ```
6.  PR을 제출하고 검토를 기다리세요.

## 🚀 감사 인사

이 프로젝트는 다음 오픈 소스 프로젝트를 기반으로 합니다:

*   [ragflow](https://github.com/infiniflow/ragflow)
*   [v3-admin-vite](https://github.com/un-pany/v3-admin-vite)
*   [minerU](https://github.com/opendatalab/MinerU)

모든 기여자분들께 감사드립니다:

<a href="https://github.com/zstar1003/ragflow-plus/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zstar1003/ragflow-plus" />
</a>

## 📜 라이선스 및 사용 제한

1.  **AGPLv3 라이선스**
    이 프로젝트에는 제3자 AGPLv3 코드가 포함되어 있으므로 모든 AGPLv3 조건을 준수해야 합니다:
    *   모든 **파생 저작물**(수정 또는 결합된 코드 포함)은 AGPLv3 라이선스를 유지하고 오픈 소스로 공개해야 합니다.
    *   **네트워크 서비스**를 통해 제공되는 경우, 사용자는 해당 소스 코드를 얻을 권리가 있습니다.

2.  **상업적 사용**
    *   **허용**: AGPLv3는 SaaS 및 기업 배포를 포함한 상업적 사용을 허용합니다.
    *   **수정되지 않은 코드**: 수정을 하지 않더라도 AGPLv3를 준수해야 합니다:
        *   (변경되지 않았더라도) 전체 소스 코드를 제공해야 합니다.
        *   네트워크 서비스로 제공되는 경우, 사용자가 소스 코드를 다운로드할 수 있도록 허용해야 합니다(AGPLv3 섹션 13).
    *   **비공개 소스 상업적 사용 금지**: 비공개 소스 상업적 사용(수정된 코드를 공개하지 않음)은 상위 AGPLv3 작성자를 포함한 모든 저작권 소유자의 서면 허가가 필요합니다.

3.  **면책 조항**
    이 프로젝트는 어떠한 보증도 없이 제공됩니다. 규정 준수에 대한 책임은 사용자에게 있습니다. 법률 자문이 필요한 경우 전문 변호사와 상담하세요.

## ✨ 스타 히스토리

![Stargazers over time](https://starchart.cc/zstar1003/ragflow-plus.svg)