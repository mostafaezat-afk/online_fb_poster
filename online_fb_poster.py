import asyncio
import os
import time
import json
import requests
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURATION
# ==========================================

# Your website URL
WEBSITE_URL = "http://elgeza.42web.io/"

# The Permanent Facebook Graph API Token
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "EAALwDOfTyC0BQ1Ik2PvPvTZCqAGXfrTHhbc9f8scLZBYYl08MDm3ZBKmpe8yqldqDmwOq6H5ULhm6Li0CCOr6lPoZBZBznZAWlmIf0N9cB0MyATL1hZCWlP82cf7klZBGTitqCRbNvIA8BUTuS91JM0bXz9pr0lSZCyS2jocl2TMNNjsyAeJVr2Eq8gNVR41lOnLj4BDZB")

POSTED_URLS_FILE = "posted_urls.txt"

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_posted_urls():
    if not os.path.exists(POSTED_URLS_FILE):
        return set()
    with open(POSTED_URLS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_posted_url(url):
    with open(POSTED_URLS_FILE, 'a', encoding='utf-8') as f:
        f.write(url + "\n")

async def fetch_news_via_browser():
    """Fetch news by simulating a real browser to bypass InfinityFree logic."""
    print(f"Opening browser to load {WEBSITE_URL}...")
    articles = []
    
    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()
        
        try:
            # Go to site and wait until the network is idle (JS challenge finished)
            await page.goto(WEBSITE_URL, wait_until="networkidle", timeout=30000)
            
            # Additional wait just in case
            await page.wait_for_timeout(3000)
            
            # Get the fully rendered final HTML
            html_content = await page.content()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for recent articles based on the theme HTML
            cards = soup.find_all('div', class_='article-card')
            
            for card in cards[:5]:
                title_tag = card.find(['h2', 'h3', 'h4'])
                if not title_tag: continue
                
                link_tag = title_tag.find('a')
                if not link_tag: continue
                
                title = link_tag.text.strip()
                link = link_tag.get('href', '#')
                
                if not link.startswith('http'):
                    link = WEBSITE_URL.rstrip('/') + '/' + link.lstrip('/')
                
                excerpt_tag = card.find('p', class_='hero-excerpt')
                summary = excerpt_tag.text.strip() if excerpt_tag else ""
                
                if title and link != '#':
                    articles.append({
                        'title': title,
                        'url': link,
                        'summary': summary
                    })
                    print(f"-> Found: {title[:50]}...")
                    
        except Exception as e:
            print(f"Browser error: {e}")
            
        finally:
            await browser.close()
            
    return articles

def post_to_facebook(article):
    """Post article to Facebook."""
    print(f"Posting: {article['title'][:50]}...")
    
    post_url = "https://graph.facebook.com/v19.0/me/feed"
    
    parts = [f"📰 {article['title']}"]
    if article['summary']:
        parts.append(f"\n{article['summary']}")
        
    parts.append(f"\n🔗 القراءة بالتفصيل من موقعنا: {article['url']}")
    parts.append("\n#أخبار_الجيزة #بشتيل")
    
    message = "\n".join(parts)
    
    payload = {
        'message': message,
        'link': article['url'],
        'access_token': FB_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(post_url, data=payload)
        result = response.json()
        
        if response.status_code == 200 and 'id' in result:
            print(f"SUCCESS: Post ID: {result['id']}")
            return True
        else:
            print(f"FAILED: {result}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# ==========================================
# MAIN
# ==========================================

async def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=== Akhbar El-Giza (Browser Headless Reader) -> Facebook Auto-Poster ===")
    
    if not FB_ACCESS_TOKEN or "YOUR" in FB_ACCESS_TOKEN:
        print("ERROR: Configure FB_ACCESS_TOKEN first.")
        return

    posted_urls = load_posted_urls()
    
    # Run the playwright fetcher
    latest_articles = await fetch_news_via_browser()
        
    if not latest_articles:
        print("No articles found from the source.")
        return
    
    print(f"\nFound {len(latest_articles)} articles.")
    latest_articles.reverse()
    
    posts_made = 0
    for article in latest_articles:
        key = article['url'] 
        if key not in posted_urls:
            success = post_to_facebook(article)
            if success:
                save_posted_url(key)
                posted_urls.add(key)
                posts_made += 1
                time.sleep(5)
            else:
                break
        else:
            print(f"Skipping: {article['title'][:30]}...")
            
    print(f"\nDone! Made {posts_made} new posts.")

if __name__ == "__main__":
    asyncio.run(main())
