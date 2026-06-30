"""
data-pipeline/conftest.py

로컬 테스트 부트스트랩: 레포 루트를 sys.path 에 추가해 모노레포 공용 패키지
shared/ 를 data-pipeline 안에서 import 할 수 있게 한다 (`from shared.ontology import Deal`).

- 프로덕션 컨테이너에서는 Dockerfile 이 shared/ 를 /app/shared 로 복사하므로 불필요.
- data-pipeline 디렉토리는 cwd/pytest rootdir 로 sys.path 에 남아 있어
  기존 `from db import get_conn` 패턴은 그대로 동작한다.
"""
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
