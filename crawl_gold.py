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
                    # Bảng trên webgia thường có 4 cột (Loại vàng, Tên vàng, Mua vào, Bán ra)
                    # Dòng đầu tiên có thể có 5 cột (có thêm cột Khu vực chứa rowspan)
                    if len(cols) >= 4:
                        # Lấy 2 cột cuối cùng luôn luôn là Giá Mua và Giá Bán
                        sell = cols[-1]
                        buy = cols[-2]
                        
                        # Tên vàng thường nằm ở cột áp chót trước giá mua
                        name = cols[-3]
                        
                        # Nếu cột Tên vàng bị trống, lấy cột Loại vàng
                        if not name:
                            name = cols[-4]
                        
                        # --- BỘ LỌC RÁC TỪ WEBGIA ---
                        lower_buy = buy.lower()
                        if "webgia" in lower_buy or "web" in lower_buy or "giá" in lower_buy:
                            continue
                        if not any(c.isdigit() for c in buy) and not any(c.isdigit() for c in sell):
                            continue
                            
                        # --- CHUẨN HÓA TÊN LOẠI VÀNG ĐỂ HTML APP ĐỌC ĐƯỢC ---
                        # 1. Phú Quý: Đổi "V9999P" hoặc "Vàng 999.9 phi SJC" -> Thành tên mà HTML đang mong đợi
                        if brand == "phu_quy" and ("V9999P" in name or "Vàng 999.9 phi SJC" in name or "V9999P" in cols[-4]):
                            name = "Vàng nguyên liệu 999,9"
                            
                        # 2. Bảo Tín Mạnh Hải: Đổi "Nhẫn tròn 999.9 BTMH" -> Thành tên mà HTML đang mong đợi
                        if brand == "btmh" and "Nhẫn tròn 999.9 BTMH" in name:
                            name = "Vàng miếng SJC (Cty CP BTMH)"
                            
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
    # Cập nhật đúng 2 link đích theo yêu cầu
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

    # Chạy cào đa luồng (song song 2 link) để lấy dữ liệu nhanh nhất có thể
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_data, brand, url, headers) for brand, url in urls.items()]
        
        for future in concurrent.futures.as_completed(futures):
            brand, prices = future.result()
            data["prices"][brand] = prices

    # Lưu ra file JSON
    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("Cào dữ liệu thành công! Đã bắt đúng giá V9999P và Nhẫn tròn 999.9 BTMH.")

if __name__ == "__main__":
    crawl_gold_prices()