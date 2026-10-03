import feedparser
import urllib.request
import urllib.parse
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Danh sách nguồn tin chuẩn theo đúng các danh mục trên giao diện TinMoi68
RSS_SOURCES = [
    { 'url': 'https://vnexpress.net/rss/thoi-su.rss', 'category': 'Thời sự' },
    { 'url': 'http://feeds.bbci.co.uk/news/world/rss.xml', 'category': 'Thế giới' },
    { 'url': 'https://vnexpress.net/rss/kinh-doanh.rss', 'category': 'Kinh doanh' },
    { 'url': 'https://vnexpress.net/rss/bat-dong-san.rss', 'category': 'Bất động sản' },
    { 'url': 'http://feeds.bbci.co.uk/news/technology/rss.xml', 'category': 'Công nghệ' },
    { 'url': 'http://feeds.bbci.co.uk/news/science_and_environment/rss.xml', 'category': 'Khoa học' },
    { 'url': 'https://vnexpress.net/rss/suc-khoe.rss', 'category': 'Sức khỏe' },
    { 'url': 'https://vnexpress.net/rss/the-thao.rss', 'category': 'Thể thao' },
    { 'url': 'https://vnexpress.net/rss/giai-tri.rss', 'category': 'Giải trí' },
    { 'url': 'https://vnexpress.net/rss/phap-luat.rss', 'category': 'Pháp luật' },
    { 'url': 'https://vnexpress.net/rss/giao-duc.rss', 'category': 'Giáo dục' },
    { 'url': 'https://vnexpress.net/rss/doi-song.rss', 'category': 'Đời sống' },
    { 'url': 'https://vnexpress.net/rss/du-lich.rss', 'category': 'Du lịch' }
]

FIREBASE_URL = "https://tinmoi68-default-rtdb.asia-southeast1.firebasedatabase.app/articles.json"

def translate_mymemory(text):
    """Hàm dịch tự động tiếng Anh sang tiếng Việt nếu nguồn tin là quốc tế"""
    if not text or len(text.strip()) == 0:
        return ""
    
    clean_text = text.strip()[:500]
    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean_text)}&langpair=en|vi"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            res = json.loads(response.read().decode('utf-8'))
            translated = res.get('responseData', {}).get('translatedText', '')
            if translated and "QUERY LIMIT" not in translated and "MYMEMORY WARNING" not in translated:
                return translated
    except Exception as e:
        print(f"Lỗi API dịch: {e}")
    
    return clean_text

def extract_full_article_content(article_url):
    """Mở liên kết bài gốc để cào các đoạn văn bản chi tiết"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(article_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Xóa các thành phần không cần thiết
            for tag in soup(['script', 'style', 'iframe', 'header', 'footer', 'nav']):
                tag.decompose()
                
            paragraphs = soup.find_all('p')
            full_text = []
            for p in paragraphs:
                txt = p.get_text().strip()
                if len(txt) > 40 and not txt.startswith("Copyright") and not txt.startswith("Follow"):
                    full_text.append(txt)
            
            return full_text[:8]
    except Exception as e:
        print(f"Không thể cào toàn văn từ {article_url}: {e}")
    return []

def fetch_and_post_news():
    print("🚀 Bắt đầu cào tin tức tự động theo đúng tất cả danh mục...")
    
    posted_count = 0
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")

    for source in RSS_SOURCES:
        feed = feedparser.parse(source['url'])
        category = source['category']
        print(f"\n📂 Đang xử lý danh mục: [{category}]")

        # Lấy 2 bài mới nhất cho mỗi danh mục
        for entry in feed.entries[:2]:
            link = entry.get('link', '')
            title_raw = entry.get('title', '')
            summary_raw = entry.get('summary', '') or entry.get('description', '')

            # Kiểm tra nếu nguồn là tiếng Anh thì dịch sang tiếng Việt
            if 'bbci.co.uk' in source['url']:
                title_vi = translate_mymemory(title_raw)
                excerpt_vi = translate_mymemory(summary_raw)
            else:
                title_vi = title_raw
                # Làm sạch HTML trong summary nếu từ nguồn VnExpress
                excerpt_soup = BeautifulSoup(summary_raw, 'html.parser')
                excerpt_vi = excerpt_soup.get_text().strip()

            print(f"  📄 Bài viết: {title_vi}")

            # Cào nội dung chi tiết bài viết
            paragraphs = extract_full_article_content(link)
            
            content_html = ""
            if paragraphs:
                translated_paragraphs = []
                for p_text in paragraphs:
                    if 'bbci.co.uk' in source['url']:
                        p_vi = translate_mymemory(p_text)
                    else:
                        p_vi = p_text
                        
                    if p_vi:
                        translated_paragraphs.append(f"<p class='mb-4 text-gray-800 dark:text-gray-200 leading-relaxed'>{p_vi}</p>")
                    time.sleep(0.3)
                content_html = "".join(translated_paragraphs)
            else:
                content_html = f"<p class='mb-4'>{excerpt_vi}</p>"

            content_html += f"<p class='mt-6 text-xs text-gray-500 italic border-t pt-3'>Nguồn tin gốc: <a href='{link}' target='_blank' class='text-blue-600 underline'>Xem bài gốc</a>. Tổng hợp bởi TinMoi68 Bot.</p>"

            # Lấy hình ảnh đại diện
            image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=800&q=80"
            if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                image_url = entry.media_thumbnail[0]['url']
            elif 'media_content' in entry and len(entry.media_content) > 0:
                image_url = entry.media_content[0]['url']
            else:
                # Tìm ảnh trong nội dung tóm tắt HTML nếu có
                img_soup = BeautifulSoup(summary_raw, 'html.parser')
                img_tag = img_soup.find('img')
                if img_tag and img_tag.get('src'):
                    image_url = img_tag.get('src')

            article_data = {
                "title": title_vi,
                "category": category, # Tên danh mục khớp hoàn toàn với danh mục trên menu web
                "readTime": "3 phút đọc",
                "image": image_url,
                "excerpt": excerpt_vi,
                "content": content_html,
                "date": date_str,
                "timestamp": int(time.time() * 1000)
            }

            # Đẩy dữ liệu bài viết lên Firebase
            req = urllib.request.Request(
                FIREBASE_URL,
                data=json.dumps(article_data).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            try:
                with urllib.request.urlopen(req) as response:
                    if response.status == 200:
                        print(f"  ✅ Đã đăng thành công vào mục [{category}]")
                        posted_count += 1
            except Exception as e:
                print(f"  ❌ Lỗi khi đăng bài: {e}")

    print(f"\n🎉 Hoàn tất! Đã cập nhật tổng cộng {posted_count} bài viết đầy đủ cho các danh mục.")

if __name__ == '__main__':
    fetch_and_post_news()
