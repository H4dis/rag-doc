import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
import json
import time
import hashlib
from typing import Set, List, Dict, Optional
from datetime import datetime
import re

# ========== تنظیمات ==========
DATA_PATH = Path("data/raw/crawled")
DATA_PATH.mkdir(parents=True, exist_ok=True)


class WebCrawler:
    """خزنده وب برای استخراج محتوای سایت‌های دانشگاهی"""

    def __init__(self, max_pages: int = 50, delay: float = 1.0):
        self.max_pages = max_pages
        self.delay = delay  # تأخیر بین درخواست‌ها (احترام به سرور)
        self.visited: Set[str] = set()
        self.all_content: List[Dict] = []

        # هدرهای مرورگر واقعی
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def is_valid_url(self, url: str, base_domain: str) -> bool:
        """بررسی اعتبار URL برای خزش"""
        # حذف لینک‌های تکراری و بی‌ربط
        invalid_patterns = [
            '#', 'javascript:', 'mailto:', 'tel:', 'wp-content',
            'feed', 'rss', 'xml', '.pdf', '.jpg', '.png', '.zip'
        ]
        for pattern in invalid_patterns:
            if pattern in url.lower():
                return False

        # فقط لینک‌های دامنه اصلی
        parsed = urlparse(url)
        return base_domain in parsed.netloc and url not in self.visited

    def clean_text(self, text: str) -> str:
        """پاکسازی متن از فاصله‌ها و کاراکترهای اضافی"""
        # حذف فاصله‌های اضافی
        text = re.sub(r'\s+', ' ', text)
        # حذف خطوط خالی
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def extract_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """استخراج محتوای مفید از صفحه"""

        # پیدا کردن عنوان صفحه
        title = ""
        if soup.title:
            title = soup.title.string
        elif soup.find('h1'):
            title = soup.find('h1').get_text()

        # حذف تگ‌های غیرضروری
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                         'iframe', 'noscript', 'meta', 'link']):
            tag.decompose()

        # حذف کلاس‌های تبلیغاتی و منوها
        for tag in soup.find_all(class_=re.compile('menu|nav|sidebar|footer|ad|banner')):
            tag.decompose()

        # استخراج متن اصلی (اولویت با main یا article)
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            text = soup.get_text(separator='\n', strip=True)

        # پاکسازی متن
        text = self.clean_text(text)

        # استخراج متادیتا
        meta_desc = ""
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_desc_tag:
            meta_desc = meta_desc_tag.get('content', '')

        keywords = ""
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag:
            keywords = keywords_tag.get('content', '')

        # پیدا کردن تاریخ انتشار
        publish_date = ""
        date_patterns = [
            soup.find('meta', {'property': 'article:published_time'}),
            soup.find('time'),
            soup.find(class_=re.compile('date|time'))
        ]
        for pattern in date_patterns:
            if pattern:
                publish_date = pattern.get('content') or pattern.get('datetime') or pattern.get_text()
                break

        return {
            "url": url,
            "title": title.strip(),
            "content": text[:8000],  # محدود کردن طول
            "meta_description": meta_desc,
            "keywords": keywords,
            "publish_date": publish_date,
            "content_length": len(text),
            "crawled_at": datetime.now().isoformat()
        }

    def get_all_links(self, soup: BeautifulSoup, base_url: str, base_domain: str) -> List[str]:
        """استخراج همه لینک‌های داخلی صفحه"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)

            if self.is_valid_url(full_url, base_domain):
                # حذف پارامترهای اضافی از URL
                parsed = urlparse(full_url)
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean_url not in self.visited:
                    links.append(clean_url)

        return links

    def crawl(self, start_url: str, save_progress: bool = True):
        """شروع خزش از یک URL پایه"""

        print(f"🕷️ شروع خزش: {start_url}")
        print(f"📊 حداکثر صفحات: {self.max_pages}")

        to_visit = [start_url]
        base_domain = urlparse(start_url).netloc

        while to_visit and len(self.visited) < self.max_pages:
            url = to_visit.pop(0)

            if url in self.visited:
                continue

            print(f"🔍 [{len(self.visited) + 1}/{self.max_pages}] {url}")

            try:
                # ارسال درخواست
                response = requests.get(url, headers=self.headers, timeout=15)
                if response.status_code != 200:
                    print(f"   ⚠️ وضعیت: {response.status_code}")
                    self.visited.add(url)
                    continue

                # پردازش صفحه
                soup = BeautifulSoup(response.text, 'html.parser')

                # استخراج محتوا
                content = self.extract_content(soup, url)
                if content['content'] and len(content['content']) > 100:  # حداقل محتوا
                    self.all_content.append(content)
                    print(f"   ✅ ذخیره شد ({len(content['content'])} کاراکتر)")
                else:
                    print(f"   ⚠️ محتوای کافی نیست")

                # پیدا کردن لینک‌های جدید
                new_links = self.get_all_links(soup, url, base_domain)
                to_visit.extend(new_links)
                self.visited.add(url)

                # ذخیره موقت هر 10 صفحه
                if save_progress and len(self.all_content) % 10 == 0:
                    self.save_to_json(f"crawled_{base_domain}_partial.json")

                # تأخیر برای احترام به سرور
                time.sleep(self.delay)

            except requests.exceptions.Timeout:
                print(f"   ❌ timeout")
                self.visited.add(url)
            except Exception as e:
                print(f"   ❌ خطا: {str(e)[:50]}")
                self.visited.add(url)

        # ذخیره نهایی
        self.save_to_json(f"crawled_{base_domain}.json")

        # گزارش نهایی
        print(f"\n{'=' * 50}")
        print(f"✅ خزش کامل شد!")
        print(f"📄 صفحات بازدید شده: {len(self.visited)}")
        print(f"💾 محتوای ذخیره شده: {len(self.all_content)} صفحه")
        print(f"📁 مسیر ذخیره: {DATA_PATH}")
        print(f"{'=' * 50}")

        return self.all_content

    def save_to_json(self, filename: str):
        """ذخیره نتایج در فایل JSON"""
        filepath = DATA_PATH / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.all_content, f, ensure_ascii=False, indent=2)
        print(f"   💾 ذخیره شد: {filepath}")

    def crawl_sitemap(self, sitemap_url: str):
        """خزش از طریق فایل sitemap.xml (سریع‌تر)"""
        print(f"🗺️ خواندن sitemap: {sitemap_url}")

        try:
            response = requests.get(sitemap_url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'xml')

            # استخراج همه URLs از sitemap
            urls = []
            for loc in soup.find_all('loc'):
                url = loc.get_text()
                if url not in self.visited:
                    urls.append(url)

            print(f"📊 تعداد URLs پیدا شده: {len(urls)}")

            # خزش به ترتیب
            for url in urls[:self.max_pages]:
                if url not in self.visited:
                    self.crawl_page(url)
                    time.sleep(self.delay)

            self.save_to_json(f"sitemap_crawled.json")

        except Exception as e:
            print(f"❌ خطا در خواندن sitemap: {e}")

    def crawl_page(self, url: str) -> Optional[Dict]:
        """خزش یک صفحه خاص"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                content = self.extract_content(soup, url)
                if content['content']:
                    self.all_content.append(content)
                    self.visited.add(url)
                    return content
        except Exception as e:
            print(f"   ❌ خطا: {e}")
        return None


# ========== توابع کمکی ==========

def crawl_university_sites():
    """خزش سایت‌های مرتبط با دانشگاه"""

    # لیست سایت‌های مفید برای خزش
    sites = [
        "https://pnu.ac.ir",
        "https://alborz.pnu.ac.ir",
        "https://reg.pnu.ac.ir",
        "https://lms.alborz.pnu.ac.ir"
    ]

    crawler = WebCrawler(max_pages=30, delay=1.5)

    for site in sites:
        print(f"\n🚀 شروع خزش: {site}")
        try:
            content = crawler.crawl(site)
            print(f"✅ {len(content)} صفحه از {site} ذخیره شد")
        except Exception as e:
            print(f"❌ خطا در خزش {site}: {e}")


def crawl_specific_pages(urls: List[str]):
    """خزش صفحات خاص (مثل صفحات راهنما)"""
    crawler = WebCrawler(max_pages=len(urls), delay=1)

    for url in urls:
        print(f"🔍 خزش: {url}")
        crawler.crawl_page(url)
        time.sleep(0.5)

    crawler.save_to_json("specific_pages.json")
    return crawler.all_content


def merge_crawled_data():
    """ادغام تمام فایل‌های خزش شده"""
    all_data = []

    for json_file in DATA_PATH.glob("*.json"):
        print(f"📄 خواندن: {json_file.name}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_data.extend(data)

    # حذف تکراری‌ها بر اساس URL
    unique_data = {}
    for item in all_data:
        url = item.get('url', '')
        if url not in unique_data:
            unique_data[url] = item

    # ذخیره نهایی
    final_path = DATA_PATH / "all_crawled_data.json"
    with open(final_path, 'w', encoding='utf-8') as f:
        json.dump(list(unique_data.values()), f, ensure_ascii=False, indent=2)

    print(f"\n✅ ادغام کامل شد!")
    print(f"📊 کل صفحات: {len(unique_data)}")
    print(f"💾 ذخیره در: {final_path}")

    return list(unique_data.values())


# ========== اجرا ==========
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Web Crawler for University Sites')
    parser.add_argument('--url', type=str, help='URL برای شروع خزش')
    parser.add_argument('--sitemap', type=str, help='URL فایل sitemap.xml')
    parser.add_argument('--max', type=int, default=30, help='حداکثر صفحات')
    parser.add_argument('--merge', action='store_true', help='ادغام فایل‌های خزش شده')

    args = parser.parse_args()

    if args.merge:
        merge_crawled_data()
    elif args.sitemap:
        crawler = WebCrawler(max_pages=args.max)
        crawler.crawl_sitemap(args.sitemap)
    elif args.url:
        crawler = WebCrawler(max_pages=args.max)
        crawler.crawl(args.url)
    else:
        # حالت پیش‌فرض: خزش سایت اصلی
        print("🚀 شروع خزش پیش‌فرض...")
        crawl_university_sites()