import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import concurrent.futures

def fetch_data(brand, url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return brand, []
            
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        
        brand_prices = []
        if table:
            tbody = table.find("tbody")
            rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]
            
            for row in rows:
                cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                if len(cols) >= 3:
                    buy = cols[-2]
                    sell = cols[-1]
                    name = " ".join(cols[:-2])
                    
                    # Lọc rác watermark của webgia
                    if "webgia" in buy.lower() or "web" in buy.lower(): buy = ""
                    if "webgia" in sell.lower() or "web" in sell.lower(): sell = ""
                    
                    # Bỏ qua dòng nếu không chứa chữ số (rác)
                    if not any(c.isdigit() for c in buy) and not any(c.isdigit() for c in sell):
                        continue
                        
                    # --- ÁNH XẠ TÊN CHUẨN CHO APP HTML ---
                    name_upper = name.upper()
                    
                    # Bắt Phú Quý V9999P
                    if brand == "phu_quy" and ("V9999P" in name_upper or "999.9 PHI SJC" in name_upper):
                        name = "Vàng nguyên liệu 999,9"
                        
                    # Bắt Nhẫn tròn BTMH
                    if brand == "btmh" and "NHẪN TRÒN 999.9 BTMH" in name_upper:
                        name = "Vàng miếng SJC (Cty CP BTMH)"
                        
                    brand_prices.append({
                        "type": name.strip(),
                        "buy": buy,
                        "sell": sell
                    })
        return brand, brand_prices
    except Exception as e:
        print(f"Lỗi {brand}: {e}")
        return brand, []

def crawl_gold_prices():
    urls = {
        "phu_quy": "https://webgia.com/gia-vang/phu-quy/",
        "btmh": "https://webgia.com/gia-vang/bao-tin-manh-hai/"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_data, brand, url, headers) for brand, url in urls.items()]
        
        for future in concurrent.futures.as_completed(futures):
            brand, prices = future.result()
            data["prices"][brand] = prices

    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("Xong! Đã quét toàn bộ bảng giá và sẵn sàng bắt V9999P.")

if __name__ == "__main__":
    crawl_gold_prices()