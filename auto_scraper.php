<?php
/**
 * ==============================================
 * سكربت سحب الأخبار التلقائي - أخبار الجيزة
 * ==============================================
 * 
 * المصادر: اليوم السابع | المصري اليوم | مصراوي
 * الكلمات المفتاحية: بشتيل، الجيزة
 * 
 * كيفية التشغيل:
 *   - ارفع الملف على htdocs بجوار wp-config.php
 *   - GitHub Actions يستدعيه يوميًا الساعة 2 الظهر
 *   - أو افتحه يدويًا: http://elgeza.42web.io/auto_scraper.php?secret=elgeza_secret_2026
 */

// === ضبط الوقت والذاكرة ===
set_time_limit(300);
ini_set('memory_limit', '256M');
header('Content-Type: application/json; charset=utf-8');

// === حماية بسيطة ===
$SECRET_KEY = "elgeza_secret_2026";
$provided_secret = isset($_GET['secret']) ? $_GET['secret'] : '';
if ($provided_secret !== $SECRET_KEY) {
    http_response_code(403);
    echo json_encode(['error' => 'Unauthorized. Add ?secret=YOUR_SECRET to the URL.']);
    exit;
}

// === تحميل WordPress ===
define('WP_USE_THEMES', false);
require('./wp-blog-header.php');

// === الإعدادات ===
$KEYWORDS = ['بشتيل', 'الجيزة', 'محافظة الجيزة'];

// خريطة التصنيفات (غيّر الأرقام حسب تصنيفات موقعك)
$CATEGORY_MAP = [
    'محليات' => 2,
    'حوادث'  => 3,
    'رياضة'  => 4,
    'تعليم'  => 5,
    'عام'    => 1,
];

// === الدوال المساعدة ===

function contains_keywords($text, $keywords) {
    foreach ($keywords as $keyword) {
        if (mb_strpos($text, $keyword) !== false) {
            return true;
        }
    }
    return false;
}

function classify_category($title, $content = '') {
    $text = $title . ' ' . $content;
    $accident_words = ['حادث', 'جريمة', 'مقتل', 'سرقة', 'شرطة', 'مباحث', 'القبض', 'نيابة', 'محكمة', 'متهم'];
    $sports_words   = ['مباراة', 'الأهلي', 'الزمالك', 'منتخب', 'كأس', 'بطولة'];
    $edu_words      = ['تعليم', 'مدرسة', 'جامعة', 'طلاب', 'امتحان'];
    
    foreach ($accident_words as $w) { if (mb_strpos($text, $w) !== false) return 'حوادث'; }
    foreach ($sports_words as $w)   { if (mb_strpos($text, $w) !== false) return 'رياضة'; }
    foreach ($edu_words as $w)      { if (mb_strpos($text, $w) !== false) return 'تعليم'; }
    return 'محليات';
}

function fetch_url($url) {
    $ch = curl_init();
    curl_setopt_array($ch, [
        CURLOPT_URL => $url,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        CURLOPT_HTTPHEADER => ['Accept-Language: ar,en;q=0.9'],
        CURLOPT_SSL_VERIFYPEER => false,
    ]);
    $response = curl_exec($ch);
    curl_close($ch);
    return $response;
}

function post_already_exists($title) {
    global $wpdb;
    $existing = $wpdb->get_var(
        $wpdb->prepare("SELECT ID FROM {$wpdb->posts} WHERE post_title = %s AND post_status = 'publish' LIMIT 1", $title)
    );
    return !empty($existing);
}

function publish_to_wp($title, $content, $category_name, $source_url, $image_url = '') {
    global $CATEGORY_MAP;
    
    if (post_already_exists($title)) {
        return ['status' => 'skipped', 'reason' => 'already exists'];
    }
    
    $cat_id = isset($CATEGORY_MAP[$category_name]) ? $CATEGORY_MAP[$category_name] : $CATEGORY_MAP['عام'];
    
    $post_data = [
        'post_title'    => $title,
        'post_content'  => $content,
        'post_status'   => 'publish',
        'post_author'   => 1,
        'post_category' => [$cat_id],
    ];
    
    $post_id = wp_insert_post($post_data);
    
    if (is_wp_error($post_id)) {
        return ['status' => 'error', 'message' => $post_id->get_error_message()];
    }
    
    // محاولة تحميل الصورة البارزة
    if (!empty($image_url)) {
        set_featured_image($post_id, $image_url);
    }
    
    return ['status' => 'success', 'post_id' => $post_id];
}

function set_featured_image($post_id, $image_url) {
    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');
    
    $image_data = @file_get_contents($image_url);
    if ($image_data === false) return;
    
    $filename = basename(parse_url($image_url, PHP_URL_PATH));
    if (empty($filename)) $filename = 'img_' . $post_id . '.jpg';
    
    $upload = wp_upload_bits($filename, null, $image_data);
    if ($upload['error']) return;
    
    $filetype = wp_check_filetype($filename);
    $attachment = [
        'post_mime_type' => $filetype['type'],
        'post_title'     => sanitize_file_name($filename),
        'post_content'   => '',
        'post_status'    => 'inherit',
    ];
    
    $attach_id = wp_insert_attachment($attachment, $upload['file'], $post_id);
    $attach_data = wp_generate_attachment_metadata($attach_id, $upload['file']);
    wp_update_attachment_metadata($attach_id, $attach_data);
    set_post_thumbnail($post_id, $attach_id);
}

// === سحب الأخبار من RSS ===

function parse_rss_feed($rss_url) {
    $xml_string = fetch_url($rss_url);
    if (empty($xml_string)) return [];
    
    // تنظيف XML
    $xml_string = preg_replace('/&(?!amp;|lt;|gt;|quot;|apos;)/', '&amp;', $xml_string);
    
    libxml_use_internal_errors(true);
    $xml = simplexml_load_string($xml_string);
    if ($xml === false) return [];
    
    $items = [];
    if (isset($xml->channel->item)) {
        foreach ($xml->channel->item as $item) {
            $items[] = [
                'title'   => (string)$item->title,
                'link'    => (string)$item->link,
                'summary' => strip_tags((string)$item->description),
            ];
        }
    }
    return $items;
}

// === سحب محتوى المقال الكامل ===

function fetch_youm7_content($url) {
    $html = fetch_url($url);
    if (empty($html)) return ['content' => '', 'image' => ''];
    
    $doc = new DOMDocument();
    @$doc->loadHTML(mb_convert_encoding($html, 'HTML-ENTITIES', 'UTF-8'));
    $xpath = new DOMXPath($doc);
    
    // سحب محتوى المقال الكامل
    $content = '';
    // محاولة أولى: articleBody
    $nodes = $xpath->query('//div[@id="articleBody"]//p');
    // محاولة ثانية: article-text
    if ($nodes->length == 0) $nodes = $xpath->query('//div[contains(@class,"article-text")]//p');
    // محاولة ثالثة: NewsStory
    if ($nodes->length == 0) $nodes = $xpath->query('//div[@id="NewsStory"]//p');
    if ($nodes->length > 0) {
        foreach ($nodes as $node) {
            $text = trim($node->textContent);
            if (!empty($text)) $content .= $text . "\n\n";
        }
    }
    
    // سحب الصورة
    $image = '';
    $og_images = $xpath->query('//meta[@property="og:image"]/@content');
    if ($og_images->length > 0) {
        $image = $og_images->item(0)->value;
    }
    
    return ['content' => trim($content), 'image' => $image];
}

function fetch_almasry_content($url) {
    $html = fetch_url($url);
    if (empty($html)) return ['content' => '', 'image' => ''];
    
    $doc = new DOMDocument();
    @$doc->loadHTML(mb_convert_encoding($html, 'HTML-ENTITIES', 'UTF-8'));
    $xpath = new DOMXPath($doc);
    
    $content = '';
    // محاولة أولى: NewsStory
    $nodes = $xpath->query('//div[@id="NewsStory"]//p');
    // محاولة ثانية: article-body
    if ($nodes->length == 0) $nodes = $xpath->query('//div[contains(@class,"article-body")]//p');
    // محاولة ثالثة: أي div فيه article
    if ($nodes->length == 0) $nodes = $xpath->query('//article//p');
    if ($nodes->length > 0) {
        foreach ($nodes as $node) {
            $text = trim($node->textContent);
            if (!empty($text)) $content .= $text . "\n\n";
        }
    }
    
    $image = '';
    $og_images = $xpath->query('//meta[@property="og:image"]/@content');
    if ($og_images->length > 0) {
        $image = $og_images->item(0)->value;
    }
    
    return ['content' => trim($content), 'image' => $image];
}

function fetch_masrawy_content($url) {
    $html = fetch_url($url);
    if (empty($html)) return ['content' => '', 'image' => ''];
    
    $doc = new DOMDocument();
    @$doc->loadHTML(mb_convert_encoding($html, 'HTML-ENTITIES', 'UTF-8'));
    $xpath = new DOMXPath($doc);
    
    $content = '';
    // محاولة أولى: ArticleDetails
    $nodes = $xpath->query('//div[contains(@class,"ArticleDetails")]//p');
    // محاولة ثانية: article_body__
    if ($nodes->length == 0) $nodes = $xpath->query('//div[contains(@class,"article_body")]//p');
    // محاولة ثالثة: أي article
    if ($nodes->length == 0) $nodes = $xpath->query('//article//p');
    if ($nodes->length > 0) {
        foreach ($nodes as $node) {
            $text = trim($node->textContent);
            if (!empty($text)) $content .= $text . "\n\n";
        }
    }
    
    $image = '';
    $og_images = $xpath->query('//meta[@property="og:image"]/@content');
    if ($og_images->length > 0) {
        $image = $og_images->item(0)->value;
    }
    
    return ['content' => trim($content), 'image' => $image];
}

// ==========================================================
//                    التشغيل الرئيسي
// ==========================================================

$results = ['youm7' => [], 'almasry' => [], 'masrawy' => []];
$total_published = 0;
$total_skipped = 0;

// ======== 1. اليوم السابع (RSS) ========
$youm7_sections = [296, 203, 97]; // المحافظات، الحوادث، أخبار مصر

foreach ($youm7_sections as $section_id) {
    $rss_url = "https://www.youm7.com/rss/SectionRss?SectionID={$section_id}";
    $items = parse_rss_feed($rss_url);
    
    foreach ($items as $item) {
        if (!contains_keywords($item['title'] . ' ' . $item['summary'], $KEYWORDS)) {
            continue;
        }
        
        // سحب المحتوى الكامل
        $article = fetch_youm7_content($item['link']);
        $content = !empty($article['content']) ? $article['content'] : $item['summary'];
        $category = classify_category($item['title'], $content);
        
        $result = publish_to_wp($item['title'], $content, $category, $item['link'], $article['image']);
        
        if ($result['status'] === 'success') {
            $total_published++;
            $results['youm7'][] = ['title' => $item['title'], 'status' => 'published', 'post_id' => $result['post_id']];
        } else {
            $total_skipped++;
            $results['youm7'][] = ['title' => $item['title'], 'status' => $result['status']];
        }
        
        usleep(500000); // نصف ثانية بين كل خبر
    }
}

// ======== 2. المصري اليوم (RSS) ========
$almasry_rss = "https://www.almasryalyoum.com/rss/rssfeeds";
$items = parse_rss_feed($almasry_rss);

foreach ($items as $item) {
    if (!contains_keywords($item['title'] . ' ' . $item['summary'], $KEYWORDS)) {
        continue;
    }
    
    $article = fetch_almasry_content($item['link']);
    $content = !empty($article['content']) ? $article['content'] : $item['summary'];
    $category = classify_category($item['title'], $content);
    
    $result = publish_to_wp($item['title'], $content, $category, $item['link'], $article['image']);
    
    if ($result['status'] === 'success') {
        $total_published++;
        $results['almasry'][] = ['title' => $item['title'], 'status' => 'published', 'post_id' => $result['post_id']];
    } else {
        $total_skipped++;
        $results['almasry'][] = ['title' => $item['title'], 'status' => $result['status']];
    }
    
    usleep(500000);
}

// ======== 3. مصراوي (HTML scraping) ========
// مصراوي ليس لديهم RSS، لكن PHP على السيرفر يقدر يسحب HTML مباشرة
$masrawy_urls = [
    'https://www.masrawy.com/news/news_egypt',
    'https://www.masrawy.com/news/news_publicaffairs',
];

foreach ($masrawy_urls as $masrawy_url) {
    $html = fetch_url($masrawy_url);
    if (empty($html)) continue;
    
    $doc = new DOMDocument();
    @$doc->loadHTML(mb_convert_encoding($html, 'HTML-ENTITIES', 'UTF-8'));
    $xpath = new DOMXPath($doc);
    
    // ابحث عن روابط الأخبار
    $links = $xpath->query('//a[contains(@href, "/news/details/") or contains(@href, "/news/news_")]/@href');
    $processed_urls = [];
    
    foreach ($links as $link_node) {
        $href = $link_node->value;
        if (strpos($href, 'http') !== 0) {
            $href = 'https://www.masrawy.com' . $href;
        }
        
        if (in_array($href, $processed_urls)) continue;
        if (strpos($href, '/details/') === false) continue; // فقط صفحات المقالات
        $processed_urls[] = $href;
        
        // سحب تفاصيل المقال
        $article = fetch_masrawy_content($href);
        if (empty($article['content'])) continue;
        
        // استخرج العنوان من المحتوى أو العنوان og:title
        $art_html = fetch_url($href);
        $art_doc = new DOMDocument();
        @$art_doc->loadHTML(mb_convert_encoding($art_html, 'HTML-ENTITIES', 'UTF-8'));
        $art_xpath = new DOMXPath($art_doc);
        
        $title_nodes = $art_xpath->query('//h1');
        $title = $title_nodes->length > 0 ? trim($title_nodes->item(0)->textContent) : '';
        if (empty($title)) {
            $og_title = $art_xpath->query('//meta[@property="og:title"]/@content');
            $title = $og_title->length > 0 ? $og_title->item(0)->value : '';
        }
        if (empty($title)) continue;
        
        // فلتر بالكلمات المفتاحية
        if (!contains_keywords($title . ' ' . $article['content'], $KEYWORDS)) {
            continue;
        }
        
        $category = classify_category($title, $article['content']);
        $result = publish_to_wp($title, $article['content'], $category, $href, $article['image']);
        
        if ($result['status'] === 'success') {
            $total_published++;
            $results['masrawy'][] = ['title' => $title, 'status' => 'published', 'post_id' => $result['post_id']];
        } else {
            $total_skipped++;
            $results['masrawy'][] = ['title' => $title, 'status' => $result['status']];
        }
        
        usleep(500000);
        
        if (count($results['masrawy']) >= 10) break; // حد أقصى 10 من مصراوي
    }
}

// === النتيجة النهائية ===
echo json_encode([
    'status'    => 'completed',
    'published' => $total_published,
    'skipped'   => $total_skipped,
    'details'   => $results,
    'timestamp' => date('Y-m-d H:i:s'),
], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
