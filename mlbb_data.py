import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from scipy import stats
import warnings
warnings.filterwarnings('ignore')   


def scrape_mlbb_data():
    url = 'https://mlbb.io/api/hero/filtered-statistics?rankId=6&timeframeId=5'
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,id;q=0.8,ga;q=0.7',
        'priority': 'u=1, i',
        'referer': 'https://mlbb.io/hero-statistics',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'x-client-secret': '259009191be734535393edc59e865dce'
    }
    
    cookies = {
        'locale': 'en',
        '__Host-next-auth.csrf-token': 'd1c994b1e4f940c46de8c79e8ffb04802fa5ab7a6837ba9d9e27f229eeeb4668%7C457f92ce86ec05a3782929593882a5276721a5c4ccfa4c35acb2ef11076eb38d',
        '__Secure-next-auth.callback-url': 'https%3A%2F%2Fmlbb.io',
        '_pk_id.1.cb63': '4efe70aa70b5b9d6.1764512705.',
        '_pk_ref.1.cb63': '%5B%22%22%2C%22%22%2C1764523742%2C%22https%3A%2F%2Fwww.google.com%2F%22%5D',
        '_pk_ses.1.cb63': '1'
    }
    

    response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
    response.raise_for_status()
    data = response.json()
    if data.get('success'):
        return data['data']



def create_dataset(hero_data):
    heroes = []
    
    for hero in hero_data:
        hero_info = {
            'hero_id': hero['hero_id'],
            'hero_name': hero['hero_name'],
            'role': hero['role'][0] if hero['role'] else 'Unknown',
            'lane': hero['lane'][0] if hero['lane'] else 'Unknown',
            'pick_rate': hero['pick_rate'],
            'win_rate': hero['win_rate'],
            'ban_rate': hero['ban_rate'],
            'speciality': ', '.join(hero['speciality']) if hero['speciality'] else 'Unknown'
        }
        heroes.append(hero_info)
    
    df = pd.DataFrame(heroes)
    return df




print("Step 1: Scraping data from MLBB API...")
hero_data = scrape_mlbb_data()

print("Step 2: Creating dataset...")
df = create_dataset(hero_data)
print(f"Dataset created with {len(df)} heroes")

output_file = 'mlbb_hero_datasets.csv'
df.to_csv(output_file, index=False)