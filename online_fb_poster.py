import requests
from bs4 import BeautifulSoup
import time
import os

# ==========================================
# CONFIGURATION
# ==========================================

# Youm7 Giza News Tag (the original news source)
YOUM7_GIZA_URL = "https://www.youm7.com/Tags/Index?id=9385&tag=%D9%85%D8%AD%D8%A7%D9%81%D8%B8%D8%A9-%D8%A7%D9%84%D8%AC%D9%8A%D8%B2%D8%A9"

# Facebook Graph API Configuration
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "EAALwDOfTyC0BQ1JP4NZCGJFiqYwOhSk4Tg23UXo8ueeTLd5qPtnTi07HlnTpls5WEEWCcQRZA2wStrFDOCVXa5ZBjztCNArcGTZBBrkZADRm9oF1typwGgh3YYnaVvDKV2iVgajZCJ1CdPll6YBCNgZCDZAYueiVPkPF9uS7C5sjBcRvHZCQN8naCGDeYquHEQx0OrZAwlXmsKSXxj5yaw5G3VQMVmyDSE4vvlWo71ZB6aN2aUb")

# File to keep track of posted URLs so we don't post duplicates
POSTED_URLS_FILE = "posted_urls.txt"

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_posted_urls():
    """Load previously posted URLs to avoid duplicates."""
    if not os.path.exists(POSTED_URLS_FILE):
        return set()
    with open(POSTED_URLS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_posted_url(url):
    """Save a successfully posted URL."""
    with open(POSTED_URLS_FILE, 'a', encoding='utf-8') as f:
        f.write(url + "\n")

def fetch_latest_news():
    """Fetch the latest Giza news from Youm7."""
    print(f"Fetching Giza news from Youm7...")
    articles = []
    session = requests.Session()
    
    try:
        response = session.get(YOUM7_GIZA_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get latest 5 news items
        news_items = soup.find_all('div', class_='col-xs-12 bigOneSec', limit=5)
        
        for item in news_items:
            link_tag = item.find('a')
            if not link_tag: continue
            article_url = "https://www.youm7.com" + link_tag['href']
            
            try:
                art_response = session.get(article_url, headers=HEADERS, timeout=15)
                art_soup = BeautifulSoup(art_response.content, 'html.parser')
                
                title_tag = art_soup.find('h1')
                if not title_tag: continue
                title = title_tag.text.strip()
                
                # Get summary from article body
                content_div = art_soup.find('div', id='articleBody')
                summary = ""
                if content_div:
                    paragraphs = content_div.find_all('p')
                    summary = "\n".join([p.text.strip() for p in paragraphs[:2] if p.text.strip()])
                
                articles.append({
                    'title': title,
                    'summary': summary,
                    'url': article_url
                })
                print(f"-> Found: {title[:50]}...")
                time.sleep(2)
                
            except Exception as e:
                print(f"Error fetching article: {e}")
                
    except Exception as e:
        print(f"Error fetching Youm7 page: {e}")
        
    return articles

def post_to_facebook(article):
    """Post the article to Facebook via Graph API."""
    print(f"Posting to Facebook: {article['title'][:50]}...")
    
    post_url = "https://graph.facebook.com/v19.0/me/feed"
    
    message = f"📰 {article['title']}\n\n{article['summary']}\n\nاقرأ المزيد: {article['url']}\n\n#اخبار_الجيزة #بشتيل"
    
    payload = {
        'message': message,
        'link': article['url'],
        'access_token': FB_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(post_url, data=payload)
        result = response.json()
        
        if response.status_code == 200 and 'id' in result:
            print(f"SUCCESS: Posted! Post ID: {result['id']}")
            return True
        else:
            print(f"FAILED: {result}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# ==========================================
# MAIN SCRIPT
# ==========================================

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=== Youm7 Giza News -> Facebook Auto-Poster ===")
    
    if not FB_ACCESS_TOKEN or "YOUR" in FB_ACCESS_TOKEN:
        print("ERROR: Please configure FB_ACCESS_TOKEN.")
        return

    posted_urls = load_posted_urls()
    latest_articles = fetch_latest_news()
    
    if not latest_articles:
        print("No articles found.")
        return
    
    print(f"\nFound {len(latest_articles)} articles.")
        
    # Post oldest first
    latest_articles.reverse()
    
    posts_made = 0
    for article in latest_articles:
        if article['url'] not in posted_urls:
            success = post_to_facebook(article)
            
            if success:
                save_posted_url(article['url'])
                posted_urls.add(article['url'])
                posts_made += 1
                time.sleep(5)
            else:
                break
        else:
            print(f"Skipping (already posted): {article['title'][:30]}...")
            
    print(f"\nDone! Made {posts_made} new posts.")

if __name__ == "__main__":
    main()
