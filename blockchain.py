import hashlib
import json
from datetime import datetime
from typing import Optional, List


class Block(object):
    __slots__ = ('index', 'previous_hash', 'timestamp', 'data', 'hash')

    def __init__(self, index: int, previous_hash: str, timestamp: int, data: str, hash: Optional[str]):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.hash = hash

    def __eq__(self, other) -> bool:
        return self.index == other.index and self.previous_hash == other.previous_hash \
               and self.timestamp == other.timestamp and self.data == other.data and self.hash == other.hash

    def dict(self):
        return {'index': self.index, 'previous_hash': self.previous_hash,
                'timestamp': self.timestamp, 'data': self.data, 'hash': self.hash}


class Blockchain(object):
    def __init__(self, debug=False):
        self.debug = debug
        self._blockchain = [self.generate_genesis_block()]

    @property
    def blocks(self):
        return self._blockchain

    @property
    def length(self):
        return len(self._blockchain)

    @property
    def genesis_block(self):
        return self._blockchain[0]

    @property
    def latest_block(self) -> Block:
        return self._blockchain[-1]

    @staticmethod
    def generate_genesis_block() -> Block:
        return Block(0, '0', 1465154705, 'my genesis block!!',
                     '816534932c2b7154836da6afc367695e6337db8a921823784c14378abed4f7d7')

    @classmethod
    def calculate_hash_for_block(cls, block: Block) -> str:
        return cls.calculate_hash(block.index, block.previous_hash, block.timestamp, block.data)

    @staticmethod
    def calculate_hash(index: int, previous_hash: str, timestamp: int, data: str):
        data_str = str(index) + previous_hash + str(timestamp) + data
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def is_valid_new_block(self, block: Block) -> bool:
        return self.is_valid_block(block, self.latest_block)

    def is_valid_block(self, block: Block, previous_block: Block) -> bool:
        if previous_block.index + 1 != block.index:
            self.log('invalid index')
            return False
        if previous_block.hash != block.previous_hash:
            self.log('invalid previoushash')
            return False
        if self.calculate_hash_for_block(block) != block.hash:
            self.log('invalid hash')
            return False
        return True

    def add_block(self, block: Block):
        if self.is_valid_new_block(block):
            self._blockchain.append(block)

    def generate_new_block(self, data: str) -> Block:
        new_index = self.latest_block.index + 1
        new_timestamp = datetime.utcnow().timestamp()
        new_hash = self.calculate_hash(new_index, self.latest_block.hash, new_timestamp, data)

        return Block(new_index, self.latest_block.hash, new_timestamp, data, new_hash)

    def is_valid_chain(self, chain: List[Block]) -> bool:
        if self.genesis_block != chain[0]:
            self.log('Wrong genesis block')
            return False

        return all(self.is_valid_block(chain[i+1], chain[i]) for i in range(len(chain) - 1))

    def replace_chain(self, blocks: List[Block]):
        if self.is_valid_chain(blocks) and len(blocks) > self.length:
            self._blockchain = blocks
        else:
            self.log('Received blockchain invalid')

    def json(self):
        return json.dumps([b.dict() for b in self.blocks])

    def log(self, msg):
        if self.debug:
            print(msg)
