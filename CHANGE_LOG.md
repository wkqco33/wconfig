# 변경 이력 (CHANGE_LOG)

## [0.1.1] - 2026-07-16

### 추가
- `typing.Literal` 타입 디코딩 지원
  - 설정 파일이나 환경 변수 등에서 읽어온 값을 `Literal[...]` 정의와 비교하여 검증하는 로직 추가
  - `Literal`에 정의된 허용 값 범위를 벗어날 경우 `ConfigDecodeError` 발생
- `Literal` 디코딩 기능을 검증하는 테스트 케이스 추가 (`tests/test_config.py`)

### 버그 수정
- `Literal` 타입을 사용할 때 `TypeError: Subscripted generics cannot be used with class and instance checks` 에러가 발생하던 현상 수정
