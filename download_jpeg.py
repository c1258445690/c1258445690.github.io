import os
import re
import urllib.request
from urllib.parse import urlparse

POSTS_DIR = "_posts"
IMAGE_DIR = "assets/images"

JPEG_URL_RE = re.compile(
    r"https://cdn.nlark.com/yuque/[^\s\)\"']+\.jpeg",
    re.IGNORECASE,
)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def download(url, save_dir):
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    local_path = os.path.join(save_dir, filename)

    if os.path.exists(local_path):
        print(f"[skip] {filename}")
        return filename

    print(f"[download] {url}")
    urllib.request.urlretrieve(url, local_path)
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
            if name.endswith(".md"):
                process_md(os.path.join(root, name))

    print("\nAll done.")

if __name__ == "__main__":
    main()
