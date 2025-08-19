from fastapi import FastAPI, HTTPException, Request
from typing import Union
import requests
from lxml import html
import re
import os
from pymongo import MongoClient
from datetime import datetime
from pydantic import BaseModel
import time
from fastapi.responses import JSONResponse
app = FastAPI()

# MongoDB setup
MONGO_URI="mongodb+srv://ruttvikpadharaactowiz:<db_password>@cluster0.ztutrdw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["amazon_api"]
key_table = db["key_tables"]
logs_table = db["logs_table"]

HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'device-memory': '8',
        'downlink': '7.4',
        'dpr': '1',
        'ect': '4g',
        'priority': 'u=0, i',
        'referer': 'https://www.amazon.in/',
        'rtt': '150',
        'sec-ch-device-memory': '8',
        'sec-ch-dpr': '1',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"10.0.0"',
        'sec-ch-viewport-width': '1366',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'viewport-width': '1366',
    }
cookies = {
        'csm-sid': '737-3972249-5354157',
        'x-amz-captcha-1': '1754313054312189',
        'x-amz-captcha-2': 'KTNCRARNl2YprTJ7OjVfgg==',
        'session-id': '257-4589919-6523722',
        'i18n-prefs': 'INR',
        'lc-acbin': 'en_IN',
        'ubid-acbin': '258-7188680-0550234',
        'session-id-time': '2082787201l',
        'csm-hit': 'tb:WQJ2XJ43PDNBCEP2KG0D+s-WQJ2XJ43PDNBCEP2KG0D|1754373569217&t:1754373569217&adb:adblk_no',
        'rxc': 'AGpw8VOGv1byFizf6Xc',
        'session-token': 'SaBo7TXoWnu6zO71N+8T1v7UOHp8xpGdtG0UjqLriyXtzB/XoIrWSTpocKXW3NGo3eWYwfbi3WiNyqCafNLO30j3eI08cdq+a/H4Hx1F+YT2FXdnUYSy56YrLsPczcoJ3EAS2nP4E0qcwO47pxDGoRSXkRMjBhDGtF3DthgDccvCnuvN5Kzvv/DUOmf6ApLGm6vvMzkRv0tnzR6n6UF4R2IZNf41XRDvguHmvOqJiOqaFP3yNvCSN6EngAJnHR/ql0cgQn/zOQmyUbr/htSoq18LF4lhJ+f7jYp1C4jVGJn6NIMeN7L8/zbxJJ/WSpsSIbr/psTr2TUmEcQwp+drfX+DfodOWVNh',
    }

class SearchRequest(BaseModel):
    product_name: str
    api_key: str

# Cleaning helpers
def clean_price(value: str) -> Union[int, None]:
    try:
        return int(value.replace(",", "").replace("\u20b9", "").strip())
    except:
        return None

def clean_rating(value: str) -> Union[float, None]:
    try:
        return float(value.strip().split(" ")[0])
    except:
        return None

def clean_total_ratings(value: str) -> Union[int, None]:
    try:
        return int(value.replace(",", "").strip())
    except:
        return None

def clean_discount(discount_str):
    try:
        match = re.search(r'\d+', discount_str)
        return f"{match.group()}%" if match else None
    except:
        return None
@app.post("/Product_name_search")
def search_products(request: Request, body: SearchRequest) -> dict:
    product_name = body.product_name
    api_key = body.api_key
    start_time = time.time()
    request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_ip = request.client.host

    key_data = key_table.find_one({"key": api_key})

    execution_time = round(time.time() - start_time, 2)

    # Invalid API key
    if not key_data:
        logs_table.insert_one({
            "ip": client_ip,
            "params": {"url": product_name, "api": api_key},
            "request_time": request_time,
            "status_code": 401,
            "key": api_key,
            "response": {
                "query_params": {"url": product_name, "api_key": api_key},
                "success": False,
                "message": "API key is not valid.",
                "execution_time": execution_time,
                "data": None
            }
        })
        return JSONResponse(
    status_code=401,
    content={
        "status_code": 401,
        "message": "API key is not valid."
    }
)

    # Inactive key
    if not key_data.get("status", False):
        logs_table.insert_one({
            "ip": client_ip,
            "params": {"url": product_name, "api": api_key},
            "request_time": request_time,
            "status_code": 403,
            "key": api_key,
            "response": {
                "query_params": {"url": product_name, "api_key": api_key},
                "success": False,
                "message": "API key is not active.",
                "execution_time": execution_time,
                "data": None
            }
        })
        return JSONResponse(
    status_code=403,
    content={
        "status_code": 403,
        "message": "API key is not active."
    }
)

    # Usage limit exceeded
    if key_data["usage"] >= key_data["limit"]:
        logs_table.insert_one({
            "ip": client_ip,
            "params": {"url": product_name, "api": api_key},
            "request_time": request_time,
            "status_code": 429,
            "key": api_key,
            "response": {
                "query_params": {"url": product_name, "api_key": api_key},
                "success": False,
                "message": "API key usage limit exceeded.",
                "execution_time": execution_time,
                "data": None
            }
        })
        return JSONResponse(
    status_code=429,
    content={
        "status_code": 429,
        "message": "API key usage limit exceeded."
    }
)

    # Request Amazon
    search_url = f"https://www.amazon.in/s?k={product_name.replace(' ', '+')}"
    response = requests.get(search_url, headers=HEADERS, cookies=cookies)
    status_code = response.status_code
    execution_time = round(time.time() - start_time, 2)

    if status_code != 200:
        logs_table.insert_one({
            "ip": client_ip,
            "params": {"url": product_name, "api": api_key},
            "request_time": request_time,
            "status_code": status_code,
            "key": api_key,
            "response": {
                "query_params": {"url": product_name, "api_key": api_key},
                "success": False,
                "message": "Failed to fetch search results",
                "execution_time": execution_time,
                "data": None
            }
        })
        return {"status_code": status_code, "data": [], "message": "Failed to fetch search results"}

    # Parse Results
    tree = html.fromstring(response.text)
    product_elements = tree.xpath('//div[@data-component-type="s-search-result"]')

    if not product_elements:
        logs_table.insert_one({
            "ip": client_ip,
            "params": {"url": product_name, "api": api_key},
            "request_time": request_time,
            "status_code": 200,
            "key": api_key,
            "response": {
                "query_params": {"url": product_name, "api_key": api_key},
                "success": False,
                "message": "Product not found",
                "execution_time": execution_time,
                "data": None
            }
        })
        return {"status_code": 200, "data": [], "message": "Product not found"}

    results = {}
    for i, element in enumerate(product_elements[:10], start=1):
        asin = element.get("data-asin")
        price_raw = element.xpath('.//span[@class="a-price-whole"]/text()')
        mrp_raw = element.xpath('.//span[@class="a-price a-text-price"]/span[@class="a-offscreen"]/text()')
        discount_raw = element.xpath('.//span[contains(text(), "% off")]/text()')
        rating_raw = element.xpath('.//span[@class="a-icon-alt"]/text()')
        total_ratings_raw = element.xpath('.//span[@class="a-size-base s-underline-text"]/text()')
        brand = element.xpath('.//img[@class="s-image"]/@alt')
        image_url = element.xpath('.//img[@class="s-image"]/@src')
        delivery_full = element.xpath('.//span[contains(@aria-label, "delivery")]')
        is_prime = bool(element.xpath('.//i[@aria-label="Amazon Prime"]'))
        symbol_raw = element.xpath('.//span[@class="a-price-symbol"]/text()') 

        results[str(i)] = {
            "title": brand[0] if brand else "N/A",
            "currency": symbol_raw[0] if symbol_raw else "₹",
            "price": clean_price(price_raw[0]) if price_raw else "N/A",
            "mrp": clean_price(mrp_raw[0]) if mrp_raw else "N/A",
            "discount": clean_discount(discount_raw[0]) if discount_raw else "N/A",
            "rating": clean_rating(rating_raw[0]) if rating_raw else "N/A",
            "total_ratings": clean_total_ratings(total_ratings_raw[0]) if total_ratings_raw else "N/A",
            "prime": is_prime,
            "delivery_date": " ".join(delivery_full[0].itertext()).strip() if delivery_full else "N/A",
            "product_url": f"https://www.amazon.in/dp/{asin}" if asin else "N/A",
            "image_url": image_url[0] if image_url else "N/A"
        }

    key_table.update_one({"key": api_key}, {"$inc": {"usage": 1}})

    logs_table.insert_one({
        "ip": client_ip,
        "params": {"url": product_name, "api": api_key},
        "request_time": request_time,
        "status_code": 200,
        "key": api_key,
        "response": {
            "query_params": {"url": product_name, "api_key": api_key},
            "success": True,
            "message": "Product info fetched successfully",
            "execution_time": execution_time,
            "data": results
        }
    })

    return  { 
            "query_params": {"url": product_name, "api_key": api_key},
            "success": True,
            "message": "Product info fetched successfully",
            "execution_time": execution_time,
            "data": results
    }