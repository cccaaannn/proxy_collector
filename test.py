import requests

proxy = "1.65.196.114:1080"
proxy_with_schema = {"http":f"socks5h://{proxy}", "https":f"socks5h://{proxy}"}

res = requests.get("http://httpbin.org/ip", proxies=proxy_with_schema, timeout=5, verify=False)

print(res.json()['origin'])
