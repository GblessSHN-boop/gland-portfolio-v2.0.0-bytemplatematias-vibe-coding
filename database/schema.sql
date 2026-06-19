CREATE DATABASE IF NOT EXISTS gland_portfolio_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE gland_portfolio_db;

CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('owner', 'admin') DEFAULT 'owner',
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL,
    subject VARCHAR(200) DEFAULT NULL,
    message TEXT NOT NULL,
    status ENUM('new', 'read', 'approved', 'rejected', 'archived') DEFAULT 'new',
    admin_note TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site_identity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(150) NOT NULL DEFAULT 'Gland Siahaan Portfolio',
    header_logo VARCHAR(255) DEFAULT NULL,
    favicon VARCHAR(255) DEFAULT NULL,
    preloader_text VARCHAR(100) DEFAULT 'GLAND',
    preloader_logo VARCHAR(255) DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hero_content (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title_line_1 VARCHAR(150) NOT NULL DEFAULT 'AI Engineer',
    title_line_2 VARCHAR(150) NOT NULL DEFAULT 'Creative Designer',
    subtitle VARCHAR(255) DEFAULT NULL,
    background_image VARCHAR(255) DEFAULT NULL,
    right_video VARCHAR(255) DEFAULT NULL,
    intro_button_text VARCHAR(100) DEFAULT 'Intro Video',
    intro_video_url VARCHAR(255) DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS personal_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    photo VARCHAR(255) DEFAULT NULL,
    bio TEXT DEFAULT NULL,
    email VARCHAR(150) DEFAULT NULL,
    phone VARCHAR(80) DEFAULT NULL,
    address VARCHAR(150) DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS selected_highlights (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    category VARCHAR(150) NOT NULL,
    year_label VARCHAR(20) NOT NULL,
    sort_order INT DEFAULT 0,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(150) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT DEFAULT NULL,
    image VARCHAR(255) DEFAULT NULL,
    project_url VARCHAR(255) DEFAULT NULL,
    detail_url VARCHAR(255) DEFAULT NULL,
    sort_order INT DEFAULT 0,
    is_featured TINYINT(1) DEFAULT 1,
    is_active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS media_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    file_type VARCHAR(80) NOT NULL,
    alt_text VARCHAR(255) DEFAULT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analytics_visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id VARCHAR(120) NOT NULL,
    ip_hash VARCHAR(255) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    device_type VARCHAR(50) DEFAULT NULL,
    browser VARCHAR(80) DEFAULT NULL,
    referrer TEXT DEFAULT NULL,
    landing_page VARCHAR(255) DEFAULT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP NULL DEFAULT NULL,
    duration_seconds INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analytics_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id VARCHAR(120) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    event_target VARCHAR(255) DEFAULT NULL,
    page_url VARCHAR(255) DEFAULT NULL,
    section_name VARCHAR(120) DEFAULT NULL,
    metadata JSON DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT DEFAULT NULL,
    action VARCHAR(120) NOT NULL,
    target_type VARCHAR(120) DEFAULT NULL,
    target_id INT DEFAULT NULL,
    description TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE SET NULL
);

-- GLAND ADMIN AUTH SESSIONS START
CREATE TABLE IF NOT EXISTS admin_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    ip_address VARCHAR(64) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_admin_sessions_token_hash (token_hash),
    INDEX idx_admin_sessions_admin_id (admin_id),
    INDEX idx_admin_sessions_expires_at (expires_at),
    CONSTRAINT fk_admin_sessions_admin_id
        FOREIGN KEY (admin_id)
        REFERENCES admin_users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- GLAND ADMIN AUTH SESSIONS END

-- GLAND ADMIN LOGIN EVENTS START
CREATE TABLE IF NOT EXISTS admin_login_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NULL,
    event_type VARCHAR(50) NOT NULL,
    identifier VARCHAR(150) DEFAULT NULL,
    success TINYINT(1) DEFAULT 0,
    ip_address VARCHAR(64) DEFAULT NULL,
    user_agent TEXT DEFAULT NULL,
    message VARCHAR(255) DEFAULT NULL,
    alert_email_sent TINYINT(1) DEFAULT 0,
    alert_error TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_admin_login_events_admin_id (admin_id),
    INDEX idx_admin_login_events_event_type (event_type),
    INDEX idx_admin_login_events_success (success),
    INDEX idx_admin_login_events_created_at (created_at),
    CONSTRAINT fk_admin_login_events_admin_id
        FOREIGN KEY (admin_id)
        REFERENCES admin_users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- GLAND ADMIN LOGIN EVENTS END

-- GLAND ADMIN PASSWORD RESET TOKENS START
CREATE TABLE IF NOT EXISTS admin_password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    used_at DATETIME DEFAULT NULL,
    requested_ip VARCHAR(64) DEFAULT NULL,
    requested_user_agent TEXT DEFAULT NULL,
    email_sent TINYINT(1) DEFAULT 0,
    email_error TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_admin_password_reset_tokens_admin_id (admin_id),
    INDEX idx_admin_password_reset_tokens_token_hash (token_hash),
    INDEX idx_admin_password_reset_tokens_expires_at (expires_at),
    INDEX idx_admin_password_reset_tokens_used_at (used_at),
    CONSTRAINT fk_admin_password_reset_tokens_admin_id
        FOREIGN KEY (admin_id)
        REFERENCES admin_users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- GLAND ADMIN PASSWORD RESET TOKENS END
