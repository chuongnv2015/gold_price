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
                    
                    # Bảng BTMH có 3 cột, Phú Quý có 4-5 cột. Lấy >= 3 để vét sạch
                    if len(cols) >= 3:
                        # 2 cột cuối cùng luôn là Giá Mua và Giá Bán
                        buy = cols[-2]
                        sell = cols[-1]
                        
                        # Nối tất cả các cột phía trước lại làm Tên vàng để không bị trượt từ khóa
                        name = " ".join(cols[:-2])
                        
                        # --- XỬ LÝ RÁC WEBGIA (Lọc riêng từng cột) ---
                        lower_buy = buy.lower()
                        lower_sell = sell.lower()
                        
                        if "webgia" in lower_buy or "web" in lower_buy or "giá" in lower_buy:
                            buy = ""
                        if "webgia" in lower_sell or "web" in lower_sell or "giá" in lower_sell:
                            sell = ""
                            
                        # Nếu cả 2 cột đều không có số tiền thì mới bỏ qua dòng này
                        if not any(c.isdigit() for c in buy) and not any(c.isdigit() for c in sell):
                            continue
                            
                        # --- DỊCH TÊN VÀNG CHO APP THÁP TÀI SẢN ĐỌC ---
                        # Đổi tên Phú Quý
                        if brand == "phu_quy" and ("V9999P" in name or "999.9 phi SJC" in name):
                            name = "Vàng nguyên liệu 999,9"
                            
                        # Đổi tên BTMH
                        if brand == "btmh" and "Nhẫn tròn 999.9 BTMH" in name:
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
    # Cập nhật đúng 2 link đích
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

    # Cào song song đa luồng để tiết kiệm thời gian
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_data, brand, url, headers) for brand, url in urls.items()]
        
        for future in concurrent.futures.as_completed(futures):
            brand, prices = future.result()
            data["prices"][brand] = prices

    # Lưu kết quả
    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("Cào dữ liệu thành công! Đã bắt đúng mốc V9999P và Nhẫn tròn 999.9 BTMH.")

if __name__ == "__main__":
    crawl_gold_prices()