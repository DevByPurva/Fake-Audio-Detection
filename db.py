import sqlite3

def create_blockchain_db():
    # Connect to SQLite database (it will create if doesn't exist)
    conn = sqlite3.connect('blockchain.db')
    c = conn.cursor()

    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS blocks (
            block_index INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            predicted_label TEXT,
            confidence REAL,
            prev_hash TEXT,
            hash TEXT
        )
    ''')

    # Commit and close
    conn.commit()
    conn.close()

# Call this function once to initialize the database
create_blockchain_db()
