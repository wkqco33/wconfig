# 변경 이력 (CHANGE_LOG)

## [0.2.1] - 2026-08-16

### 추가
- JSON, TOML, YAML, `.env`, 환경변수 설정 로딩 지원
- 설정 source별 우선순위 병합 및 `get_source()` provenance 조회 지원
- dataclass, 컨테이너, Union, Optional, Literal 타입 디코딩 지원
- 공개 API와 기능 영역별 테스트 구성
- 공개 PyPI 배포를 위한 패키지 메타데이터와 MIT 라이선스 추가

### 개선
- 설정 키 정규화 및 중첩 환경변수 매핑 동작 문서화
- 파일 형식 및 `.env` 파싱 오류 메시지 명확화
- 엄격한 Pyright 타입 검사를 유지하면서 동적 설정 경계의 경고 정책 명시

## [0.1.1] - 2026-07-16

### 추가
- `typing.Literal` 타입 디코딩 지원
  - 설정 파일이나 환경 변수 등에서 읽어온 값을 `Literal[...]` 정의와 비교하여 검증하는 로직 추가
  - `Literal`에 정의된 허용 값 범위를 벗어날 경우 `ConfigDecodeError` 발생
- `Literal` 디코딩 기능을 검증하는 테스트 케이스 추가 (`tests/test_config.py`)

### 버그 수정
- `Literal` 타입을 사용할 때 `TypeError: Subscripted generics cannot be used with class and instance checks` 에러가 발생하던 현상 수정
