import feedparser
import urllib.request
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from googletrans import Translator
from deep_translator import GoogleTranslator as DeepGoogleTranslator

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

py_translator = Translator()

def translate_text(text):
    """Hàm dịch Tiếng Việt mạnh mẽ với 2 cơ chế dự phòng"""
    if not text or len(text.strip()) == 0:
        return ""
    
    clean_text = text.strip()
    
    # Phương án dịch 1: googletrans
    try:
        res = py_translator.translate(clean_text, src='auto', dest='vi')
        if res and res.text:
            return res.text
    except Exception as e:
        pass

    # Phương án dịch 2 dự phòng: deep-translator
    try:
        res_deep = DeepGoogleTranslator(source='auto', target='vi').translate(clean_text[:4000])
        if res_deep:
            return res_deep
    except Exception as e:
        pass

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
            
            # Lấy 8 đoạn chính
            return full_text[:8]
    except Exception as e:
        print(f"Không thể cào toàn văn từ {article_url}: {e}")
    return []

def fetch_and_post_news():
    print("🚀 Bắt đầu cào và dịch bài viết sang Tiếng Việt...")
    
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
            
            # 1. Dịch Tiêu đề & Tóm tắt sang Tiếng Việt
            title_vi = translate_text(title_en)
            excerpt_vi = translate_text(summary_en)

            print(f"📄 Đang dịch bài: {title_vi}")

            # 2. Cào và Dịch toàn bộ nội dung chi tiết bài viết
            paragraphs_en = extract_full_article_content(link)
            
            content_html = ""
            if paragraphs_en:
                translated_paragraphs = []
                for p_en in paragraphs_en:
                    p_vi = translate_text(p_en)
                    if p_vi:
                        translated_paragraphs.append(f"<p class='mb-4 text-gray-800 dark:text-gray-200 leading-relaxed'>{p_vi}</p>")
                    time.sleep(0.3) # Nghỉ ngắn giữa các đoạn để không bị chặn IP
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
                        print(f"✅ Đã đăng bài Tiếng Việt: {title_vi}")
                        posted_count += 1
            except Exception as e:
                print(f"❌ Lỗi đẩy bài lên Firebase: {e}")

    print(f"🎉 Hoàn tất! Đã cập nhật {posted_count} bài viết Tiếng Việt mới lên TinMoi68.")

if __name__ == '__main__':
    fetch_and_post_news()
