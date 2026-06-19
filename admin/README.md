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
