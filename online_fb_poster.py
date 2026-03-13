import requests
from bs4 import BeautifulSoup
import time
import os

# ==========================================
# CONFIGURATION
# ==========================================

# Your website URL (the WordPress site)
WEBSITE_URL = "http://elgeza.42web.io/"

# Facebook Graph API Configuration
# You MUST get these from the Facebook Developer Portal
FB_PAGE_ID = "100002134983059" # معرف صفحة "صورة من بشتيل" الوهمي أو الحقيقي
FB_PAGE_ACCESS_TOKEN = "YOUR_FACEBOOK_PAGE_ACCESS_TOKEN"

# File to keep track of posted URLs so we don't post duplicates
POSTED_URLS_FILE = "posted_urls.txt"

# Anti-bot headers just in case we hit InfinityFree blocks on GET requests
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
    """Fetch the latest news articles from the website's HTML."""
    print(f"Fetching news from {WEBSITE_URL}...")
    articles = []
    
    try:
        response = requests.get(WEBSITE_URL, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8' # Ensure Arabic text reads correctly
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # The static website uses 'article-card' class for news items
            cards = soup.find_all('div', class_='article-card')
            
            for card in cards[:5]: # Get latest 5
                title_tag = card.find(['h2', 'h3', 'h4'])
                if not title_tag: continue
                
                link_tag = title_tag.find('a')
                if not link_tag: continue
                
                title = link_tag.text.strip()
                link = link_tag['href']
                
                # Make the link absolute if it's relative
                if not link.startswith('http'):
                    link = WEBSITE_URL.rstrip('/') + '/' + link.lstrip('/')
                
                if title and link:
                    articles.append({
                        'title': title,
                        'url': link
                    })
        else:
            print(f"Failed to fetch website. Status code: {response.status_code}")
            
    except Exception as e:
        print(f"Error fetching news: {e}")
        
    return articles

def post_to_facebook(article):
    """Post the article to Facebook via Graph API."""
    print(f"Posting to Facebook: {article['title']}")
    
    post_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    
    message = f"{article['title']}\n\nاقرأ المزيد هنا: {article['url']}"
    
    payload = {
        'message': message,
        'link': article['url'],
        'access_token': FB_PAGE_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(post_url, data=payload)
        result = response.json()
        
        if response.status_code == 200 and 'id' in result:
            print(f"SUCCESS: Posted to Facebook. Post ID: {result['id']}")
            return True
        else:
            print(f"FAILED to post. Error: {result}")
            return False
            
    except Exception as e:
        print(f"Error during Facebook API request: {e}")
        return False

# ==========================================
# MAIN SCRIPT
# ==========================================

def main():
    if FB_PAGE_ACCESS_TOKEN == "YOUR_FACEBOOK_PAGE_ACCESS_TOKEN":
        print("ERROR: Please configure FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN inside the script.")
        return

    posted_urls = load_posted_urls()
    latest_articles = fetch_latest_news()
    
    if not latest_articles:
        print("No articles found to post.")
        return
        
    # Reverse to post the oldest of the new batch first
    latest_articles.reverse()
    
    posts_made = 0
    for article in latest_articles:
        if article['url'] not in posted_urls:
            success = post_to_facebook(article)
            
            if success:
                save_posted_url(article['url'])
                posted_urls.add(article['url'])
                posts_made += 1
                
                # Sleep a bit to avoid hitting rate limits
                time.sleep(5)
            else:
                # If posting failed (e.g. bad token), stop trying others
                break
        else:
            print(f"Skipping already posted article: {article['title']}")
            
    print(f"\nDone! Made {posts_made} new posts.")

if __name__ == "__main__":
    main()
