import json
import os
from config import DATA_FILES

def load_data(key, default=None):
    file = DATA_FILES[key]
    default = default or ({} if key != 'banned' else set())
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if key == 'banned':
                return set(data)
            return data
    return default

def save_data(key, data):
    file = DATA_FILES[key]
    with open(file, 'w', encoding='utf-8') as f:
        if key == 'banned':
            json.dump(list(data), f, ensure_ascii=False, indent=2)
        else:
            json.dump(data, f, ensure_ascii=False, indent=2) 
