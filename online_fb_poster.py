import requests
from bs4 import BeautifulSoup
import time
import os
import json

# ==========================================
# CONFIGURATION
# ==========================================

# Our Custom Feed Endpoint URL
# (You must upload custom_feed.php to your WordPress root first)
WEBSITE_FEED_URL = "http://elgeza.42web.io/custom_feed.php"

# Default Website URL (used for building links if the feed doesn't provide absolute ones)
WEBSITE_URL = "http://elgeza.42web.io"

# The Permanent Facebook Graph API Token you provided
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN", "EAALwDOfTyC0BQ1Ik2PvPvTZCqAGXfrTHhbc9f8scLZBYYl08MDm3ZBKmpe8yqldqDmwOq6H5ULhm6Li0CCOr6lPoZBZBznZAWlmIf0N9cB0MyATL1hZCWlP82cf7klZBGTitqCRbNvIA8BUTuS91JM0bXz9pr0lSZCyS2jocl2TMNNjsyAeJVr2Eq8gNVR41lOnLj4BDZB")

POSTED_URLS_FILE = "posted_urls.txt"

# Modern User-Agent that most free hosts prefer 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

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

def fetch_custom_feed():
    """Fetch JSON news feed from our custom endpoint."""
    print(f"Fetching news from {WEBSITE_FEED_URL}...")
    articles = []
    
    try:
        # Requesting our custom JSON endpoint will bypass normal browser-checking
        response = requests.get(WEBSITE_FEED_URL, headers=HEADERS, timeout=20)
        
        if response.status_code == 200:
            try:
                # Expecting a JSON array of post objects
                feed_data = response.json()
                
                for item in feed_data:
                    title = item.get('title', '')
                    url = item.get('url', '')
                    summary = item.get('summary', '')
                    
                    if title and url:
                        articles.append({
                            'title': title,
                            'url': url,
                            'summary': summary
                        })
                        print(f"-> Found ({url}): {title[:50]}...")
            except json.JSONDecodeError:
                print("Error: The file returned from the site was not valid JSON.")
                print(f"Response preview: {response.text[:200]}")
        else:
            print(f"Failed. Server returned status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        
    return articles

def fetch_scraper_fallback():
    """Fallback: Attempt to parse the static front page with cloudscraper."""
    import cloudscraper
    print("Trying fallback via cloudscraper...")
    articles = []
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(WEBSITE_URL, timeout=20)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for recent articles based on the theme HTML observed
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
                    print(f"-> Found via Fallback ({link}): {title[:50]}...")
    except ImportError:
         print("Cloudscraper not installed, skipping fallback.")
    except Exception as e:
         print(f"Fallback Error: {e}")
         
    return articles

def post_to_facebook(article):
    """Post article to Facebook."""
    print(f"Posting: {article['title'][:50]}...")
    
    post_url = "https://graph.facebook.com/v19.0/me/feed"
    
    parts = [f"📰 {article['title']}"]
    if article['summary']:
        parts.append(f"\n{article['summary']}")
        
    parts.append(f"\n🔗 لمتابعة القراءة: {article['url']}")
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

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    print("=== Akhbar El-Giza (Direct Website Source) -> Facebook Auto-Poster ===")
    
    if not FB_ACCESS_TOKEN or "YOUR" in FB_ACCESS_TOKEN:
        print("ERROR: Configure FB_ACCESS_TOKEN first.")
        return

    posted_urls = load_posted_urls()
    
    # Try fetching from our custom endpoint first
    latest_articles = fetch_custom_feed()
    
    if not latest_articles:
        print("Custom feed empty or failed. Attempting fallback method.")
        latest_articles = fetch_scraper_fallback()
        
    if not latest_articles:
        print("No articles found from any source.")
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
    main()
