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
