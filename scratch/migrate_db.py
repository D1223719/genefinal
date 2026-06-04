import sqlite3
import glob

# 找到所有 db 檔案
dbs = glob.glob('*.db') + glob.glob('**/*.db', recursive=True)
print('Found DBs:', dbs)

for db_path in dbs:
    print(f'Processing: {db_path}')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(weakness_memories)")
    rows = cur.fetchall()
    cols = [row[1] for row in rows]
    print('Existing columns:', cols)
    
    if cols:  # 表存在
        if 'correct_count' not in cols:
            cur.execute('ALTER TABLE weakness_memories ADD COLUMN correct_count INTEGER DEFAULT 0')
            print('Added correct_count')
        if 'total_count' not in cols:
            cur.execute('ALTER TABLE weakness_memories ADD COLUMN total_count INTEGER DEFAULT 0')
            print('Added total_count')
        if 'mastery_rate' not in cols:
            cur.execute('ALTER TABLE weakness_memories ADD COLUMN mastery_rate FLOAT DEFAULT 0.0')
            print('Added mastery_rate')
        conn.commit()
        print('Migration done for:', db_path)
    else:
        print('Table weakness_memories not found in:', db_path)
    conn.close()

print('All done!')
