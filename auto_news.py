import feedparser
import urllib.request
import urllib.parse
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Các nguồn RSS báo quốc tế
RSS_SOURCES = [
    {
        'url': 'http://feeds.bbci.co.uk/news/world/rss.xml',
        'category': 'Thế giới'
    },
    {
        'url': 'http://feeds.bbci.co.uk/news/technology/rss.xml',
        'category': 'Công nghệ'
    },
    {
        'url': 'http://feeds.bbci.co.uk/news/business/rss.xml',
        'category': 'Kinh doanh'
    },
    {
        'url': 'http://feeds.bbci.co.uk/news/science_and_environment/rss.xml',
        'category': 'Khoa học'
    }
]

FIREBASE_URL = "https://tinmoi68-default-rtdb.asia-southeast1.firebasedatabase.app/articles.json"

def translate_mymemory(text):
    """Dịch bằng API MyMemory cực kỳ ổn định, không bị block IP"""
    if not text or len(text.strip()) == 0:
        return ""
    
    clean_text = text.strip()[:500] # Giới hạn độ dài mỗi đoạn để dịch nhanh
    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean_text)}&langpair=en|vi"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode('utf-8'))
            translated = res.get('responseData', {}).get('translatedText', '')
            if translated and "QUERY LENGTH LIMIT EXCEEDED" not in translated:
                return translated
    except Exception as e:
        print(f"Lỗi API dịch MyMemory: {e}")
    
    return clean_text

def extract_full_article_content(article_url):
    """Mở link bài gốc và cào các đoạn văn bản chính"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            full_text = []
            for p in paragraphs:
                txt = p.get_text().strip()
                if len(txt) > 40 and not txt.startswith("Copyright") and not txt.startswith("Follow"):
                    full_text.append(txt)
            
            return full_text[:6] # Lấy 6 đoạn văn bản chính
    except Exception as e:
        print(f"Không thể cào toàn văn từ {article_url}: {e}")
    return []

def fetch_and_post_news():
    print("🚀 Bắt đầu cào và dịch bài viết sang Tiếng Việt bằng MyMemory API...")
    
    posted_count = 0
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")

    for source in RSS_SOURCES:
        feed = feedparser.parse(source['url'])
        category = source['category']

        for entry in feed.entries[:1]: # Lấy 1 bài mới nhất từ mỗi chuyên mục
            link = entry.get('link', '')
            title_en = entry.get('title', '')
            summary_en = entry.get('summary', '') or entry.get('description', '')
            
            # 1. Dịch Tiêu đề & Tóm tắt
            title_vi = translate_mymemory(title_en)
            excerpt_vi = translate_mymemory(summary_en)

            print(f"📄 Đang xử lý: {title_vi}")

            # 2. Cào và Dịch từng đoạn nội dung chi tiết
            paragraphs_en = extract_full_article_content(link)
            
            content_html = ""
            if paragraphs_en:
                translated_paragraphs = []
                for p_en in paragraphs_en:
                    p_vi = translate_mymemory(p_en)
                    if p_vi:
                        translated_paragraphs.append(f"<p class='mb-4 text-gray-800 dark:text-gray-200 leading-relaxed'>{p_vi}</p>")
                    time.sleep(0.5) # Chờ 0.5s giữa các đoạn
                content_html = "".join(translated_paragraphs)
            else:
                content_html = f"<p class='mb-4'>{excerpt_vi}</p>"

            content_html += f"<p class='mt-6 text-xs text-gray-500 italic border-t pt-3'>Nguồn tin gốc: <a href='{link}' target='_blank' class='text-blue-600 underline'>BBC News</a>. Tổng hợp & dịch tự động bởi TinMoi68 Bot.</p>"

            # 3. Lấy hình ảnh bài viết
            image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80"
            if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                image_url = entry.media_thumbnail[0]['url']
            elif 'media_content' in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0]['url']

            article_data = {
                "title": title_vi,
                "category": category,
                "readTime": "3 phút đọc",
                "image": image_url,
                "excerpt": excerpt_vi,
                "content": content_html,
                "date": date_str,
                "timestamp": int(time.time() * 1000)
            }

            # 4. Đẩy bài viết lên Firebase Database
            req = urllib.request.Request(
                FIREBASE_URL,
                data=json.dumps(article_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req) as response:
                    if response.status == 200:
                        print(f"✅ Đã đăng thành công bài Tiếng Việt: {title_vi}")
                        posted_count += 1
            except Exception as e:
                print(f"❌ Lỗi đẩy bài lên Firebase: {e}")

    print(f"🎉 Hoàn tất! Đã cập nhật {posted_count} bài viết Tiếng Việt mới lên TinMoi68.")

if __name__ == '__main__':
    fetch_and_post_news()
