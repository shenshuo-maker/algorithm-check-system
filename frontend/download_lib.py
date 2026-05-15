import requests
import os

# 创建 lib 文件夹
if not os.path.exists("lib"):
    os.makedirs("lib")

# 下载 Vue（勿用 registry.npmmirror.com/vue@3/dist/...，会返回 NOT_FOUND 的 JSON）
url_vue = "https://cdn.jsdelivr.net/npm/vue@3.5.13/dist/vue.global.prod.js"
r = requests.get(url_vue, timeout=120)
r.raise_for_status()
with open("lib/vue.global.prod.js", "wb") as f:
    f.write(r.content)

# 下载 Element Plus JS
url_ep_js = "https://registry.npmmirror.com/element-plus@2/dist/index.full.js"
r = requests.get(url_ep_js)
with open("lib/index.full.js", "wb") as f:
    f.write(r.content)

# 下载 Element Plus CSS
url_ep_css = "https://registry.npmmirror.com/element-plus@2/dist/index.css"
r = requests.get(url_ep_css)
with open("lib/index.css", "wb") as f:
    f.write(r.content)

print("下载完成！")