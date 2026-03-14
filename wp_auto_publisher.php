<?php
/**
 * Custom End Point: wp_auto_publisher.php
 * Receives POST requests from our Python Multi-Source Scraper and publishes them to WordPress.
 * 
 * Upload this file to your WordPress root directory (same folder as wp-config.php)
 */

define('WP_USE_THEMES', false);
require('./wp-blog-header.php');

header('Content-Type: application/json; charset=utf-8');

$expected_secret = "elgeza_secret_2026";

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Only POST requests are allowed.']);
    exit;
}

$secret = isset($_POST['secret']) ? $_POST['secret'] : '';
if ($secret !== $expected_secret) {
    http_response_code(403);
    echo json_encode(['error' => 'Invalid secret token.']);
    exit;
}

$title    = isset($_POST['title']) ? sanitize_text_field($_POST['title']) : '';
$content  = isset($_POST['content']) ? wp_kses_post($_POST['content']) : '';
$category = isset($_POST['category']) ? sanitize_text_field($_POST['category']) : '';
$source   = isset($_POST['source']) ? esc_url_raw($_POST['source']) : '';
$image_url= isset($_POST['image_url']) ? esc_url_raw($_POST['image_url']) : '';

if (empty($title) || empty($content)) {
    http_response_code(400);
    echo json_encode(['error' => 'Title and content are required.']);
    exit;
}

$existing_post = get_page_by_title($title, OBJECT, 'post');
if ($existing_post) {
    echo json_encode(['status' => 'skipped', 'message' => 'Post already exists.']);
    exit;
}

$category_map = array(
    'محليات'  => 2,
    'حوادث'   => 3,
    'رياضة'    => 4,
    'عام'     => 1
);

$cat_id = isset($category_map[$category]) ? $category_map[$category] : $category_map['عام'];
$final_content = $content . "\n\n<p><a href='{$source}' target='_blank' rel='nofollow'>المصدر</a></p>";

$post_data = array(
    'post_title'    => $title,
    'post_content'  => $final_content,
    'post_status'   => 'publish',
    'post_author'   => 1,
    'post_category' => array($cat_id)
);

$post_id = wp_insert_post($post_data);

if (is_wp_error($post_id)) {
    http_response_code(500);
    echo json_encode(['error' => $post_id->get_error_message()]);
    exit;
}

if (!empty($image_url)) {
    require_once(ABSPATH . 'wp-admin/includes/media.php');
    require_once(ABSPATH . 'wp-admin/includes/file.php');
    require_once(ABSPATH . 'wp-admin/includes/image.php');

    $image_data = @file_get_contents($image_url);
    if ($image_data !== false) {
        $filename = basename($image_url);
        $filename = preg_replace('/\?.*/', '', $filename);
        if(empty($filename)) $filename = 'thumbnail_' . $post_id . '.jpg';

        $upload_file = wp_upload_bits($filename, null, $image_data);

        if (!$upload_file['error']) {
            $wp_filetype = wp_check_filetype($filename, null);
            $attachment = array(
                'post_mime_type' => $wp_filetype['type'],
                'post_title'     => sanitize_file_name($filename),
                'post_content'   => '',
                'post_status'    => 'inherit'
            );
            $attach_id = wp_insert_attachment($attachment, $upload_file['file'], $post_id);
            $attach_data = wp_generate_attachment_metadata($attach_id, $upload_file['file']);
            wp_update_attachment_metadata($attach_id, $attach_data);
            set_post_thumbnail($post_id, $attach_id);
        }
    }
}

echo json_encode([
    'status' => 'success',
    'message'=> 'Post created successfully',
    'post_id'=> $post_id
]);
exit;
