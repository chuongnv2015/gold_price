import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def crawl_gold_prices():
    # Sử dụng trang tổng hợp uy tín để lấy dữ liệu BTMC và BTMH nhanh chóng
    urls = {
        "btmc": "https://webgia.com/gia-vang/bao-tin-minh-chau/",
        "btmh": "https://webgia.com/gia-vang/bao-tin-manh-hai/"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }

    for brand, url in urls.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                table = soup.find("table") # Tìm bảng giá vàng
                
                brand_prices = []
                if table:
                    rows = table.find_all("tr")[1:] # Bỏ qua header
                    for row in rows:
                        cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                        if len(cols) >= 3:
                            brand_prices.append({
                                "type": cols[0],
                                "buy": cols[1],
                                "sell": cols[2]
                            })
                data["prices"][brand] = brand_prices
        except Exception as e:
            print(f"Lỗi khi cào dữ liệu {brand}: {e}")
            data["prices"][brand] = []

    # Lưu ra file gold-prices.json
    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("Đã cập nhật file gold-prices.json thành công!")

if __name__ == "__main__":
    crawl_gold_prices()