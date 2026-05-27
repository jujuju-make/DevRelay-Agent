"""添加 sub_type 列到 reports 表。"""
import pymysql
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    url = settings.database_url
    # mysql+aiomysql://user:pass@host:port/db
    prefix = "mysql+aiomysql://"
    rest = url[len(prefix):]
    user_pass, host_db = rest.split("@")
    user, password = user_pass.split(":")
    host_part, db_part = host_db.split("/")
    host = host_part.split(":")[0]
    port = int(host_part.split(":")[1]) if ":" in host_part else 3306
    database = db_part.split("?")[0]

    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM reports LIKE 'sub_type'")
            if not cursor.fetchone():
                sql = "ALTER TABLE reports ADD COLUMN sub_type VARCHAR(32) DEFAULT NULL COMMENT 'sub type: auto_digest/manual'"
                cursor.execute(sql)
                print("OK: added sub_type column to reports table")
            else:
                print("OK: sub_type column already exists")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        conn.close()
