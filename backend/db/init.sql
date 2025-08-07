-- backend/db/init.sql

-- Create the database
CREATE DATABASE IF NOT EXISTS `atlas_the_joy_of_painting_db`;
USE `atlas_the_joy_of_painting_db`;

-- 1. Episodes table
CREATE TABLE `episodes` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `season` INT,
    `episode` INT,
    `air_date` DATE,
    `youtube_src` VARCHAR(255),
    `img_src` VARCHAR(255),
    `num_colors` INT,
    `extra_info` JSON,
    PRIMARY KEY (`id`),
    UNIQUE KEY `unique_episode` (`season`, `episode`)
);

-- 2. Colors table
CREATE TABLE `colors` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL UNIQUE,
    `hex` VARCHAR(7) NOT NULL UNIQUE,
    PRIMARY KEY (`id`)
);

-- 3. Subjects table
CREATE TABLE `subjects` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL UNIQUE,
    PRIMARY KEY (`id`)
);

-- 4. Episode_Colors junction table
CREATE TABLE `episode_colors` (
    `episode_id` INT NOT NULL,
    `color_id` INT NOT NULL,
    PRIMARY KEY (`episode_id`, `color_id`),
    FOREIGN KEY (`episode_id`) REFERENCES `episodes`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`color_id`) REFERENCES `colors`(`id`) ON DELETE CASCADE
);

-- 5. Episode_Subjects junction table
CREATE TABLE `episode_subjects` (
    `episode_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    PRIMARY KEY (`episode_id`, `subject_id`),
    FOREIGN KEY (`episode_id`) REFERENCES `episodes`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE
);
