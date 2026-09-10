import html
import os
import re
import sys
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://open.neis.go.kr/hub"
KST = ZoneInfo("Asia/Seoul")
WEEKDAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


class NeisError(RuntimeError):
    pass


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"환경변수 {name}가 설정되지 않았습니다.")
    return value


def neis_get(dataset: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    query = {"KEY": os.getenv("NEIS_API_KEY", "sample"), "Type": "json", "pIndex": 1, "pSize": 1000, **params}
    try:
        response = requests.get(f"{BASE_URL}/{dataset}", params=query, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise NeisError(f"NEIS API 요청 실패: {exc}") from exc

    if "RESULT" in payload:
        result = payload["RESULT"]
        raise NeisError(f"NEIS API 오류: {result.get('CODE', '')} {result.get('MESSAGE', '')}")
    rows = []
    for block in payload.get(dataset, []):
        rows.extend(block.get("row", []))
    return rows


def find_school(name: str) -> tuple[str, str, str]:
    rows = neis_get("schoolInfo", {"SCHUL_NM": name, "SCHUL_KND_SC_NM": "고등학교"})
    exact = [r for r in rows if r.get("SCHUL_NM", "").strip() == name]
    row = (exact or rows)[0] if (exact or rows) else None
    if not row:
        raise NeisError(f"학교를 찾지 못했습니다: {name}")
    return row["ATPT_OFCDC_SC_CODE"], row["SD_SCHUL_CODE"], row["SCHUL_NM"]


def clean_subject(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip() or "(과목 없음)"


def get_timetable(office: str, school_code: str, date_text: str, grade: str, class_num: str) -> dict[int, str]:
    rows = neis_get("hisTimetable", {"ATPT_OFCDC_SC_CODE": office, "SD_SCHUL_CODE": school_code, "ALL_TI_YMD": date_text, "GRADE": grade, "CLASS_NM": class_num})
    result: dict[int, str] = {}
    for row in rows:
        try:
            period = int(str(row.get("PERIO", "")).strip())
        except ValueError:
            continue
        subject = clean_subject(row.get("ITRT_CNTNT", ""))
        if period not in result or result[period] == "(과목 없음)":
            result[period] = subject
    return dict(sorted(result.items()))


def send_discord(webhook: str, school: str, grade: str, class_num: str, today: datetime, timetable: dict[int, str]) -> None:
    date_label = f"{today.month}월 {today.day}일 {WEEKDAYS[today.weekday()]} 시간표"
    lines = [f"{period}교시 | {subject}" for period, subject in timetable.items()]
    description = "\n".join(lines) if lines else "오늘은 등록된 시간표가 없습니다."
    payload = {"embeds": [{"title": f"📚 {date_label}", "description": description, "color": 3447003, "fields": [{"name": "학교", "value": school, "inline": False}, {"name": "학년/반", "value": f"{grade}학년 {class_num}반", "inline": True}], "footer": {"text": "NEIS Open API · KST"}}]}
    try:
        response = requests.post(webhook, json=payload, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Discord 웹훅 전송 실패: {exc}") from exc


def main() -> int:
    try:
        today = datetime.now(KST)
        if today.weekday() >= 5:
            print("주말이므로 전송하지 않습니다.")
            return 0
        school_name = env_required("SCHOOL_NAME")
        grade = env_required("GRADE")
        class_num = env_required("CLASS_NUM")
        webhook = env_required("DISCORD_WEBHOOK_URL")
        office, school_code, official_name = find_school(school_name)
        timetable = get_timetable(office, school_code, today.strftime("%Y%m%d"), grade, class_num)
        send_discord(webhook, official_name, grade, class_num, today, timetable)
        print(f"전송 완료: {official_name} / {grade}학년 {class_num}반 / {len(timetable)}개 교시")
        return 0
    except (ValueError, NeisError, RuntimeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
