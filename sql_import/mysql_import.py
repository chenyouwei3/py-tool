import os
import pymysql
from pymysql import Error

# 数据库连接配置
db_config = {
    'host': '',      # 数据库主机
    'user': '',               # 数据库用户名
    'password': '',           # 数据库密码
    'database': '',           # 要导入的数据库
}

# SQL 文件所在目录
sql_directory = 'C:\\Users\\cheny\\Desktop\\py-tool\\sql_import'  # 替换为实际的文件夹路径

# 连接到数据库
def connect_to_db():
    try:
        connection = pymysql.connect(**db_config)
        print("成功连接到数据库")
        return connection
    except Error as e:
        print(f"数据库连接错误: {e}")
        return None

# 执行 SQL 文件
def execute_sql_file(cursor, sql_file_path):
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql = file.read()
            cursor.execute(sql)
            print(f"成功执行 SQL 文件: {sql_file_path}")
    except Exception as e:
        print(f"执行文件 {sql_file_path} 时出错: {e}")

# 批量导入 SQL 文件
def import_sql_files():
    connection = connect_to_db()
    if connection:
        cursor = connection.cursor()
        try:
            # 检查 SQL 文件目录是否存在
            if not os.path.exists(sql_directory):
                print(f"错误：指定的 SQL 文件夹路径不存在: {sql_directory}")
                return

            # 扫描目录下的所有 .sql 文件
            for root, dirs, files in os.walk(sql_directory):
                for file in files:
                    if file.endswith('.sql'):
                        sql_file_path = os.path.join(root, file)
                        execute_sql_file(cursor, sql_file_path)

            # 提交事务
            connection.commit()
            print("所有 SQL 文件已成功导入数据库。")
        except Exception as e:
            print(f"批量导入 SQL 文件时出错: {e}")
        finally:
            cursor.close()
            connection.close()
    else:
        print("无法连接到数据库，无法执行 SQL 文件导入。")

if __name__ == "__main__":
    import_sql_files()
