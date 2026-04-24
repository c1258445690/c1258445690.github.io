import os
import re
import urllib.request
from urllib.parse import urlparse
import subprocess

POSTS_DIR = "_posts"
IMAGE_DIR = "assets/images"

JPEG_URL_RE = re.compile(
    r"https://cdn.nlark.com/yuque/[^\s\)\"']+\.png",
    re.IGNORECASE,
)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# 下载,保存到本地
def download(url, save_dir):
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    local_path = os.path.join(save_dir, filename)

    if os.path.exists(local_path):
        print(f"[skip] {filename}")
        return filename
    print(f"[download] {url}")
    urllib.request.urlretrieve(url, local_path)
    filename=compress_png(local_path,filename)
    return filename
# 压缩png,返回新的文件名称
def compress_png(local_path,filename):
    from PIL import Image

    if local_path.endswith(".png"):
        img = Image.open(local_path)
        # 转成 RGB（如果原图有透明通道，下面会说怎么处理）
        img = img.convert("RGB")
        webpfile=local_path[:-len(".png")]+".webp"
        filename=filename[:-len(".png")]+".webp"
        img.save(
            webpfile,
            format="WEBP",
            quality=80,   # 0-100，越低体积越小
            method=6      # 0-6，压缩强度，6最高
        )
        os.remove(local_path)
        return filename
    else:
        return filename
def process_md(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    urls = set(JPEG_URL_RE.findall(content))
    if not urls:
        return

    print(f"\nProcessing {md_path}")
    for url in urls:
        filename = download(url, IMAGE_DIR)
        new_url = f"/assets/images/{filename}"
        content = content.replace(url, new_url)
        print(f"Replaced {url} with {new_url}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    
def main():
    ensure_dir(IMAGE_DIR)

    for root, _, files in os.walk(POSTS_DIR):
        for name in files:
            if name.endswith("2026-04-24-数据结构.md"):
                process_md(os.path.join(root, name))

    print("\nAll done.")

if __name__ == "__main__":
    main()
