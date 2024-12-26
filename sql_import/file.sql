CREATE TABLE `file` (
                            `id` bigint NOT NULL AUTO_INCREMENT,
                            `file_sha1` char(40) NOT NULL DEFAULT '' COMMENT '文件hash',
                            `file_name` varchar(256) NOT NULL DEFAULT '' COMMENT '文件名',
                            `file_size` bigint(20) DEFAULT '0' COMMENT '文件大小',
                            `file_addr` varchar(1024) NOT NULL DEFAULT '' COMMENT '文件存储位置',
                            `status` int(11) NOT NULL DEFAULT '0' COMMENT '状态(可用/禁用/已删除等状态)',
                            `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            `delete_time` datetime ,
                            PRIMARY KEY (`id`),
                            UNIQUE KEY `idx_file_hash` (`file_sha1`),
                            KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
