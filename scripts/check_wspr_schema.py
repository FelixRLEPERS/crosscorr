import requests

url = "http://db1.wspr.live/"
params = {"query": "DESCRIBE wspr.rx"}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()  # Проверка на ошибки HTTP
    print(response.text)
except requests.exceptions.HTTPError as err:
    print(f"HTTP ошибка: {err}")
except requests.exceptions.RequestException as err:
    print(f"Ошибка соединения: {err}")
