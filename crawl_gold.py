import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import concurrent.futures

def fetch_btmh():
    """Cào dữ liệu Bảo Tín Mạnh Hải từ webgia (do vẫn đang hoạt động chuẩn)"""
    brand = "btmh"
    url = "https://webgia.com/gia-vang/bao-tin-manh-hai/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return brand, []
        
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
                    name = cols[-3]
                    if not name and len(cols) >= 4: name = cols[-4]
                    row_text = " ".join(cols).upper()
                    
                    # Lọc rác
                    if "WEB" in buy.upper() or "GIÁ" in buy.upper(): buy = ""
                    if "WEB" in sell.upper() or "GIÁ" in sell.upper(): sell = ""
                    if not any(c.isdigit() for c in buy) and not any(c.isdigit() for c in sell): continue
                    
                    # Dịch tên cho App HTML
                    if "NHẪN TRÒN 999.9 BTMH" in row_text:
                        name = "Vàng miếng SJC (Cty CP BTMH)"
                        
                    brand_prices.append({"type": name.strip(), "buy": buy, "sell": sell})
        return brand, brand_prices
    except Exception as e:
        print(f"Lỗi BTMH: {e}")
        return brand, []

def fetch_phu_quy():
    """Cào dữ liệu trực tiếp từ TRANG CHỦ Phú Quý để đảm bảo độ chuẩn xác cao nhất"""
    brand = "phu_quy"
    url = "https://phuquy.com.vn/bang-gia/vang"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return brand, []
        
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        brand_prices = []
        if table:
            rows = table.find_all("tr")
            for row in rows:
                cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                
                # Bảng chính chủ thường chuẩn form: Cột 1 Tên, Cột 2 Mua, Cột 3 Bán
                if len(cols) >= 3:
                    name = cols[0]
                    buy = cols[1]
                    sell = cols[2]
                    
                    # Bỏ qua dòng tiêu đề (ví dụ: Tên Vàng | Giá mua | Giá bán)
                    if not any(c.isdigit() for c in buy): 
                        continue
                        
                    # Dịch chuẩn tên V9999P cho app HTML nhận diện
                    name_upper = name.upper()
                    if "V9999P" in name_upper or "NHẪN PHÚ QUÝ" in name_upper:
                        name = "Vàng nguyên liệu 999,9"
                        
                    brand_prices.append({
                        "type": name,
                        "buy": buy,
                        "sell": sell
                    })
        return brand, brand_prices
    except Exception as e:
        print(f"Lỗi Phú Quý: {e}")
        return brand, []

def crawl_gold_prices():
    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }

    # Chạy đa luồng song song 2 nguồn khác nhau
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_btmh = executor.submit(fetch_btmh)
        future_pq = executor.submit(fetch_phu_quy)
        
        for future in concurrent.futures.as_completed([future_btmh, future_pq]):
            brand, prices = future.result()
            data["prices"][brand] = prices

    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("Thành công: Cào dữ liệu từ Webgia (BTMH) và Trang chủ Phú Quý!")

if __name__ == "__main__":
    crawl_gold_prices()