-- Optional: example table for purchase logs (utf8mb4, indexed lookup column)
CREATE TABLE IF NOT EXISTS `{{RESOURCE_NAME}}_purchases` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `identifier` VARCHAR(64) NOT NULL,
    `item` VARCHAR(64) NOT NULL,
    `count` INT UNSIGNED NOT NULL,
    `total` INT UNSIGNED NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_identifier` (`identifier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
