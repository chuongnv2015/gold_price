import json
import re
import unicodedata
import concurrent.futures
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


# ============================================================
# CAU HINH
# ============================================================

URL_PHU_QUY = "https://phuquygroup.vn/giavang"
URL_BTMH = "https://webgia.com/gia-vang/bao-tin-manh-hai/"

OUTPUT_FILE = "gold-prices.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


# ============================================================
# HAM DUNG CHUNG
# ============================================================

def get_page(url):
    """Tai trang web va tra ve BeautifulSoup."""
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=25
    )
    response.raise_for_status()

    # Dung encoding do requests phat hien; fallback UTF-8 neu can.
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding or "utf-8"

    return BeautifulSoup(response.text, "html.parser")


def normalize_name(text):
    """Chuan hoa ten de so sanh, khong phan biet hoa thuong/dau."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    )
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip().upper()


def clean_price(value):
    """
    Chuan hoa gia thanh dang 13.740.000.
    Gia trong, '-', watermark hoac khong co chu so se thanh chuoi rong.
    """
    value = (value or "").replace("\xa0", " ").strip()

    if not value:
        return ""

    lowered = value.lower()
    if "webgia" in lowered or "web" in lowered:
        return ""

    if value in {"-", "—", "–"}:
        return ""

    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""

    return f"{int(digits):,}".replace(",", ".")


# ============================================================
# PHU QUY - WEBSITE CHINH THUC
# ============================================================

def fetch_phu_quy():
    """
    Doc bang gia Phu Quy tu website chinh thuc.

    Chi chap nhan bang co dong ten chinh xac:
    'Vang 999.9 phi SJC'.

    Khong lay gia cua 'Vang trang suc 999.9',
    'Phu Quy 1 Luong 999.9' hay san pham khac de thay the V9999P.
    """
    print("Dang lay bang gia Phu Quy...")

    soup = get_page(URL_PHU_QUY)

    target_table = None

    # Tim bang co dong Vang 999.9 phi SJC.
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])

            if not cells:
                continue

            row_name = cells[0].get_text(" ", strip=True)

            if normalize_name(row_name) == "VANG 999.9 PHI SJC":
                target_table = table
                break

        if target_table is not None:
            break

    if target_table is None:
        raise RuntimeError(
            "Khong tim thay dong 'Vang 999.9 phi SJC' "
            "trong HTML tra ve tu website Phu Quy. "
            "Co the website da doi cau truc hoac tai bang gia bang JavaScript."
        )

    prices = []
    found_v9999p = False

    for row in target_table.find_all("tr"):
        cells = row.find_all(["td", "th"])

        # Cau truc bang tren anh nguoi dung cung cap:
        # cot 1 = Ten vang, cot 2 = Mua vao, cot 3 = Ban ra.
        if len(cells) < 3:
            continue

        name = cells[0].get_text(" ", strip=True)
        if not name:
            continue

        normalized = normalize_name(name)

        # Bo qua cac dong tieu de.
        if "MUA VAO" in normalized or "BAN RA" in normalized:
            continue

        buy_raw = cells[1].get_text(" ", strip=True)
        sell_raw = cells[2].get_text(" ", strip=True)

        buy = clean_price(buy_raw)
        sell = clean_price(sell_raw)

        # Khong dua cac dong khong phai san pham vao JSON.
        if not buy and not sell:
            continue

        if normalized == "VANG 999.9 PHI SJC":
            if not buy:
                raise RuntimeError(
                    "Tim thay dong V9999P nhung khong doc duoc gia mua."
                )

            name = "Vàng nguyên liệu 999,9"
            found_v9999p = True

            print("Da tim thay V9999P:")
            print(f"  Mua vao: {buy}")
            print(f"  Ban ra:  {sell if sell else 'Chua niem yet'}")

        prices.append({
            "type": name,
            "buy": buy,
            "sell": sell
        })

    if not found_v9999p:
        raise RuntimeError(
            "Khong doc duoc dong V9999P tu bang gia Phu Quy."
        )

    return "phu_quy", prices


# ============================================================
# BAO TIN MANH HAI - WEBGIA
# ============================================================

def fetch_btmh():
    """Doc bang gia Bao Tin Manh Hai tu Webgia."""
    print("Dang lay bang gia Bao Tin Manh Hai...")

    soup = get_page(URL_BTMH)

    table = soup.find("table")
    if table is None:
        raise RuntimeError("Khong tim thay bang gia BTMH tren Webgia.")

    tbody = table.find("tbody")
    rows = (
        tbody.find_all("tr")
        if tbody
        else table.find_all("tr")[1:]
    )

    prices = []

    for row in rows:
        cols = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all(["td", "th"])
        ]

        if len(cols) < 3:
            continue

        # Webgia: cac cot cuoi cung la gia mua va gia ban.
        name = " ".join(cols[:-2]).strip()
        buy = clean_price(cols[-2])
        sell = clean_price(cols[-1])

        if not name or (not buy and not sell):
            continue

        # Chi chuan hoa ten neu dung la dong vang mieng SJC.
        if "VANG MIENG SJC" in normalize_name(name):
            name = "Vàng miếng SJC (Cty CP BTMH)"

        prices.append({
            "type": name,
            "buy": buy,
            "sell": sell
        })

    if not prices:
        raise RuntimeError("Khong doc duoc du lieu gia BTMH.")

    print(f"Da lay {len(prices)} dong gia BTMH.")
    return "btmh", prices


# ============================================================
# CRAWL VA LUU JSON
# ============================================================

def crawl_gold_prices():
    data = {
        "updated_at": datetime.now(
            ZoneInfo("Asia/Ho_Chi_Minh")
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }

    # Chay song song hai nguon.
    tasks = [fetch_phu_quy, fetch_btmh]

    try:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=2
        ) as executor:
            futures = [
                executor.submit(task)
                for task in tasks
            ]

            for future in concurrent.futures.as_completed(futures):
                brand, prices = future.result()
                data["prices"][brand] = prices

        # Kiem tra bat buoc: khong luu neu thieu V9999P.
        phu_quy_prices = data["prices"].get("phu_quy", [])

        v9999p = next(
            (
                item for item in phu_quy_prices
                if item["type"] == "Vàng nguyên liệu 999,9"
            ),
            None
        )

        if v9999p is None or not v9999p["buy"]:
            raise RuntimeError(
                "Du lieu V9999P khong hop le. "
                "Huy thao tac ghi de gold-prices.json cu."
            )

        # Chi ghi file sau khi ca hai nguon da lay du lieu thanh cong.
        with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

        print("\nDa cap nhat", OUTPUT_FILE)
        print("Thoi gian:", data["updated_at"])
        print("V9999P:", v9999p)

    except Exception as error:
        print("\nLOI CRAWL:", error)
        print(
            "Khong ghi de file JSON. "
            "File gold-prices.json cu duoc giu nguyen de tranh mat du lieu."
        )
        raise


if __name__ == "__main__":
    crawl_gold_prices()