import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import concurrent.futures

def fetch_data(brand, url, headers):
    """Hàm cào và lọc dữ liệu cho từng thương hiệu"""
    try:
        with requests.Session() as session:
            response = session.get(url, headers=headers, timeout=15)
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
                    
                    # Bỏ qua nếu dòng quá ngắn không đủ dữ liệu
                    if len(cols) < 3:
                        continue
                        
                    # Lấy text của toàn bộ dòng để rà soát từ khóa bất chấp lệch cột
                    row_text = " ".join(cols).upper()
                    
                    # 2 cột ngoài cùng bên phải luôn luôn là Giá Mua và Giá Bán
                    buy = cols[-2]
                    sell = cols[-1]
                    
                    # Tên mặc định lấy ở cột áp chót (kế cột Giá Mua)
                    name = cols[-3]
                    if not name and len(cols) >= 4:
                        name = cols[-4]
                    
                    # --- XỬ LÝ LỌC RÁC TỪ WEBGIA ---
                    if "WEB" in buy.upper() or "GIÁ" in buy.upper():
                        buy = ""
                    if "WEB" in sell.upper() or "GIÁ" in sell.upper():
                        sell = ""
                        
                    # Nếu Mua và Bán đều bị trống hoặc toàn chữ (không có số tiền) -> Bỏ qua dòng này
                    if not any(c.isdigit() for c in buy) and not any(c.isdigit() for c in sell):
                        continue
                        
                    # --- DỊCH THUẬT TÊN VÀNG CHUẨN CHO APP HTML ---
                    # 1. Bắt Vàng nguyên liệu 999,9 (Phú Quý)
                    if brand == "phu_quy" and ("V9999P" in row_text or "PHI SJC" in row_text):
                        name = "Vàng nguyên liệu 999,9"
                        
                    # 2. Bắt Vàng miếng SJC BTMH
                    if brand == "btmh" and "NHẪN TRÒN 999.9 BTMH" in row_text:
                        name = "Vàng miếng SJC (Cty CP BTMH)"
                        
                    brand_prices.append({
                        "type": name.strip(),
                        "buy": buy,
                        "sell": sell
                    })
            return brand, brand_prices
    except Exception as e:
        print(f"Lỗi khi cào dữ liệu {brand}: {e}")
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

    # Chạy đa luồng song song để tăng tốc cào
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_data, brand, url, headers) for brand, url in urls.items()]
        
        for future in concurrent.futures.as_completed(futures):
            brand, prices = future.result()
            data["prices"][brand] = prices

    # Ghi ra file JSON
    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("Cào dữ liệu thành công! Đã bắt mốc V9999P và Nhẫn BTMH.")

if __name__ == "__main__":
    crawl_gold_prices()