
import json
import re
import unicodedata
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import concurrent.futures


# Chuẩn hóa chữ để so sánh tên sản phẩm
def normalize_text(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", text).strip().upper()


# Kiểm tra và làm sạch giá
def clean_price(value):
    value = value.strip()

    # Loại bỏ watermark
    if "webgia" in value.lower() or "web" in value.lower():
        return ""

    # Chỉ chấp nhận dữ liệu có chữ số
    if not any(c.isdigit() for c in value):
        return ""

    return value


def fetch_data(brand, url, headers):
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        brand_prices = []
        found_target = False

        for table in soup.find_all("table"):
            rows = table.find_all("tr")

            if not rows:
                continue

            # Tìm dòng tiêu đề
            header_row = None
            header_index = 0

            for i, row in enumerate(rows):
                cells = row.find_all(["th", "td"])
                texts = [
                    normalize_text(c.get_text(" ", strip=True))
                    for c in cells
                ]

                if any("MUA" in t for t in texts) and any(
                    "BAN" in t for t in texts
                ):
                    header_row = texts
                    header_index = i
                    break

            if header_row is None:
                continue

            # Xác định vị trí các cột theo tiêu đề
            buy_idx = next(
                (i for i, t in enumerate(header_row) if "MUA" in t),
                None
            )
            sell_idx = next(
                (i for i, t in enumerate(header_row) if "BAN" in t),
                None
            )

            code_idx = next(
                (i for i, t in enumerate(header_row)
                 if "LOAI VANG" in t),
                None
            )

            name_idx = next(
                (i for i, t in enumerate(header_row)
                 if "TEN VANG" in t),
                None
            )

            # Website chính thức Phú Quý chỉ có cột Loại vàng
            if name_idx is None:
                name_idx = code_idx if code_idx is not None else 0

            if buy_idx is None or sell_idx is None:
                continue

            for row in rows[header_index + 1:]:
                cols = [
                    c.get_text(" ", strip=True)
                    for c in row.find_all(["td", "th"])
                ]

                required_idx = max(
                    buy_idx,
                    sell_idx,
                    name_idx,
                    code_idx if code_idx is not None else 0
                )

                if len(cols) <= required_idx:
                    continue

                name = cols[name_idx].strip()
                buy = clean_price(cols[buy_idx])
                sell = clean_price(cols[sell_idx])

                code = (
                    cols[code_idx].strip()
                    if code_idx is not None
                    else ""
                )

                name_upper = normalize_text(name)
                code_upper = normalize_text(code)

                # Bỏ qua dòng không có tên
                if not name and not code:
                    continue

                # Nhận diện chính xác V9999P
                is_v9999p = (
                    code_upper == "V9999P"
                    or "VANG 999.9 PHI SJC" in name_upper
                )

                if brand == "phu_quy" and is_v9999p:
                    name = "Vàng nguyên liệu 999,9"
                    found_target = True

                # Ánh xạ tên Bảo Tín Mạnh Hải
                if (
                    brand == "btmh"
                    and "NHAN TRON 999.9 BTMH" in name_upper
                ):
                    name = "Vàng miếng SJC (Cty CP BTMH)"

                # Không lưu dòng không có giá
                if not buy and not sell:
                    continue

                brand_prices.append({
                    "type": name.strip(),
                    "buy": buy,
                    "sell": sell
                })

        if brand == "phu_quy" and not found_target:
            print("CẢNH BÁO: Không tìm thấy V9999P!")

        return brand, brand_prices

    except Exception as e:
        print(f"Lỗi {brand}: {e}")
        return brand, []


def crawl_gold_prices():

    # Phú Quý dùng nguồn chính thức
    # BTMH tiếp tục dùng Webgia
    urls = {
        "phu_quy": "https://phuquygroup.vn/giavang",
        "btmh": "https://webgia.com/gia-vang/bao-tin-manh-hai/"
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    data = {
        "updated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "prices": {}
    }

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=2
    ) as executor:

        futures = [
            executor.submit(fetch_data, brand, url, headers)
            for brand, url in urls.items()
        ]

        for future in concurrent.futures.as_completed(futures):
            brand, prices = future.result()
            data["prices"][brand] = prices

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

    # Kiểm tra riêng V9999P
    phu_quy = data["prices"].get("phu_quy", [])

    target = next(
        (
            item for item in phu_quy
            if item["type"] == "Vàng nguyên liệu 999,9"
        ),
        None
    )

    if target:
        print("\nĐÃ TÌM THẤY V9999P:")
        print(f"Mua vào: {target['buy']}")
        print(f"Bán ra: {target['sell']}")
    else:
        print("\nCẢNH BÁO: Chưa lấy được giá V9999P!")

    print("\nĐã lưu gold-prices.json")


if __name__ == "__main__":
    crawl_gold_prices()