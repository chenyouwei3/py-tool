CREATE TABLE `user_file` (
                                 `id` bigint NOT NULL  AUTO_INCREMENT,
                                 `user_id` bigint NOT NULL DEFAULT '0',
                                 `file_sha1` varchar(64) NOT NULL DEFAULT '' COMMENT '文件hash',
                                 `file_size` bigint(20) DEFAULT '0' COMMENT '文件大小',
                                 `file_name` varchar(256) NOT NULL DEFAULT '' COMMENT '文件名',
                                 `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                 `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                                 `delete_time` datetime ,
                                 `status` int(11) NOT NULL DEFAULT '0' COMMENT '文件状态(0正常1已删除2禁用)',
                                 PRIMARY KEY (`id`),
                                 UNIQUE KEY `idx_user_file` (`user_id`, `file_sha1`),
                                 KEY `idx_status` (`status`),
                                 KEY `idx_user_id` (`user_id`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8;