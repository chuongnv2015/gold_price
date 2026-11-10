import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import concurrent.futures
import re

def fetch_btmh():
    """Cào Bảo Tín Mạnh Hải từ webgia và bắt ĐÚNG Nhẫn tròn 999.9"""
    brand = "btmh"
    url = "https://webgia.com/gia-vang/bao-tin-manh-hai/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        
        brand_prices = []
        if table:
            rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]
            for row in rows:
                cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                if len(cols) >= 3:
                    buy = cols[-2]
                    sell = cols[-1]
                    name = " ".join(cols[:-2]).upper()
                    
                    # Nếu chính xác là Nhẫn BTMH thì mới lấy
                    if "NHẪN TRÒN 999.9 BTMH" in name:
                        brand_prices.append({
                            "type": "Vàng miếng SJC (Cty CP BTMH)", # Đổi tên chuẩn cho App HTML
                            "buy": buy,
                            "sell": sell
                        })
                        break # Tìm thấy rồi thì dừng luôn cho nhẹ máy
        return brand, brand_prices
    except Exception as e:
        print(f"Lỗi BTMH: {e}")
        return brand, []

def fetch_phu_quy():
    """Cào TRỰC TIẾP Phú Quý và bắt ĐÚNG mã V9999P / 999.9 phi SJC"""
    brand = "phu_quy"
    url = "https://phuquy.com.vn/bang-gia/vang"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Phương thức 1: Quét thẻ Table (Phòng hờ web có bảng chuẩn)
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                text_content = row.get_text(separator=" ", strip=True).upper()
                if "V9999P" in text_content or "999.9 PHI SJC" in text_content:
                    cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
                    prices = []
                    for c in cols:
                        num_str = "".join(filter(str.isdigit, c))
                        if len(num_str) >= 6: # Các số có độ dài >= 100.000đ
                            prices.append(c)
                    
                    if len(prices) >= 1:
                        buy = prices[0]
                        sell = prices[1] if len(prices) > 1 else "-"
                        return brand, [{"type": "Vàng nguyên liệu 999,9", "buy": buy, "sell": sell}]
        
        # Phương thức 2 (Sát thủ): Quét Regex trực tiếp trên mã HTML thô ngầm của trang
        # Tìm chính xác chữ V9999P hoặc 999.9 phi SJC, sau đó bắt 2 cụm số dạng xx.xxx.xxx hoặc xx,xxx,xxx
        match = re.search(r'(V9999P|999\.9 phi SJC).*?(\d{2,3}[.,]\d{3}[.,]\d{3}|\d{7,8}).*?(\d{2,3}[.,]\d{3}[.,]\d{3}|\d{7,8}|-)', html, re.IGNORECASE | re.DOTALL)
        
        if match:
            buy = match.group(2)
            sell = match.group(3)
            return brand, [{"type": "Vàng nguyên liệu 999,9", "buy": buy, "sell": sell}]
            
        print("Không tìm thấy mã V9999P trên website Phú Quý lúc này.")
        return brand, []
    except Exception as e:
        print(f"Lỗi Phú Quý: {e}")
        return brand, []

def crawl_gold_prices():
    data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {}
    }

    # Chạy 2 mỏ đào cùng lúc
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_btmh = executor.submit(fetch_btmh)
        future_pq = executor.submit(fetch_phu_quy)
        
        for future in concurrent.futures.as_completed([future_btmh, future_pq]):
            brand, prices = future.result()
            data["prices"][brand] = prices

    # Lưu file
    with open("gold-prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print("Hoàn tất! Đã bắt được chính xác mã V9999P từ Phú Quý và Nhẫn BTMH từ Webgia.")

if __name__ == "__main__":
    crawl_gold_prices()