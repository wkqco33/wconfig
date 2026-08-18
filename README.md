# wconfig

`wconfig`는 Go의 Viper에서 영감을 받은 Python용 계층형 설정 로더입니다. 코드 기본값, 설정 파일, `.env`, 환경변수를 예측 가능한 우선순위로 병합합니다.

`환경변수 > .env > 파일 > 코드 기본값`

## 주요 기능

- JSON, TOML, YAML, `.env`, 환경변수에서 설정 로드
- 로더 호출 순서와 무관하게 일관된 계층형 우선순위 병합
- `database.host` 같은 dotted key 방식으로 값 조회
- 병합된 설정을 dataclass 및 타입 컨테이너로 디코딩
- `get_source()`를 통한 설정 값의 출처(source provenance) 추적
- 대소문자 및 하이픈/언더스코어(`-` / `_`) 구분 없는 유연한 키 정규화

## 설치

```bash
pip install wpyconf
```

> **참고**: PyPI 배포 패키지 이름은 `wpyconf`이며, 코드 내 import 경로는 하위 호환성을 위해 `wconfig`를 사용합니다.

## 빠른 시작

```python
from dataclasses import dataclass

from wconfig import Config


@dataclass
class DatabaseSettings:
    host: str
    port: int
    enabled: bool


config = (
    Config(env_prefix="APP")
    .set_defaults(
        {
            "database": {
                "host": "localhost",
                "port": 5432,
                "enabled": False,
            }
        }
    )
    .load_file("config.yaml")
    .load_dotenv(".env")
    .load_env()
)

db = config.decode(DatabaseSettings, key="database")
print(db.host)
print(config.get("database.port"))
```

## 환경변수 키 매핑

`env_prefix="APP"`이고 기본 구분자를 사용할 때의 예시는 다음과 같습니다.

- `APP_DATABASE__HOST` -> `database.host`
- `APP_DATABASE__PORT` -> `database.port`
- `APP_FEATURE_FLAGS__BETA` -> `feature_flags.beta`

기본 환경변수 관련 설정은 다음과 같습니다.

- prefix separator: `_`
- nested delimiter: `__`
- lookup delimiter: `.`

## 공개 API

### `Config`

- `set_defaults(mapping)`: 코드 기본값 등록
- `load_file(path, *, name=None, format=None)`: JSON, TOML, YAML 파일 로드 (확장자가 없는 파일은 `format="yaml"` 등으로 지정 가능)
- `load_files(*paths)`: 여러 설정 파일 로드
- `load_dotenv(path=".env")`: dotenv 파일 로드
- `load_env(environ=None)`: 실제 환경변수 또는 전달한 매핑 로드
- `get(key, default=None)`: dotted path로 값 조회
- `require(key)` / `config[key]`: 반드시 필요한 값을 조회하고 없으면 `MissingConfigKeyError` 발생
- `has(key)` / `key in config`: 키 존재 여부 확인
- `get_source(key)`: 최종 값이 어느 source에서 왔는지 조회
- `as_dict()`: 병합된 설정을 일반 딕셔너리로 내보내기
- `decode(type, key=None)`: 전체 또는 일부 설정을 dataclass, Enum, Path, Sequence/Mapping 등으로 디코딩 (환경변수 문자열 리스트/JSON 파싱 지원)
- `sources()`: 등록된 모든 설정 소스 정보 목록 조회

### `load_config(...)`

간단한 구성에서는 `load_config()`로 `Config` 인스턴스를 한 번에 만들 수 있습니다.

```python
from wconfig import load_config

config = load_config(
    defaults={"api": {"timeout": 30}},
    files=("config.yaml",),
    dotenv=".env",
    env_prefix="APP",
)
```

`load_config()`는 `env_prefix` 또는 `environ`을 지정한 경우에만 환경변수를 자동으로 읽습니다. prefix 없이 전체 프로세스 환경변수를 읽으려면 `env=True`를 명시해야 합니다.

## 동작 규칙

- 모든 key는 내부적으로 소문자 + `_` 기준으로 정규화됩니다.
- 따라서 `service-config.api-key`, `service_config.api_key`, `SERVICE_CONFIG.API_KEY`는 같은 key로 취급됩니다.
- `env_prefix="APP"`이면 `APP_`로 시작하는 환경변수만 읽습니다.
- 같은 우선순위 source는 나중에 로드한 값이 앞선 값을 덮어씁니다.

## source 추적

어떤 값이 어디에서 왔는지 확인하려면 `get_source()`를 사용할 수 있습니다.

```python
source = config.get_source("database.host")
print(source.value)        # 'localhost'
print(source.source.kind)  # 'defaults'
print(source.source.name)  # 'defaults'
```

## 지원 파일 형식

- `.json`
- `.toml`
- `.yaml`
- `.yml`

## 개발 및 테스트

테스트 실행:

```bash
uv run --group dev pytest
```

패키지 빌드:

```bash
uv build
```

## 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)에 따라 배포됩니다.
