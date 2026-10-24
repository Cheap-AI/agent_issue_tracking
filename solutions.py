Given : A dictionary where keys are alphabets and values are integers, and given another integer : k,
Task : Write a function called group_keys_by_frequency_of_values that works for any such dictionary of arbitrary length n and returns the expected output based on the value of k.
Constraints: 0 < n < 100 & 0 < k < 100

input_dict = {"a":8, "b":5, "c":8, "d":4, "e":7, "f":7, "g":1, "h":9, "j":3}


k= 2
# output for k=3 []
# output for k=2 [['a', 'c'], ['e', 'f']]
# output for k=1 [['b'], ['d'], ['g'], ['h'], ['j']]

from collections import Counter

def group_keys_by_frequency_of_values(input_dict,k):
    Count_k = Counter(input_dict.values())
    #['8':2, '5':1, '4':1 ...]
    res = []
    for key, value in Count_k.items():
        if value == k:
            res.append([i_key for i_key, i_value in input_dict.items() if i_value==key])
    return res
            
    def maximum_subarray(nums):
        #[2,-6,5,3,7,-2,-5]
        cum_sum = 0
        max_sum = 0

        for n in nums:
            if cum_sum <= 0:
                cum_sum = n
            else:
                cum_sum += n
            max_sum = max(max_sum, cum_sum)
        return max_sum

    from collections import Counter

    def first_uniq_char(s: str) -> int:
        char_dict = Counter(s)

        for i, char in enumerate(s):
            if char_dict.get(char) == 1:
                return i
        return -1

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from confluent_kafka import Consumer, KafkaError
import redis

# 1. Initialize Redis for caching/deduplication to shield the downstream DB
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# 2. Setup a Thread Pool to handle slow downstream operations asynchronously
executor = ThreadPoolExecutor(max_workers=10)

def process_claim_downstream(claim_payload):
    """
    This runs inside a separate background worker thread.
    Even if this API call takes 10 seconds, it won't time out Kafka!
    """
    claim_id = claim_payload.get("claim_id")
    try:
        # Check Redis first: Have we already processed this in the last hour? (Idempotency)
        if redis_client.get(f"processed:{claim_id}"):
            return  # Skip duplicate

        # Simulate a slow external network call to your medical clearinghouse
        # response = requests.post("https://downstream.com", json=claim_payload, timeout=5)
        
        # If successful, cache the state in Redis for 1 hour
        redis_client.setex(f"processed:{claim_id}", 3600, "success")
        logging.info(f"Successfully processed claim {claim_id}")
        
    except Exception as e:
        logging.error(f"Downstream failure for claim {claim_id}: {e}")
        # In production, route to a Dead Letter Queue (DLQ) topic here [1.10]

def start_consumer():
    conf = {
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'medical-claims-v1',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True, # Let the background thread client auto-commit
        'max.poll.interval.ms': 300000 # 5 minutes threshold [1.6]
    }

    consumer = Consumer(conf)
    consumer.subscribe(['medical-claims-topic'])

    try:
        while True:
            # Poll must happen continuously to keep the consumer group alive!
            msg = consumer.poll(timeout=1.0) 
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logging.error(f"Kafka Error: {msg.error()}")
                    break

            # A valid message arrived! Parse it rapidly in-memory
            try:
                claim_data = json.loads(msg.value().decode('utf-8'))
                
                # ASYNC HANDOFF: Dispatch the slow database/API work to the thread pool.
                # This returns instantly, allowing the loop to immediately hit consumer.poll() again.
                executor.submit(process_claim_downstream, claim_data)
                
            except Exception as parse_err:
                logging.error(f"Serialization error: {parse_err}")

    finally:
        consumer.close()
        executor.shutdown(wait=True)

if __name__ == "__main__":
    start_consumer()
