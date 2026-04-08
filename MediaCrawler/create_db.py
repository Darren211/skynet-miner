import pymysql

try:
    conn = pymysql.connect(host='localhost', user='root', password='12345678')
    cursor = conn.cursor()
    cursor.execute('CREATE DATABASE IF NOT EXISTS media_crawler DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;')
    conn.commit()
    cursor.close()
    conn.close()
    print("Database media_crawler created successfully.")
except Exception as e:
    print(f"Failed to create database: {e}")
