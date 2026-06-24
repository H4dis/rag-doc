import requests
from pathlib import Path
import json
from datetime import datetime
from crawler import WebCrawler

API_URL = "http://localhost:8000"
CRAWLED_DIR = Path("data/raw/crawled")

class HybridRetriever:
    def __init__(self):
        self.crawler = WebCrawler(max_pages=10)

    def ask(self, question: str) -> str:
        print(f"🔍 Searching DB: {question}")

        # 1. first try API
        try:
            resp = requests.post(
                f"{API_URL}/ask",
                json={"question": question, "session_id": "hybrid"},
                timeout=10
            )
            result = resp.json()
            if result.get("source_count", 0) > 0:
                print(f"✅ Found in DB ({result['source_count']} sources)")
                return result["answer"]
        except Exception as e:
            print(f"⚠️ API error: {e}")

        # 2. check crawled files
        print("📂 Checking crawled files...")
        crawled_data = self.load_crawled_files()
        if crawled_data:
            print(f"✅ Found {len(crawled_data)} crawled pages")
            return self.answer_from_crawled(question, crawled_data)

        # 3. start live crawl
        print("🌐 Starting live crawl...")
        new_data = self.crawler.crawl("https://pnu.ac.ir")
        if new_data:
            print(f"✅ Crawled {len(new_data)} pages")
            return self.answer_from_crawled(question, new_data)

        return "❌ اطلاعاتی پیدا نشد."

    def load_crawled_files(self) -> list:
        all_data = []
        for json_file in CRAWLED_DIR.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
            except Exception as e:
                print(f"⚠️ Error reading {json_file.name}: {e}")
        return all_data

    def answer_from_crawled(self, question: str, data: list) -> str:
        answer = f"📝 پاسخ به '{question}':\n\n"
        for i, item in enumerate(data[:5], 1):
            title = item.get("title", "بدون عنوان")
            content = item.get("content", "")[:300]
            url = item.get("url", "")
            answer += f"{i}. {title}\n   {content}...\n   🔗 {url}\n\n"
        return answer

if __name__ == "__main__":
    retriever = HybridRetriever()
    q = input("❓ سوال: ")
    print(retriever.ask(q))