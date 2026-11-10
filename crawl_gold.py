
import json
import re
import requests
import concurrent.futures

from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

URL_PHU_QUY = "https://phuquygroup.vn/giavang"
URL_BTMH = "https://webgia.com/gia-vang/bao-tin-manh-hai/"


def clean_price(value):
    """Làm sạch giá, không nhận watermark."""
    value = value.strip()

    if not value or "webgia" in value.lower() or "web" in value.lower():
        return ""

    if value in ["-", "—", "–"]:
        return ""

    # Chỉ giữ lại số
    digits = re.sub(r"\D", "", value)

    if not digits:
        return ""

    # Chuẩn hóa về định dạng 13.500.000
    return f"{int(digits):,}".replace(",", ".")


def get_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=20
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


# ==========================================
# PHÚ QUÝ - WEBSITE CHÍNH THỨC
# ==========================================

def fetch_phu_quy():

    brand = "phu_quy"

    try:
        soup = get_page(URL_PHU_QUY)

        prices = []

        # Tìm bảng có các tiêu đề Loại vàng, Mua vào, Bán ra
        for table in soup.find_all("table"):

            rows = table.find_all("tr")

            for row in rows:

                cells = row.find_all(["td", "th"])

                if len(cells) < 3:
                    continue

                values = [
                    cell.get_text(" ", strip=True)
                    for cell in cells
                ]

                row_text = " ".join(values).lower()

                # Bỏ qua dòng tiêu đề
                if "loại vàng" in row_text:
                    continue

                name = values[0].strip()

                # Chỉ lấy dữ liệu thuộc bảng giá
                if not name:
                    continue

                buy = clean_price(values[1])
                sell = clean_price(values[2])

                prices.append({
                    "type": name,
                    "buy": buy,
                    "sell": sell
                })

        # Kiểm tra riêng sản phẩm V9999P
        target = next(
            (
                item for item in prices
                if "vàng 999.9 phi sjc" in item["type"].lower()
            ),
            None
        )

        if target is None:
            raise ValueError(
                "Không tìm thấy dòng Vàng 999.9 phi SJC "
                "trên website chính thức!"
            )

        if not target["buy"]:
            raise ValueError(
                "V9999P không có giá mua hợp lệ!"
            )

        print("\nPHÚ QUÝ - V9999P")
        print("Tên:", target["type"])
        print("Mua:", target["buy"])
        print("Bán:", target["sell"])

        # Đổi tên theo cấu trúc JSON của ứng dụng
        target["type"] = "Vàng nguyên liệu 999,9"

        return brand, prices

    except Exception as e:
        print(f"LỖI PHÚ QUÝ: {e}")
        return brand, []


# ==========================================
# BẢO TÍN MẠNH HẢI - WEBGIA
# ==========================================

def fetch_btmh():

    brand = "btmh"

    try:
        soup = get_page(URL_BTMH)

        prices = []

        table = soup.find("table")

        if not table:
            raise ValueError("Không tìm thấy bảng giá BTMH")

        tbody = table.find("tbody")

        rows = (
            tbody.find_all("tr")
            if tbody
            else table.find_all("tr")[1:]
        )

        for row in rows:

            cols = [
                ele.get_text(" ", strip=True)
                for ele in row.find_all(["td", "th"])
            ]

            if len(cols) < 3:
                continue

            name = " ".join(cols[:-2]).strip()

            buy = clean_price(cols[-2])
            sell = clean_price(cols[-1])

            if not name:
                continue

            if not buy and not sell:
                continue

            # Không gán nhầm tên nhẫn thành vàng miếng SJC
            prices.append({
                "type": name,
                "buy": buy,
                "sell": sell
            })

        print(f"\nBTMH: Đã lấy {len(prices)} dòng giá")

        return brand, prices

    except Exception as e:
        print(f"LỖI BTMH: {e}")
        return brand, []


# ==========================================
# CRAWL TỔNG HỢP
# ==========================================

def crawl_gold_prices():

    data = {
        "updated_at": datetime.now(
            ZoneInfo("Asia/Ho_Chi_Minh")
        ).strftime("%Y-%m-%d %H:%M:%S"),

        "prices": {}
    }

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=2
    ) as executor:

        futures = [
            executor.submit(fetch_phu_quy),
            executor.submit(fetch_btmh)
        ]

        for future in concurrent.futures.as_completed(futures):

            brand, prices = future.result()

            data["prices"][brand] = prices

    # Kiểm tra dữ liệu V9999P trước khi lưu
    phu_quy = data["prices"].get("phu_quy", [])

    v9999p = next(
        (
            item for item in phu_quy
            if item["type"] == "Vàng nguyên liệu 999,9"
        ),
        None
    )

    if not v9999p:
        print("\nCẢNH BÁO: KHÔNG CÓ DỮ LIỆU V9999P!")

    else:
        print("\nKIỂM TRA V9999P THÀNH CÔNG")
        print(json.dumps(
            v9999p,
            ensure_ascii=False,
            indent=4
        ))

    # Lưu JSON
    with open(
        "gold-prices.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

    print("\nĐÃ LƯU gold-prices.json")
    print("Thời gian:", data["updated_at"])


if __name__ == "__main__":
    crawl_gold_prices()