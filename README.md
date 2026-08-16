# wconfig

`wconfig`는 Go의 Viper에서 영감을 받은 Python용 계층형 설정 로더입니다. 코드 기본값, 설정 파일, `.env`, 환경변수를 예측 가능한 우선순위로 병합합니다.

`환경변수 > .env > 파일 > 코드 기본값`

## 주요 기능

- JSON, TOML, YAML, `.env`, 환경변수에서 설정 로드
- 로더 호출 순서와 무관하게 중첩 설정을 일관된 규칙으로 병합
- `database.host` 같은 dotted key 방식으로 값 조회
- 병합된 설정을 dataclass로 디코딩
- 공개 PyPI에 배포해 일반 Python 패키지처럼 설치 가능

## 설치

```bash
pip install wpyconf
```

## 빠른 시작

배포 이름은 `wpyconf`이며, Python import 경로는 하위 호환성을 위해 `wconfig`를 유지합니다.

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
- `load_file(path)`: JSON, TOML, YAML 파일 하나 로드
- `load_files(*paths)`: 여러 설정 파일 로드
- `load_dotenv(path=".env")`: dotenv 파일 로드
- `load_env(environ=None)`: 실제 환경변수 또는 전달한 매핑 로드
- `get(key, default=None)`: dotted path로 값 조회
- `get_source(key)`: 최종 값이 어느 source에서 왔는지 조회
- `require(key)`: 반드시 필요한 값을 조회하고 없으면 `MissingConfigKeyError` 발생
- `has(key)`: 키 존재 여부 확인
- `as_dict()`: 병합된 설정을 일반 딕셔너리로 내보내기
- `decode(type, key=None)`: 전체 또는 일부 설정을 dataclass나 타입 지정 컨테이너로 디코딩

### `load_config(...)`

간단한 구성에서는 `load_config()`로 `Config` 인스턴스를 한 번에 만들 수 있습니다.

## 동작 규칙

- 모든 key는 내부적으로 소문자 + `_` 기준으로 정규화됩니다.
- 따라서 `service-config.api-key`, `service_config.api_key`, `SERVICE_CONFIG.API_KEY`는 같은 key로 취급됩니다.
- `env_prefix="APP"`이면 `APP_`로 시작하는 환경변수만 읽습니다.
- 같은 우선순위 source는 나중에 로드한 값이 앞선 값을 덮어씁니다.

## source 추적

어떤 값이 어디에서 왔는지 확인하려면 `get_source()`를 사용할 수 있습니다.

```python
source = config.get_source("database.host")
print(source.value)
print(source.source.kind)
print(source.source.name)
```

## 지원 파일 형식

- `.json`
- `.toml`
- `.yaml`
- `.yml`

YAML 지원은 `PyYAML`을 사용합니다.

## 패키지 빌드

```bash
uv build
```

빌드 결과물은 `dist/` 디렉터리에 생성됩니다.

## 공개 PyPI로 배포

테스트 업로드로 먼저 검증하려면 TestPyPI를 사용할 수 있습니다.

```bash
export UV_PUBLISH_TOKEN=pypi-...
uv publish --index testpypi
```

공개 PyPI에 실제 배포할 때는 다음 명령을 사용합니다.

```bash
export UV_PUBLISH_TOKEN=pypi-...
uv publish
```

배포 전에 패키지를 다시 빌드하려면 다음 순서를 사용합니다.

```bash
rm -rf dist
uv build
export UV_PUBLISH_TOKEN=pypi-...
uv publish
```

`UV_PUBLISH_TOKEN`에는 PyPI 또는 TestPyPI에서 발급받은 API token을 설정합니다.

## 개발

테스트 실행:

```bash
uv run --group dev pytest
```
