# AGENTS

wconfig 프로젝트의 개발 가이드 및 에이전트 작업 지침입니다.

## 아키텍처 및 핵심 원칙

1. **설정 우선순위 (Merge Precedence)**
   - `환경변수 (Environment) > .env > 설정 파일 (File) > 코드 기본값 (Defaults)`
   - 동일 우선순위 내에서는 나중에 로드된 소스가 이전 값을 덮어씁니다.
2. **키 정규화 (Key Normalization)**
   - 모든 설정 키는 내부적으로 소문자 및 언더스코어(`_`) 기준으로 정규화됩니다.
   - 예: `service-config.api-key`, `service_config.api_key`, `SERVICE_CONFIG.API_KEY`는 동일한 키로 처리됩니다.
3. **타입 안전성 및 디코딩**
   - dataclass, primitive 타입, Sequence, Mapping, Union, Optional, Literal 등의 타입 디코딩을 지원합니다.
   - 파싱/디코딩 실패 시 구체적인 경로와 함께 명시적인 예외(`ConfigDecodeError` 등)를 발생시킵니다.

## 프로젝트 구조

```
wconfig/
├── src/wconfig/
│   ├── __init__.py       # 공개 API export
│   ├── config.py         # Config 클래스 및 load_config 함수
│   ├── errors.py         # 패키지 예외 정의
│   ├── _parsers.py       # JSON, TOML, YAML, .env 파일 파서
│   ├── _decode.py        # dataclass 및 타입 디코딩 로직
│   └── _utils.py         # 딕셔너리 deep merge 및 키 정규화 유틸리티
└── tests/
    ├── test_public_api.py        # 공개 API 테스트
    ├── test_merge_precedence.py  # 설정 병합 및 우선순위 테스트
    ├── test_file_loading.py      # JSON, TOML, YAML 파일 로딩 테스트
    ├── test_dotenv_loading.py    # .env 및 환경변수 로딩 테스트
    └── test_decode.py            # 타입 디코딩 및 검증 테스트
```

## 개발 및 테스트 워크플로 (TDD)

### 기본 원칙

- **기능별 테스트 분리**: 테스트는 관련 동작 영역(`test_decode.py`, `test_file_loading.py` 등)에 배치합니다.
- **공개 API 중심 검증**: 내부 헬퍼보다는 `Config`, `load_config` 등의 공개 인터페이스를 통해 동작을 검증합니다.
- **명시적 예외 검증**: 에러 상황에서는 정확한 패키지 예외 타입 및 에러 메시지 경로를 검증합니다.

### 주요 명령어

단일 테스트 파일 실행:
```bash
uv run --group dev pytest tests/test_public_api.py
```

특정 테스트 케이스 실행:
```bash
uv run --group dev pytest tests/test_decode.py -k literal
```

전체 테스트 스위트 실행:
```bash
uv run --group dev pytest
```

패키지 빌드:
```bash
uv build
```
