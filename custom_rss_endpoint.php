<?php
/**
 * Custom RSS Feed Generator for Akhbar El Giza
 * This file bypasses standard InfinityFree bot protection because it is directly accessed
 * and outputs plain XML without triggering the HTML/JS security challenge.
 * 
 * Upload this file to the root directory of your WordPress installation
 * (the same folder as wp-config.php).
 * Access it via: http://elgeza.42web.io/custom-rss.php
 */

// Load WordPress Core so we can safely query the custom posts
define('WP_USE_THEMES', false);
require('./wp-blog-header.php');

header('Content-Type: application/rss+xml; charset=utf-8');

// Build the RSS XML structure
echo '<?xml version="1.0" encoding="UTF-8"?>';
echo '<rss version="2.0"
    xmlns:content="http://purl.org/rss/1.0/modules/content/"
    xmlns:wfw="http://wellformedweb.org/CommentAPI/"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:atom="http://www.w3.org/2005/Atom"
    xmlns:sy="http://purl.org/rss/1.0/modules/syndication/"
    xmlns:slash="http://purl.org/rss/1.0/modules/slash/"
    >';

echo '<channel>';
echo '<title>' . get_bloginfo('name') . '</title>';
echo '<link>' . get_bloginfo('url') . '</link>';
echo '<description>' . get_bloginfo('description') . '</description>';
echo '<language>' . get_bloginfo('language') . '</language>';
echo '<atom:link href="' . get_bloginfo('url') . '/custom-rss.php" rel="self" type="application/rss+xml" />';

// Query the latest 10 posts
$args = array(
    'post_type'      => 'post',
    'posts_per_page' => 10,
    'post_status'    => 'publish',
);

$query = new WP_Query($args);

if ($query->have_posts()) {
    while ($query->have_posts()) {
        $query->the_post();
        
        // Strip shortcodes and HTML from content to make a clean summary
        $content = get_the_content();
        $content = strip_shortcodes($content);
        $content = wp_strip_all_tags($content);
        // Limit to ~200 characters for the summary
        if (mb_strlen($content) > 200) {
            $content = mb_substr($content, 0, 200) . '...';
        }

        echo '<item>';
        echo '<title>' . htmlspecialchars(get_the_title()) . '</title>';
        echo '<link>' . get_permalink() . '</link>';
        echo '<pubDate>' . mysql2date('D, d M Y H:i:s +0000', get_post_time('Y-m-d H:i:s', true), false) . '</pubDate>';
        echo '<dc:creator><![CDATA[' . get_the_author() . ']]></dc:creator>';
        echo '<guid isPermaLink="false">' . get_the_guid() . '</guid>';
        echo '<description><![CDATA[' . $content . ']]></description>';
        echo '</item>';
    }
} else {
    echo '<item><title>No Posts Found</title></item>';
}

wp_reset_postdata();

echo '</channel>';
echo '</rss>';
?>
