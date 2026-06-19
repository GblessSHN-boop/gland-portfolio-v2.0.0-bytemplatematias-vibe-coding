# GLAND Portfolio Admin CMS

Admin dashboard untuk mengelola portfolio Gland Jermano Blessed Siahaan.

## Core Modules

1. Dashboard Overview
2. Contact Messages / Inbox
3. Page Editor
4. Media Library
5. Analytics
6. Settings

## Planned Editable Sections

- Site identity: logo, favicon, preloader
- Hero: title, background, intro video, right video/card
- Personal info: photo, bio, email, phone, address
- Selected highlights
- Complete projects
- Contact messages
- Visitor analytics

## Backend

Python server + MySQL database.

## Database

See `database/schema.sql`.

## PHP Replacement

The original `contact.php` template file has been replaced by a Python backend.

Main Python endpoints:

- `GET /api/health`
- `POST /api/contact`

Temporary contact storage during development:

- `logs/contact_messages_dev.jsonl`

Next phase:

- connect `POST /api/contact` to MySQL table `messages`.

## Message CRUD

Admin message inbox:

- `admin/messages.html`

Message API endpoints:

- `GET /api/messages`
- `GET /api/messages/{id}`
- `PATCH /api/messages/{id}`
- `DELETE /api/messages/{id}`

Message statuses:

- `new`
- `read`
- `approved`
- `rejected`
- `archived`

## Projects CRUD

Admin projects editor:

- `admin/projects.html`

Project API endpoints:

- `GET /api/projects`
- `GET /api/projects/{id}`
- `POST /api/projects`
- `PATCH /api/projects/{id}`
- `DELETE /api/projects/{id}`

Project fields:

- title
- category
- description
- image_path
- project_url
- repo_url
- technologies
- display_order
- is_featured
- is_active

## Selected Highlights CRUD

Admin highlights editor:

- `admin/highlights.html`

Highlight API endpoints:

- `GET /api/highlights`
- `GET /api/highlights/{id}`
- `POST /api/highlights`
- `PATCH /api/highlights/{id}`
- `DELETE /api/highlights/{id}`

Highlight fields:

- title
- subtitle
- year_label
- highlight_url
- display_order
- is_active

## Personal Info CRUD

Admin personal info editor:

- `admin/personal-info.html`

Personal info API endpoints:

- `GET /api/personal-info`
- `POST /api/personal-info`
- `PATCH /api/personal-info`
- `DELETE /api/personal-info`

Personal info fields:

- full_name
- role_title
- description
- email
- phone
- address
- photo_path
- resume_url
- is_active

## Hero Content CRUD

Admin hero content editor:

- `admin/hero-content.html`

Hero content API endpoints:

- `GET /api/hero-content`
- `POST /api/hero-content`
- `PATCH /api/hero-content`
- `DELETE /api/hero-content`

Hero content fields:

- eyebrow
- title_line_1
- title_line_2
- description
- availability_text
- availability_location
- phone_label
- phone_url
- intro_video_label
- intro_video_url
- hero_media_type
- hero_media_path
- background_image_path
- is_active

## Site Identity CRUD

Admin site identity editor:

- `admin/site-identity.html`

Site identity API endpoints:

- `GET /api/site-identity`
- `POST /api/site-identity`
- `PATCH /api/site-identity`
- `DELETE /api/site-identity`

Site identity fields:

- site_title
- meta_description
- canonical_url
- logo_path
- header_icon_path
- favicon_path
- preloader_text
- youtube_url
- github_url
- instagram_url
- linkedin_url
- is_active

## Media Upload CRUD

Admin media library:

- `admin/media.html`

Media API endpoints:

- `GET /api/media-files`
- `GET /api/media-files/{id}`
- `POST /api/media-files`
- `PATCH /api/media-files/{id}`
- `DELETE /api/media-files/{id}`

Media upload behavior:

- Images are stored in `uploads/images`
- Videos are stored in `uploads/videos`
- Uploaded file metadata is stored in MySQL table `media_files`

## Analytics and Dashboard

Admin pages:

- `admin/dashboard.html`
- `admin/analytics.html`

Analytics API endpoints:

- `GET /api/analytics/summary`
- `GET /api/analytics/events`
- `POST /api/analytics/visit`
- `POST /api/analytics/event`

Analytics tables:

- `analytics_visits`
- `analytics_events`
