import os
import time
import requests
import feedparser
from bs4 import BeautifulSoup
import urllib.parse
from playwright.sync_api import sync_playwright

# ==========================================
# CONFIGURATION
# ==========================================

WP_WEBHOOK_URL = "http://elgeza.42web.io/wp_auto_publisher.php"
WP_SECRET = "elgeza_secret_2026"

SCRAPED_URLS_FILE = "multi_scraped_urls.txt"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_scraped_urls():
    if not os.path.exists(SCRAPED_URLS_FILE): return set()
    with open(SCRAPED_URLS_FILE, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def save_scraped_url(url):
    with open(SCRAPED_URLS_FILE, 'a', encoding='utf-8') as f:
        f.write(url + "\n")

def classify_category(title, content):
    text = (title + " " + content).lower()
    if any(k in text for k in ["حادث", "جريمة", "مقتل", "سرقة", "شرطة", "مباحث", "القبض", "نيابة", "محكمة"]):
        return "حوادث"
    if any(k in text for k in ["مباراة", "الأهلي", "الزمالك", "منتخب", "كأس", "بطولة", "أهداف", "نادي"]):
        return "رياضة"
    return "محليات"

# ==========================================
# PLAYWRIGHT POST DELIVERER 
# ==========================================
# Since InfinityFree drops raw python HTTP POSTs, we must use a real browser to deliver the data.
def post_to_wordpress_browser(article):
    print(f"Pushing to WP via Browser ({article['category']}): {article['title'][:40]}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # We navigate to the site first to get the cookies/clear the JS challenge
        try:
             page.goto("http://elgeza.42web.io/", wait_until="domcontentloaded", timeout=30000)
             page.wait_for_timeout(3000)
        except Exception:
             pass # Timeout is fine as long as we got connected
             
        # Inject an invisible form to submit the POST request
        html_form = f"""
        <form id="autoSubmit" action="{WP_WEBHOOK_URL}" method="POST">
            <input type="hidden" name="secret" value="{WP_SECRET}">
            <input type="hidden" name="title" value="">
            <input type="hidden" name="content" value="">
            <input type="hidden" name="category" value="{article['category']}">
            <input type="hidden" name="source" value="{article['url']}">
            <input type="hidden" name="image_url" value="{article.get('image', '')}">
        </form>
        <script>
            // Populate value via JS to safely escape newlines and quotes
            document.querySelector('input[name="title"]').value = `{article['title'].replace('`', "'")}`;
            document.querySelector('input[name="content"]').value = `{article.get('content', '').replace('`', "'")}`;
            document.getElementById('autoSubmit').submit();
        </script>
        """
        
        try:
             # Load the form in the existing authenticated page
             page.set_content(html_form)
             
             # Wait for navigation to the PHP handler
             page.wait_for_load_state("networkidle", timeout=15000)
             
             # Extract the returned JSON from the page
             result_text = page.locator("body").inner_text()
             
             if "success" in result_text.lower():
                 print(f"✅ WP Success: {result_text}")
                 success = True
             elif "skipped" in result_text.lower() or "already exists" in result_text.lower():
                 print(f"⏸️ WP Skipped (Exists): {result_text}")
                 success = True
             else:
                 print(f"❌ WP Failed: {result_text}")
                 success = False
        except Exception as e:
             print(f"Browser POST Error: {e}")
             success = False
             
        browser.close()
        return success


# ==========================================
# GOOGLE NEWS RSS FETCHER
# ==========================================

def fetch_google_news_for_query(query, seen_urls):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ar&gl=EG&ceid=EG:ar"
    
    articles = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = feedparser.parse(response.text)
        
        for entry in soup.entries[:5]: 
            title = entry.title
            if " - " in title: title = title.rsplit(" - ", 1)[0]
            
            article_url = entry.link
            if article_url in seen_urls: continue
            
            summary_soup = BeautifulSoup(entry.summary, 'html.parser')
            content = summary_soup.text.strip()
            
            cat = classify_category(title, content)
            
            articles.append({
                'title': title,
                'content': content,
                'category': cat,
                'image': '', 
                'url': article_url
            })
            print(f"Found via Google News: {title[:40]}")
    except Exception as e:
        print(f"Error fetching Google News for {query}: {e}")
    return articles

# ==========================================
# MAIN EXECUTION
# ==========================================

def run_scraper():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Multi-Source Scraper to WP (Google News + Browser Push Edition) ===")
    
    seen_urls = load_scraped_urls()
    all_new_articles = []
    
    queries = [
        '("بشتيل" OR "الجيزة") site:youm7.com',
        '("بشتيل" OR "الجيزة") site:almasryalyoum.com',
        '("بشتيل" OR "الجيزة") site:masrawy.com'
    ]
    
    for query in queries:
        print(f"\n--- Searching: {query} ---")
        articles = fetch_google_news_for_query(query, seen_urls)
        all_new_articles.extend(articles)
        time.sleep(2) 
        
    if not all_new_articles:
        print("\nNo new relevant articles found matching keywords.")
        return
        
    print(f"\nTotal new relevant articles to push to WP: {len(all_new_articles)}")
    
    success_count = 0
    for article in all_new_articles:
        if post_to_wordpress_browser(article):
            save_scraped_url(article['url'])
            success_count += 1
            
    print(f"\nFinished. Successfully pushed {success_count} articles to WP.")

if __name__ == "__main__":
    run_scraper()
