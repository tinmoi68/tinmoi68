import feedparser
import urllib.request
import json
import time
from datetime import datetime
from deep_translator import GoogleTranslator

# 1. Danh sách các nguồn báo quốc tế uy tín (RSS Feeds)
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

# URL Firebase Realtime Database của bạn
FIREBASE_URL = "https://tinmoi68-default-rtdb.asia-southeast1.firebasedatabase.app/articles.json"

translator = GoogleTranslator(source='auto', target='vi')

def translate_text(text):
    if not text:
        return ""
    try:
        return translator.translate(text[:4000]) # Giới hạn ký tự dịch
    except Exception as e:
        print(f"Lỗi dịch thuật: {e}")
        return text

def fetch_and_post_news():
    print("🚀 Bắt đầu quá trình lấy tin tức tự động...")
    
    posted_count = 0
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")

    for source in RSS_SOURCES:
        feed = feedparser.parse(source['url'])
        category = source['category']

        # Chỉ lấy 2 bài viết mới nhất từ mỗi nguồn
        for entry in feed.entries[:2]:
            title_en = entry.get('title', '')
            summary_en = entry.get('summary', '') or entry.get('description', '')
            
            # Dịch tiêu đề và tóm tắt sang tiếng Việt
            title_vi = translate_text(title_en)
            excerpt_vi = translate_text(summary_en)

            # Lấy ảnh đại diện nếu có
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
                "content": f"<p>{excerpt_vi}</p><p><i>(Bài viết được tổng hợp và dịch tự động từ nguồn tin quốc tế BBC News).</i></p>",
                "date": date_str,
                "timestamp": int(time.time() * 1000)
            }

            # Đẩy bài viết lên Firebase
            req = urllib.request.Request(
                FIREBASE_URL,
                data=json.dumps(article_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req) as response:
                    if response.status == 200:
                        print(f"✅ Đã đăng thành công: {title_vi}")
                        posted_count += 1
            except Exception as e:
                print(f"❌ Lỗi đẩy bài lên Firebase: {e}")

    print(f"🎉 Hoàn tất! Đã tự động cập nhật {posted_count} bài viết mới lên TinMoi68.")

if __name__ == '__main__':
    fetch_and_post_news()
