import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import concurrent.futures

def fetch_data(brand, url, headers):
    """Hàm cào và làm sạch dữ liệu cho từng brand"""
    try:
        # Dùng Session để tăng tốc độ kết nối
        with requests.Session() as session:
            response = session.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return brand, []
                
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table")
            
            brand_prices = []
            if table:
                # Ưu tiên tìm trong tbody để tránh dính thẻ thead (tiêu đề)
                tbody = table.find("tbody")
                rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]
                
                for row in rows:
                    cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                    if len(cols) >= 3:
                        name = cols[0]
                        buy = cols[1]
                        sell = cols[2]
                        
                        # --- BỘ LỌC CHỐNG NHIỄU (ANTI-WATERMARK) ---
                        # 1. Bỏ qua các dòng bị webgia chèn watermark mờ
                        lower_buy = buy.lower()
                        if "webgia" in lower_buy or "web" in lower_buy or "giá" in lower_buy:
                            continue
                            
                        # 2. Đảm bảo cột giá mua hoặc bán thực sự chứa chữ số
                        if not any(c.isdigit() for c in buy) and not any(c.isdigit() for c in sell):
                            continue
                            
                        brand_prices.append({
                            "type": name,
                            "buy": buy,
                            "sell": sell
                        })
            return brand, brand_prices
    except Exception as e:
        print(f"Lỗi khi cào dữ liệu {brand}: {e}")
        return brand, []

def crawl_gold_prices():
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

    # TỐI ƯU NHANH NHẤT: Xử lý cào nhiều trang cùng lúc (Đa luồng/Threading)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_data, brand, url, headers) for brand, url in urls.items()]
        
        for future in concurrent.futures.as_completed(futures):
            brand, prices = future.result()
            data["prices"][brand] = prices

    # Lưu ra file gold-prices.json
    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("Đã cập nhật file gold-prices.json thành công (Đã lọc sạch rác)!")

if __name__ == "__main__":
    crawl_gold_prices()