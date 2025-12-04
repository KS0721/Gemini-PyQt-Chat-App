# 💬 [프로젝트명: Gemini AI Desktop Chat Client]

[![GitHub license](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/Framework-PyQt5-41C2C5?logo=qt)](https://www.qt.io/)
[![Google Gemini API](https://img.shields.io/badge/AI_Model-Gemini%202.5%20Flash-00A650?logo=google)](https://ai.google.dev/)

> **PyQt5 GUI 환경에서 Gemini 2.5 Flash 모델을 연동하여 개발한 데스크톱 기반 대화형 AI 클라이언트입니다.**
>
> **핵심 기술:** Python, PyQt5 (GUI), Gemini API (대화 이력 관리)

---

## 💡 프로젝트 개요 및 개발 목표

본 프로젝트는 **GUI 개발 역량**과 **AI 서비스 연동 능력**을 동시에 증명하기 위해 개발되었습니다. 사용자가 쉽게 접근할 수 있는 데스크톱 환경에서 대화형 AI 서비스를 제공하는 것이 목표입니다.

* **문제 해결:** 터미널 환경이 아닌, 직관적인 **데스크톱 GUI**를 통해 Gemini AI를 사용할 수 있도록 합니다.
* **기술적 도전:** **PyQt5**의 시그널/슬롯 메커니즘을 활용하여 사용자 인터페이스와 백엔드 로직(API 호출)을 **효율적으로 분리**했습니다.

## 🎯 주요 기능 및 구현 특징

### 1. **API 키 안전 관리 (보안 강화)**
* **구현:** **`python-dotenv`** 라이브러리를 사용하여 API 키를 `.env` 파일에서 로드하도록 하여, 소스 코드에 키가 노출되는 위험을 완벽히 방지했습니다.

### 2. **실시간 대화 이력 유지 (Chat Session)**
* **구현:** `google-genai` 라이브러리의 **Chat Session** 기능을 사용하여, 이전 대화 내용을 기억하고 문맥에 맞는 답변을 생성합니다.

### 3. UI/UX 구현 및 분리
* **기술:** **Qt Designer**를 사용하여 UI 레이아웃(`gemini.ui`)을 설계하고, 파이썬 코드(`gemini.py`)에서 `loadUi`를 통해 로드하는 **모듈화된 방식**을 적용했습니다.

## 🛠️ 기술 스택 및 환경

| 분류 | 기술 | 역할 및 사용 이유 |
| :--- | :--- | :--- |
| **GUI** | **PyQt5** | Python에서 가장 강력하고 유연한 데스크톱 GUI 프레임워크 |
| **환경 변수** | **python-dotenv** | `.env` 파일을 활용한 API 키의 안전한 관리 |
| **AI 모델** | **Gemini 2.5 Flash** | 빠른 응답 속도와 우수한 범용성을 가진 경량 LLM 모델 |
| **디자인 툴** | **Qt Designer** | UI 디자인과 로직 코드의 명확한 분리 (Developer Best Practice) |

---

## ⚙️ 설치 및 실행 방법

이 프로젝트는 `gemini.py`, `gemini.ui`, 그리고 `.env` 파일이 **모두 같은 디렉터리**에 있어야 실행됩니다.

### 1. 라이브러리 설치

> 다음 명령어를 터미널에 입력하여 필요한 라이브러리를 설치합니다.
> `pip install pyqt5 google-genai python-dotenv`

### 2. `.env` 파일 생성 및 키 설정 (필수)

> 프로젝트 루트 디렉터리에 **`.env`** 파일을 생성하고, 발급받은 **Gemini API 키**를 다음과 같이 설정합니다.
>
> **파일명:** `.env`
> `GEMINI_API_KEY="[발급받은_API_키를_여기에_입력]"`

### 3. 애플리케이션 실행

> `gemini.py` 파일이 있는 위치에서 다음 명령어를 실행합니다.
> `python gemini.py`

---

## 🖼️ 실행 화면 (Screenshots)

[여기에 프로젝트의 실행 화면 스크린샷이나 GIF 이미지를 첨부하세요.]

```markdown
![챗봇 실행 화면 예시](assets/screenshot.png)
