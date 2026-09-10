# 학교 시간표 Discord 자동 전송

대한민국 NEIS Open API에서 오늘의 고등학교 시간표를 조회해 Discord Embed 웹훅으로 보냅니다. 한국 시간(Asia/Seoul)을 사용하며 토·일요일에는 전송하지 않습니다. GitHub Actions는 평일 오전 8시 10분과 오후 1시 10분(KST)에 실행됩니다.

## 1. GitHub에 프로젝트 올리기

PowerShell에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```powershell
git init
git add .
git commit -m "Add NEIS timetable Discord bot"
gh repo create school-timetable-discord --public --source=. --remote=origin --push
```

이미 저장소가 있다면 `git remote add origin 저장소주소` 후 `git push -u origin main`을 사용하세요.

## 2. Discord 웹훅 만들기

Discord 서버에서 대상 채널의 **채널 편집 → 연동 → 웹후크 → 새 웹후크 → 웹후크 URL 복사**를 선택합니다. URL은 비밀번호처럼 취급하세요.

## 3. GitHub Secret 등록

저장소의 **Settings → Secrets and variables → Actions → New repository secret**에서 이름을 `DISCORD_WEBHOOK_URL`로 하고 복사한 URL을 값으로 저장합니다.

NEIS 공식 키를 발급받았다면 같은 곳에 `NEIS_API_KEY`도 추가하세요. NEIS는 키가 없는 호출에서 `sample` 키를 시도하지만, 사용량이나 정책에 따라 동작하지 않을 수 있으므로 정식 키 사용을 권장합니다. 키는 [NEIS Open API](https://open.neis.go.kr/portal/guide/actKeyPage.do)에서 발급받을 수 있습니다.

## 4. 학교명/학년/반 설정

필수 설정은 4개입니다. `SCHOOL_NAME`, `GRADE`, `CLASS_NUM`은 Repository Variables 또는 Repository Secrets 중 한 곳에 등록할 수 있습니다. Secrets로 등록했다면 **Settings → Secrets and variables → Actions → New repository secret**, Variables로 등록했다면 **Variables → New repository variable**을 사용하세요.

```text
SCHOOL_NAME=학교의 공식 명칭
GRADE=2
CLASS_NUM=3
```

나머지 1개인 `DISCORD_WEBHOOK_URL`은 반드시 Secrets에 등록합니다. `NEIS_API_KEY`는 선택 항목이지만 안정적인 사용을 위해 권장합니다.

알림을 받을 Discord 사용자 ID를 `DISCORD_USER_ID`라는 Repository Secret으로 추가하면 메시지 앞에 해당 사용자를 멘션합니다. 사용자 ID는 Discord 개발자 모드에서 사용자 우클릭 → **사용자 ID 복사**로 얻습니다. 입력할 때 `<@...>`가 아니라 숫자 ID만 넣으세요. 생략하면 멘션 없이 전송됩니다.

학교명은 NEIS에 등록된 이름과 가깝게 입력하세요. 코드는 학교명을 검색해 교육청 코드와 학교 코드를 자동으로 가져옵니다.

## 5. GitHub Actions 활성화

저장소의 **Actions** 탭에서 workflow를 활성화합니다. 스케줄은 UTC 기준 `22:30`으로 설정되어 한국 시간 평일 오전 7시 30분에 실행됩니다. GitHub Actions의 스케줄은 저장소 상태나 지연에 따라 약간 늦어질 수 있습니다.

## 6. 테스트 실행

Actions 탭에서 **Send school timetable → Run workflow**를 눌러 수동 실행합니다. 로컬에서는 다음처럼 합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# .env에 실제 학교명, 학년, 반, 웹훅을 입력
python main.py
```

## 7. 오류 확인

- `환경변수 ...` 오류: Repository Variables 또는 Secret 이름이 정확한지 확인합니다.
- `학교를 찾지 못했습니다`: NEIS 공식 학교명, 띄어쓰기, 고등학교 여부를 확인합니다.
- `NEIS API 오류/요청 실패`: `NEIS_API_KEY` 유효성, API 응답 상태, 일시적 장애를 확인합니다.
- Discord 전송 실패: 웹훅 URL이 만료·삭제되지 않았는지, 채널 권한과 Secret 값에 공백이 없는지 확인합니다.
- 시간표가 없는 날: 프로그램은 정상 종료하고 “오늘은 등록된 시간표가 없습니다.” Embed를 전송합니다.

과목명에 포함된 HTML 태그는 자동 제거하며, 같은 교시 데이터가 여러 개면 교시 번호 기준으로 하나만 정리합니다.
