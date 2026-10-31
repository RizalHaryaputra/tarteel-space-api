-- ========================================================
-- Tarteel Space Clean Production Database Export
-- Compatible with MySQL 8.0, 8.4, and MariaDB
-- ========================================================

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
START TRANSACTION;
SET time_zone = '+00:00';

DROP TABLE IF EXISTS `dataset_pool`;
DROP TABLE IF EXISTS `user_feedbacks`;
DROP TABLE IF EXISTS `evaluations`;
DROP TABLE IF EXISTS `password_reset_tokens`;
DROP TABLE IF EXISTS `sessions`;
DROP TABLE IF EXISTS `hijaiyah_letters`;
DROP TABLE IF EXISTS `users`;

-- --------------------------------------------------------
-- 1. Table structure for `users`
CREATE TABLE `users` (
  `id` char(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(150) NOT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `auth_provider` varchar(50) DEFAULT 'local',
  `role` varchar(20) NOT NULL DEFAULT 'user',
  `avatar_url` varchar(500) DEFAULT NULL,
  `bio` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 2. Table structure for `hijaiyah_letters`
CREATE TABLE `hijaiyah_letters` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `base_letter` varchar(50) NOT NULL,
  `harakat` varchar(20) NOT NULL,
  `pronunciation` varchar(50) NOT NULL,
  `arabic_script` varchar(20) NOT NULL,
  `model_label` varchar(100) NOT NULL,
  `audio_url` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_letter_harakat` (`base_letter`,`harakat`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 3. Table structure for `sessions`
CREATE TABLE `sessions` (
  `id` char(36) NOT NULL,
  `user_id` char(36) NOT NULL,
  `started_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ended_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_sessions_user` (`user_id`),
  CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 4. Table structure for `password_reset_tokens`
CREATE TABLE `password_reset_tokens` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `token` varchar(64) NOT NULL,
  `expires_at` datetime NOT NULL,
  `used` tinyint(1) NOT NULL DEFAULT 0,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `fk_reset_tokens_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 5. Table structure for `evaluations`
CREATE TABLE `evaluations` (
  `id` char(36) NOT NULL,
  `user_id` char(36) NOT NULL,
  `session_id` char(36) DEFAULT NULL,
  `letter_id` int(11) NOT NULL,
  `audio_path` varchar(255) DEFAULT NULL,
  `accuracy_score` decimal(5,2) NOT NULL,
  `top_prediction` varchar(100) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `top3_predictions` text DEFAULT NULL,
  `is_verified` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_eval_user` (`user_id`),
  KEY `idx_eval_letter` (`letter_id`),
  KEY `idx_eval_session` (`session_id`),
  KEY `idx_eval_created` (`created_at`),
  CONSTRAINT `fk_eval_letter` FOREIGN KEY (`letter_id`) REFERENCES `hijaiyah_letters` (`id`),
  CONSTRAINT `fk_eval_session` FOREIGN KEY (`session_id`) REFERENCES `sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_eval_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 6. Table structure for `user_feedbacks`
CREATE TABLE `user_feedbacks` (
  `id` char(36) NOT NULL,
  `evaluation_id` char(36) NOT NULL,
  `user_id` char(36) NOT NULL,
  `comment` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_feedback_eval` (`evaluation_id`),
  KEY `idx_feedback_user` (`user_id`),
  CONSTRAINT `fk_feedback_eval` FOREIGN KEY (`evaluation_id`) REFERENCES `evaluations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_feedback_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 7. Table structure for `dataset_pool`
CREATE TABLE `dataset_pool` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `evaluation_id` char(36) NOT NULL,
  `verified_label` varchar(100) NOT NULL,
  `is_verified_correct` tinyint(1) NOT NULL DEFAULT 1,
  `admin_notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `is_used_for_training` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dataset_eval` (`evaluation_id`),
  CONSTRAINT `fk_dataset_eval` FOREIGN KEY (`evaluation_id`) REFERENCES `evaluations` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- Dumping data for table `users`
INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `created_at`, `auth_provider`, `role`, `avatar_url`, `bio`) VALUES
('0054066b-ddf0-4464-a2cf-489030614dbf', 'Joni', 'joni@gmail.com', '$2b$12$/MApsfaRnnQY8H2E8/6c1uYqD0ULmugDjuxNx16PxYlg3VHwK5j3q', '2026-05-01 13:54:59', 'local', 'user', NULL, NULL),
('26bf6a23-d7ae-4150-8e90-cc483f270c38', 'Haryaputra', 'rizalharyaputra.2023@student.uny.ac.id', '$2b$12$D6NArEgvX2n2GBOddYrAM.ElSYrLtScA2wkP4UC.83RFHv6TB/KK2', '2026-05-16 20:48:53', 'local', 'user', 'https://lh3.googleusercontent.com/a/ACg8ocI_fWeg5zhfNMrvrjOYp01KnOSMc9yWLAPdM0jVMArQtInOzg=s96-c', NULL),
('672b7a2e-7f0b-4f44-ab76-3ff51991c43d', 'Jono', 'jono@gmail.com', '$2b$12$ysJdd0AEq9K2E33Rp5hXre8piP2bPb.ADWIMo3gItH6xon/wndILO', '2026-05-01 13:48:01', 'local', 'user', NULL, NULL),
('6e659fb5-9aa3-4efa-9c80-f65f771131a5', 'rizal', 'rizal@gmail.com', '$2b$12$qbYhvrV7WLsOYSxuHF4pJe245J/IsPuT2GYjse1BgfRFON7CCaISy', '2026-04-29 22:49:01', 'local', 'user', NULL, NULL),
('81887ad9-3bdc-417b-9236-b111e3445c59', 'Rizal Haryaputra', 'rzlhryptr@gmail.com', NULL, '2026-05-17 09:22:58', 'github', 'admin', 'https://res.cloudinary.com/dothvi6d9/image/upload/v1781145069/tarteel_space_avatars/avatar_81887ad9-3bdc-417b-9236-b111e3445c59.jpg', NULL);

-- Dumping data for table `hijaiyah_letters`
INSERT INTO `hijaiyah_letters` (`id`, `base_letter`, `harakat`, `pronunciation`, `arabic_script`, `model_label`, `audio_url`) VALUES
(1, 'Alif', 'Fathah', 'A', 'أَ', 'alif_fathah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1780643093/letters_reference/ustadz_ref_1.wav'),
(2, 'Alif', 'Kasrah', 'I', 'إِ', 'alif_kasroh', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1780718703/letters_reference/ustadz_ref_2.wav'),
(3, 'Alif', 'Dhammah', 'U', 'أُ', 'alif_dommah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1780805573/letters_reference/ustadz_ref_3.wav'),
(4, 'Ba', 'Fathah', 'Ba', 'بَ', 'ba_fathah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781145138/letters_reference/ustadz_ref_4.wav'),
(5, 'Ba', 'Kasrah', 'Bi', 'بِ', 'ba_kasroh', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781145151/letters_reference/ustadz_ref_5.wav'),
(6, 'Ba', 'Dhammah', 'Bu', 'بُ', 'ba_dommah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781145165/letters_reference/ustadz_ref_6.wav'),
(7, 'Ta', 'Fathah', 'Ta', 'تَ', 'ta_fathah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781145190/letters_reference/ustadz_ref_7.wav'),
(8, 'Ta', 'Kasrah', 'Ti', 'تِ', 'ta_kasroh', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781145202/letters_reference/ustadz_ref_8.wav'),
(9, 'Ta', 'Dhammah', 'Tu', 'تُ', 'ta_dommah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781145214/letters_reference/ustadz_ref_9.wav'),
(10, 'Tsa', 'Fathah', 'Tsa', 'ثَ', 'tsa_fathah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781145228/letters_reference/ustadz_ref_10.wav'),
(11, 'Tsa', 'Kasrah', 'Tsi', 'ثِ', 'tsa_kasroh', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781150008/letters_reference/ustadz_ref_11.wav'),
(12, 'Tsa', 'Dhammah', 'Tsu', 'ثُ', 'tsa_dommah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781150024/letters_reference/ustadz_ref_12.wav'),
(13, 'Jim', 'Fathah', 'Ja', 'جَ', 'jim_fathah', 'https://res.cloudinary.com/dothvi6d9/video/upload/v1781150037/letters_reference/ustadz_ref_13.wav'),
(14, 'Jim', 'Kasrah', 'Ji', 'جِ', 'jim_kasroh', NULL),
(15, 'Jim', 'Dhammah', 'Ju', 'جُ', 'jim_dommah', NULL),
(16, 'Ha', 'Fathah', 'Ha', 'حَ', 'hah_fathah', NULL),
(17, 'Ha', 'Kasrah', 'Hi', 'حِ', 'hah_kasroh', NULL),
(18, 'Ha', 'Dhammah', 'Hu', 'حُ', 'hah_dommah', NULL),
(19, 'Kha', 'Fathah', 'Kha', 'خَ', 'kha_fathah', NULL),
(20, 'Kha', 'Kasrah', 'Khi', 'خِ', 'kha_kasroh', NULL),
(21, 'Kha', 'Dhammah', 'Khu', 'خُ', 'kha_dommah', NULL),
(22, 'Dal', 'Fathah', 'Da', 'دَ', 'dal_fathah', NULL),
(23, 'Dal', 'Kasrah', 'Di', 'دِ', 'dal_kasroh', NULL),
(24, 'Dal', 'Dhammah', 'Du', 'دُ', 'dal_dommah', NULL),
(25, 'Dzal', 'Fathah', 'Dza', 'ذَ', 'dzal_fathah', NULL),
(26, 'Dzal', 'Kasrah', 'Dzi', 'ذِ', 'dzal_kasroh', NULL),
(27, 'Dzal', 'Dhammah', 'Dzu', 'ذُ', 'dzal_dommah', NULL),
(28, 'Ra', 'Fathah', 'Ra', 'رَ', 'ra_fathah', NULL),
(29, 'Ra', 'Kasrah', 'Ri', 'رِ', 'ra_kasroh', NULL),
(30, 'Ra', 'Dhammah', 'Ru', 'رُ', 'ra_dommah', NULL),
(31, 'Zai', 'Fathah', 'Za', 'زَ', 'zay_fathah', NULL),
(32, 'Zai', 'Kasrah', 'Zi', 'زِ', 'zay_kasroh', NULL),
(33, 'Zai', 'Dhammah', 'Zu', 'زُ', 'zay_dommah', NULL),
(34, 'Sin', 'Fathah', 'Sa', 'سَ', 'sin_fathah', NULL),
(35, 'Sin', 'Kasrah', 'Si', 'سِ', 'sin_kasroh', NULL),
(36, 'Sin', 'Dhammah', 'Su', 'سُ', 'sin_dommah', NULL),
(37, 'Syin', 'Fathah', 'Sya', 'شَ', 'shin_fathah', NULL),
(38, 'Syin', 'Kasrah', 'Syi', 'شِ', 'shin_kasroh', NULL),
(39, 'Syin', 'Dhammah', 'Syu', 'شُ', 'shin_dommah', NULL),
(40, 'Shad', 'Fathah', 'Sha', 'صَ', 'sad_fathah', NULL),
(41, 'Shad', 'Kasrah', 'Shi', 'صِ', 'sad_kasroh', NULL),
(42, 'Shad', 'Dhammah', 'Shu', 'صُ', 'sad_dommah', NULL),
(43, 'Dhad', 'Fathah', 'Dha', 'ضَ', 'dad_fathah', NULL),
(44, 'Dhad', 'Kasrah', 'Dhi', 'ضِ', 'dad_kasroh', NULL),
(45, 'Dhad', 'Dhammah', 'Dhu', 'ضُ', 'dad_dommah', NULL),
(46, 'Tha', 'Fathah', 'Tha', 'طَ', 'tah_fathah', NULL),
(47, 'Tha', 'Kasrah', 'Thi', 'طِ', 'tah_kasroh', NULL),
(48, 'Tha', 'Dhammah', 'Thu', 'طُ', 'tah_dommah', NULL),
(49, 'Zha', 'Fathah', 'Zha', 'ظَ', 'zah_fathah', NULL),
(50, 'Zha', 'Kasrah', 'Zhi', 'ظِ', 'zah_kasroh', NULL),
(51, 'Zha', 'Dhammah', 'Zhu', 'ظُ', 'zah_dommah', NULL),
(52, 'Ain', 'Fathah', 'Aa', 'عَ', 'ain_fathah', NULL),
(53, 'Ain', 'Kasrah', 'Ii', 'عِ', 'ain_kasroh', NULL),
(54, 'Ain', 'Dhammah', 'Uu', 'عُ', 'ain_dommah', NULL),
(55, 'Ghain', 'Fathah', 'Gha', 'غَ', 'ghaiin_fathah', NULL),
(56, 'Ghain', 'Kasrah', 'Ghi', 'غِ', 'ghaiin_kasroh', NULL),
(57, 'Ghain', 'Dhammah', 'Ghu', 'غُ', 'ghaiin_dommah', NULL),
(58, 'Fa', 'Fathah', 'Fa', 'فَ', 'fa_fathah', NULL),
(59, 'Fa', 'Kasrah', 'Fi', 'فِ', 'fa_kasroh', NULL),
(60, 'Fa', 'Dhammah', 'Fu', 'فُ', 'fa_dommah', NULL),
(61, 'Qaf', 'Fathah', 'Qa', 'قَ', 'qaf_fathah', NULL),
(62, 'Qaf', 'Kasrah', 'Qi', 'قِ', 'qaf_kasroh', NULL),
(63, 'Qaf', 'Dhammah', 'Qu', 'قُ', 'qaf_dommah', NULL),
(64, 'Kaf', 'Fathah', 'Ka', 'كَ', 'kaf_fathah', NULL),
(65, 'Kaf', 'Kasrah', 'Ki', 'كِ', 'kaf_kasroh', NULL),
(66, 'Kaf', 'Dhammah', 'Ku', 'كُ', 'kaf_dommah', NULL),
(67, 'Lam', 'Fathah', 'La', 'لَ', 'lam_fathah', NULL),
(68, 'Lam', 'Kasrah', 'Li', 'لِ', 'lam_kasroh', NULL),
(69, 'Lam', 'Dhammah', 'Lu', 'لُ', 'lam_dommah', NULL),
(70, 'Mim', 'Fathah', 'Ma', 'مَ', 'mim_fathah', NULL),
(71, 'Mim', 'Kasrah', 'Mi', 'مِ', 'mim_kasroh', NULL),
(72, 'Mim', 'Dhammah', 'Mu', 'مُ', 'mim_dommah', NULL),
(73, 'Nun', 'Fathah', 'Na', 'نَ', 'nun_fathah', NULL),
(74, 'Nun', 'Kasrah', 'Ni', 'نِ', 'nun_kasroh', NULL),
(75, 'Nun', 'Dhammah', 'Nu', 'نُ', 'nun_dommah', NULL),
(76, 'Waw', 'Fathah', 'Wa', 'وَ', 'Ha_fathah', NULL),
(77, 'Waw', 'Kasrah', 'Wi', 'وِ', 'Ha_kasroh', NULL),
(78, 'Waw', 'Dhammah', 'Wu', 'وُ', 'Ha_dommah', NULL),
(79, 'Ha2', 'Fathah', 'Ha', 'هَ', 'waw_fathah', NULL),
(80, 'Ha2', 'Kasrah', 'Hi', 'هِ', 'waw_kasroh', NULL),
(81, 'Ha2', 'Dhammah', 'Hu', 'هُ', 'waw_dommah', NULL),
(82, 'Ya', 'Fathah', 'Ya', 'يَ', 'ya_fathah', NULL),
(83, 'Ya', 'Kasrah', 'Yi', 'يِ', 'ya_kasroh', NULL),
(84, 'Ya', 'Dhammah', 'Yu', 'يُ', 'ya_dommah', NULL);

SET FOREIGN_KEY_CHECKS = 1;
COMMIT;