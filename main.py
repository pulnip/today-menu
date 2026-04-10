from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os

import requests
from io import BytesIO
import pdfplumber

KST = ZoneInfo("Asia/Seoul")
today = datetime.now(KST).date()
monday = today - timedelta(days=today.weekday())

load_dotenv()
PDF = os.environ["PDF_TEMPLATE"].replace('date', monday.strftime("%m%d"))
WEB_URL = f"{os.environ["WEB_URL"]}{PDF}"
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

def get_menu_table(url: str):
    resp = requests.get(url)
    print(resp)

    with pdfplumber.open(BytesIO(resp.content)) as pdf:
        table = pdf.pages[0].extract_table()

    return table

def get_today_menu(table: list[list[str | None]]):
    header = table[2]
    col = next(i for i, cell in enumerate(header) if cell and today.isoformat() in cell)

    items: list[str] = []
    for row in table[3:]:  # 날짜 행 이후부터
        if col < len(row) and row[col] and row[col].strip():
            items.append(row[col].strip())

    return{
        "a_red" : items[0].split('\n'),
        "a_menu": items[1].split('\n'),
        "b_red" : items[2].split('\n'),
        "b_menu": items[3].split('\n'),
        "salad" : items[4].split('\n') + items[5].split('\n'),
        "rice"  : items[6].split('\n'),
        "drink" : items[7].split('\n'),
        "take_out": items[8].split('\n')
    }

def to_markdown_str(menu: dict[str: list[str]]):
    return (
        "## 오늘의 점심 메뉴를 알려드립니다.\n"
        "### A코스\n"
        f"{"\n".join(menu['a_red'] + menu['a_menu'])}\n"
        "### B코스\n"
        f"{"\n".join(menu['b_red'] + menu['b_menu'])}\n"
    )

def post_to_chat(url: str, content: str):
    return requests.post(
        url,
        json = {
            "content": content
        }
    )

if __name__ == "__main__":
    table = get_menu_table(url=WEB_URL)
    menu = get_today_menu(table=table)
    md = to_markdown_str(menu=menu)

    resp = post_to_chat(
        url=WEBHOOK_URL,
        content=md
    )
    print(resp)
