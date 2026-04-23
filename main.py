from datetime import date
from dotenv import load_dotenv
import os
from dataclasses import dataclass

import requests
from io import BytesIO
import pdfplumber

load_dotenv()
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

def fetch_pdf(url_template: str) -> tuple[bytes, str]:
    suffixes = ['~', '_']
    for s in suffixes:
        url = url_template.replace("{suffix}", s)
        resp = requests.get(url=url, timeout=10)
        if resp.status_code == 200:
            print(resp)
            return resp.content, url

    raise FileNotFoundError

def extract_table(pdf_bytes: bytes):
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        table = pdf.pages[0].extract_table()
    table = [row[2:] for row in table[2:-1]]
    table[0][0] = "날짜"
    table[-1][0] = "Take Out"

    return table

@dataclass(frozen=True)
class DailyMenu:
    date: str
    a_main: str
    a_side: str
    b_main: str
    b_side: str
    salad: str
    rice: str
    dessert: str

    def to_discord_md(self):
        return (
            "## 오늘의 점심 메뉴를 알려드립니다.\n"
            "### A코스\n"
            f"{self.a_main}\n"
            f"{self.a_side}\n"
            "### B코스\n"
            f"{self.b_main}\n"
            f"{self.b_side}\n"
        )

    def to_discord_embed(self, url: str):
        return {
            "title": "오늘의 점심 메뉴를 알려드립니다.",
            "url": url,
            "color": 0x3498DB,
            "fields": [
                {
                    "name": "A코스",
                    "value": f"{self.a_main}\n{self.a_side}\n",
                    "inline": True
                },
                {
                    "name": "B코스",
                    "value": f"{self.b_main}\n{self.b_side}\n",
                    "inline": True
                }
            ]
        }

def parse_weekly_table(table: list[list[str | None]]):
    keys = {"날짜", "A코너", "B코너", "샐러드바", "잡곡밥", "후 식"}
    key_index = {row[0]: i for i, row in enumerate(table) if row[0] in keys}

    return [DailyMenu(
        date =table[key_index["날짜"]][i],
        a_main=table[key_index["A코너"]][i],
        a_side=table[key_index["A코너"] + 1][i],
        b_main=table[key_index["B코너"]][i],
        b_side=table[key_index["B코너"] + 1][i],
        salad =table[key_index["샐러드바"] + 1][i],
        rice  =table[key_index["잡곡밥"]][i],
        dessert=table[key_index["후 식"]]
    ) for i in range(1, 6)]

def pick_today(weekly: list[DailyMenu], today: date):
    dates = [daily.date for daily in weekly]
    idx = next(i for i, d in enumerate(dates) if d and today.isoformat() in d)

    return weekly[idx]

def post_to_chat(url: str, content: str=None, embeds: list[dict]=None):
    json = {
        "avatar_url": os.environ["AVATAR_URL"],
        "content": content,
        "embeds": embeds
    }

    if embeds is not None:
        json["poll"] = {
            "question": {"text": "오늘의 점심 선택은?"},
            "answers": [
                {"poll_media": {"text": "A코스가 좋아요!"}},
                {"poll_media": {"text": "B코스가 좋아요!"}},
                {"poll_media": {"text": "둘 다 별로...(나가서 먹기)"}}
            ],
            "duration": 4
        }

    return requests.post(url=url, json=json)

def run(today: date=None):
    def _kst_today():
        from zoneinfo import ZoneInfo
        from datetime import datetime

        KST = ZoneInfo("Asia/Seoul")
        return datetime.now(KST).date()

    def _build_url_template(monday: date):
        PDF_NAME_TEMPLATE = os.environ["PDF_NAME_TEMPLATE"]
        PDF_NAME = PDF_NAME_TEMPLATE.replace("{date}", monday.strftime("%m%d"))
        WEB_URL_PREFIX = os.environ["WEB_URL_PREFIX"]
        return f"{WEB_URL_PREFIX}{PDF_NAME}"

    from datetime import timedelta
    today = today or _kst_today()
    monday = today - timedelta(days=today.weekday())
    url_template = _build_url_template(monday=monday)
    content = None
    embeds = None

    try:
        pdf_bytes, pdf_url = fetch_pdf(url_template=url_template)
        weekly = parse_weekly_table(table=extract_table(pdf_bytes=pdf_bytes))
        menu = pick_today(weekly=weekly, today=today)
        # md = menu.to_discord_md()
        embeds = [menu.to_discord_embed(url=pdf_url)]
    except FileNotFoundError:
        content = "점심 메뉴를 찾을 수 없습니다. ㅠㅠ"
    except Exception:
        content = "처리 중 오류가 발생했습니다. ㅠㅠ"

    resp = post_to_chat(
        url=WEBHOOK_URL,
        content=content,
        embeds=embeds
    )
    print(resp)
    return content

if __name__ == "__main__":
    run()
