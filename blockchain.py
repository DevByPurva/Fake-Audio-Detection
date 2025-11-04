import hashlib
import time
import sqlite3

class Blockchain:
    def __init__(self):
        self.chain = []
        self.load_chain_from_db()  # Load existing chain from the database or create genesis block

    def create_genesis_block(self):
        """Create the first block in the blockchain (genesis block)"""
        genesis_block = self.create_new_block('GENESIS', 0, 'GENESIS')
        self.chain.append(genesis_block)
        self.save_block_to_db(genesis_block)

    def create_new_block(self, predicted_label, confidence, prev_hash=''):
        """
        Function to create a new block and append it to the blockchain.
        The block stores the prediction label and confidence score.
        """
        block = {
            'block_index': len(self.chain),
            'timestamp': time.time(),
            'predicted_label': predicted_label,
            'confidence': confidence,
            'prev_hash': prev_hash,
            'hash': ''
        }

        block['hash'] = self.calculate_hash(block)
        self.chain.append(block)
        self.save_block_to_db(block)
        return block

    def calculate_hash(self, block):
        """
        Function to calculate the hash of a block. We use the SHA-256 algorithm.
        """
        block_string = str(block['block_index']) + str(block['timestamp']) + block['predicted_label'] + str(block['confidence']) + block['prev_hash']
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()

    def get_last_block(self):
        """
        Function to get the last block in the chain.
        """
        return self.chain[-1] if len(self.chain) > 0 else None

    def load_chain_from_db(self):
        """Load the blockchain from the database."""
        conn = sqlite3.connect('blockchain.db')
        c = conn.cursor()
        c.execute('SELECT * FROM blocks ORDER BY block_index ASC')  # Updated column name
        rows = c.fetchall()
        for row in rows:
            block = {
                'block_index': row[0],
                'timestamp': row[1],
                'predicted_label': row[2],
                'confidence': row[3],
                'prev_hash': row[4],
                'hash': row[5]
            }
            self.chain.append(block)
        conn.close()

    def save_block_to_db(self, block):
        """Save the block to the database."""
        conn = sqlite3.connect('blockchain.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO blocks (timestamp, predicted_label, confidence, prev_hash, hash)
            VALUES (?, ?, ?, ?, ?)
        ''', (block['timestamp'], block['predicted_label'], block['confidence'], block['prev_hash'], block['hash']))
        conn.commit()
        conn.close()
