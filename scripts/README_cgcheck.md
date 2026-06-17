# COSMOS Gate Preflight (cgcheck)
외부向 문서(은행/PI/공제회/로펌/테넌트) 작성 전, 반드시 `cgcheck` 먼저 실행.
`--format memo`로 뽑은 Gate Preflight 블록을 문서 최상단에 그대로 붙여넣는다.
Preflight 블록 없는 외부문서는 draft invalid로 간주한다.
BLOCK이면 작성 중단 후 조건 해소하고 재실행. 예외(Market Discovery 등) 쓸 땐 `--log-exception --approved-by "이름"` 필수 동반.
