import feedparser
import urllib.request
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from deep_translator import GoogleTranslator

# Nguồn tin tức quốc tế
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
translator = GoogleTranslator(source='auto', target='vi')

def translate_text(text):
    if not text or len(text.strip()) == 0:
        return ""
    try:
        # Cắt thành từng đoạn ngắn để dịch không bị lỗi giới hạn ký tự
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        translated_chunks = [translator.translate(c) for c in chunks]
        return " ".join(translated_chunks)
    except Exception as e:
        print(f"Lỗi dịch thuật: {e}")
        return text

def extract_full_article_content(article_url):
    """Mở link bài gốc và cào toàn bộ các đoạn văn bản (paragraphs)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # Lấy tất cả các thẻ p nằm trong nội dung bài báo
            paragraphs = soup.find_all('p')
            full_text = []
            for p in paragraphs:
                txt = p.get_text().strip()
                # Lọc bỏ các đoạn ngắn hoặc quảng cáo điều hướng
                if len(txt) > 40 and not txt.startswith("Copyright") and not txt.startswith("Follow"):
                    full_text.append(txt)
            
            # Chỉ lấy khoảng 8 - 12 đoạn văn bản chính của bài báo
            return full_text[:12]
    except Exception as e:
        print(f"Không thể cào toàn văn từ {article_url}: {e}")
    return []

def fetch_and_post_news():
    print("🚀 Bắt đầu lấy tin tức và cào toàn bộ nội dung chi tiết...")
    
    posted_count = 0
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")

    for source in RSS_SOURCES:
        feed = feedparser.parse(source['url'])
        category = source['category']

        for entry in feed.entries[:2]:
            link = entry.get('link', '')
            title_en = entry.get('title', '')
            summary_en = entry.get('summary', '') or entry.get('description', '')
            
            # 1. Dịch tiêu đề và tóm tắt
            title_vi = translate_text(title_en)
            excerpt_vi = translate_text(summary_en)

            # 2. Cào toàn bộ nội dung chi tiết bài viết từ Link gốc
            print(f"📄 Đang cào toàn văn bài viết: {title_en}...")
            paragraphs_en = extract_full_article_content(link)
            
            content_html = ""
            if paragraphs_en:
                translated_paragraphs = []
                for p_en in paragraphs_en:
                    p_vi = translate_text(p_en)
                    if p_vi:
                        translated_paragraphs.append(f"<p class='mb-4'>{p_vi}</p>")
                content_html = "".join(translated_paragraphs)
            else:
                content_html = f"<p class='mb-4'>{excerpt_vi}</p>"

            content_html += f"<p class='mt-6 text-xs text-gray-500 italic'>Nguồn tin gốc: <a href='{link}' target='_blank' class='text-blue-600 underline'>BBC News</a>. Dịch tự động bởi TinMoi68 Bot.</p>"

            # 3. Lấy hình ảnh bài viết
            image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80"
            if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                image_url = entry.media_thumbnail[0]['url']
            elif 'media_content' in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0]['url']

            article_data = {
                "title": title_vi,
                "category": category,
                "readTime": "4 phút đọc",
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
                        print(f"✅ Đã đăng bài chi tiết: {title_vi}")
                        posted_count += 1
            except Exception as e:
                print(f"❌ Lỗi đẩy bài lên Firebase: {e}")

    print(f"🎉 Hoàn tất! Đã cập nhật {posted_count} bài viết có đầy đủ nội dung.")

if __name__ == '__main__':
    fetch_and_post_news()
