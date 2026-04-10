from datetime import date
from dotenv import load_dotenv
import os

import requests
from io import BytesIO
import pdfplumber

load_dotenv()
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

def make_menu_dict(table: list[list[str | None]]):
    table = [row[2:] for row in table[2:-1]]
    table[0][0] = "날짜"
    table[-1][0] = "Take Out"

    keys = {"날짜", "A코너", "B코너", "샐러드바", "잡곡밥", "후 식"}
    key_index = {row[0]: i for i, row in enumerate(table) if row[0] in keys}

    return{
        "date"  : table[key_index["날짜"]][1:],
        "a_red" : table[key_index["A코너"]][1:],
        "a_menu": table[key_index["A코너"] + 1][1:],
        "b_red" : table[key_index["B코너"]][1:],
        "b_menu": table[key_index["B코너"] + 1][1:],
        "salad" : table[key_index["샐러드바"]][1:],
        "rice"  : table[key_index["잡곡밥"]][1:],
        "drink" : table[key_index["후 식"]][1:],
        "take_out": table[key_index["A코너"]][1:]
    }

def get_menu(url_template: str):
    suffix = ['~', '_']
    urls = [url_template.replace("{suffix}", s) for s in suffix]
    for url in urls:
        resp = requests.head(url=url)
        if resp.status_code == 200:
            resp = requests.get(url=url)

    print(resp)
    resp.raise_for_status()

    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        table = pdf.pages[0].extract_table()

    return make_menu_dict(table)

def get_today_menu(menu: dict[str, list[str]], today: date):
    dates = menu['date']
    col = next(i for i, cell in enumerate(dates) if cell and today.isoformat() in cell)

    return{
        key: value[col] for key, value in menu.items()
    }

def to_markdown_str(menu: dict[str: list[str]]):
    return (
        "## 오늘의 점심 메뉴를 알려드립니다.\n"
        "### A코스\n"
        f"{menu['a_red']}\n{menu['a_menu']}\n"
        "### B코스\n"
        f"{menu['b_red']}\n{menu['b_menu']}\n"
    )

def post_to_chat(url: str, content: str):
    return requests.post(
        url,
        json = {
            "content": content
        }
    )

def run(today: date=None):
    if today is None:
        from zoneinfo import ZoneInfo
        from datetime import datetime

        KST = ZoneInfo("Asia/Seoul")
        today = datetime.now(KST).date()

    from datetime import timedelta

    monday = today - timedelta(days=today.weekday())
    PDF_NAME = os.environ["PDF_NAME_TEMPLATE"].replace("{date}", monday.strftime("%m%d"))
    WEB_URL_TEMPLATE = f"{os.environ["WEB_URL_PREFIX"]}{PDF_NAME}"

    try:
        weekly_menu = get_menu(url_template=WEB_URL_TEMPLATE)
        today_menu = get_today_menu(menu=weekly_menu, today=today)
        md = to_markdown_str(menu=today_menu)
    except requests.HTTPError:
        md = "점심 메뉴를 찾을 수 없습니다. ㅠㅠ"
    except Exception:
        md = "처리 중 오류가 발생했습니다. ㅠㅠ"

    resp = post_to_chat(
        url=WEBHOOK_URL,
        content=md
    )
    print(resp)
    return md

if __name__ == "__main__":
    run()
