#!/usr/bin/env python3


from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import requests
import csv
import time
import os
import re
from typing import List, Dict
from itertools import cycle
import threading

# ---------------------------
# Config
# ---------------------------
MAX_WORKERS = 10           # Thread pool size
REQUEST_TIMEOUT = 20
RETRIES = 3
RETRY_BACKOFF = 1.5
OUTPUT_DIR = "tournaments"
MASTER_CSV = "mlbb_hero_stats_master.csv"

# Proxy rotation
PROXIES_LIST = [
    "127.0.0.1:60000",
    "127.0.0.1:60001",
    "127.0.0.1:60002",
    "127.0.0.1:60003",
]

# Thread-safe proxy rotation
proxy_cycle = cycle(PROXIES_LIST)
proxy_lock = threading.Lock()

def get_next_proxy():
    """Get next proxy in rotation (thread-safe)"""
    with proxy_lock:
        proxy_addr = next(proxy_cycle)
    return {
        "http": f"http://{proxy_addr}",
        "https": f"http://{proxy_addr}",
    }

# Cookies & Headers
COOKIES = {
    '_pk_id.1.4442': '49e248808a9df0bd.1764516360.',
    'AMP_MKTG_e0b3a97842': 'JTdCJTdE',
    '_pk_ses.1.4442': '1',
    '_gid': 'GA1.2.1907129899.1765175641',
    'CI': '467357707',
    '_ga': 'GA1.1.873935266.1764516355',
    'AMP_e0b3a97842': 'JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjI4OTkwMTE2NC1lNGQzLTQ3M2YtYjgwMy02ZDc2NDA4OTAwNDUlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzY1MTc1NjQyMDExJTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc2NTE4MTUyMjY3NSUyQyUyMmxhc3RFdmVudElkJTIyJTNBMzQxJTJDJTIycGFnZUNvdW50ZXIlMjIlM0EzNiU3RA==',
    '_ga_3TE8DNE0DL': 'GS2.1.s1765175640$o3$g1$t1765181526$j52$l0$h0',
    '_ga_98E1TX5TKZ': 'GS2.1.s1765175641$o4$g1$t1765181526$j52$l0$h0',
}

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9,id;q=0.8,ga;q=0.7',
    'cache-control': 'max-age=0',
    'priority': 'u=0, i',
    'referer': 'https://liquipedia.net/mobilelegends/MPL/Philippines/Season_1/Statistics',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    # 'cookie': '_pk_id.1.4442=49e248808a9df0bd.1764516360.; AMP_MKTG_e0b3a97842=JTdCJTdE; _pk_ses.1.4442=1; _gid=GA1.2.1907129899.1765175641; CI=467357707; _ga=GA1.1.873935266.1764516355; AMP_e0b3a97842=JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjI4OTkwMTE2NC1lNGQzLTQ3M2YtYjgwMy02ZDc2NDA4OTAwNDUlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzY1MTc1NjQyMDExJTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc2NTE4MTUyMjY3NSUyQyUyMmxhc3RFdmVudElkJTIyJTNBMzQxJTJDJTIycGFnZUNvdW50ZXIlMjIlM0EzNiU3RA==; _ga_3TE8DNE0DL=GS2.1.s1765175640$o3$g1$t1765181526$j52$l0$h0; _ga_98E1TX5TKZ=GS2.1.s1765175641$o4$g1$t1765181526$j52$l0$h0',
}


# ---------------------------
# Parse statistics table
# ---------------------------

# Known MLBB heroes list for validation
VALID_HEROES = {
    "Akai", "Alucard", "Aulus", "Bane", "Aldous", "Balmond", "Angela", "Atlas", "Alpha", "Alice",
    "Badang", "Arlott", "Aamon", "Aurora", "Argus", "Baxia", "Barats", "Beatrix", "Benedetta", "Belerick",
    "Brody", "Bruno", "Carmilla", "Cecilion", "Cici", "Chip", "Chang'e", "Clint", "Chou", "Claude",
    "Cyclops", "Diggie", "Dyrroth", "Edith", "Esmeralda", "Eudora", "Estes", "Fanny", "Faramis", "Floryn",
    "Gord", "Grock", "Granger", "Gloo", "Franco", "Fredrinn", "Gatotkaca", "Freya", "Gusion", "Guinevere",
    "Hanzo", "Hanabi", "Harith", "Harley", "Hayabusa", "Hilda", "Helcurt", "Hylos", "Jawhead", "Ixia",
    "Johnson", "Irithel", "Joy", "Kadita", "Julian", "Kalea", "Kagura", "Kaja", "Karina", "Karrie",
    "Khaleed", "Khufra", "Kimmy", "Lapu-Lapu", "Lancelot", "Leomord", "Layla", "Lesley", "Ling", "Lolita",
    "Martis", "Luo Yi", "Lukas", "Lunox", "Lylia", "Mathilda", "Masha", "Melissa", "Minotaur", "Moskov",
    "Minsitthar", "Miya", "Nana", "Natalia", "Natan", "Nolan", "Obsidia", "Odette", "Paquito", "Novaria",
    "Pharsa", "Popol and Kupa", "Phoveus", "Rafaela", "Roger", "Saber", "Ruby", "Selena", "Silvanna", "Sun",
    "Suyou", "Terizla", "Thamuz", "Tigreal", "Uranus", "Valir", "Valentina", "Vale", "Vexana", "Wanwan",
    "X.Borg", "Yi Sun-shin", "Xavier", "Yin", "Yu Zhong", "Yve", "Zetian", "Zhask", "Zhuxin", "Zilong",
    "Popol & Kupa"  # Alternative spelling
}

def parse_stats_table(table, tournament):
    """Parse MLBB Liquipedia /Statistics table"""
    hero_data = []
    tbody = table.find("tbody") or table
    
    # Find rows with class "dota-stat-row" (MLBB uses dota class names)
    rows = tbody.find_all("tr", class_="dota-stat-row")
    
    # If no dota-stat-row found, try regular tr rows
    if not rows:
        rows = tbody.find_all("tr")

    for row in rows:
        # Skip header rows
        if row.find("th") and not row.find("td"):
            continue

        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        # 1. HERO NAME (column index 1)
        hero_name = ""
        hero_cell = cells[1] if len(cells) > 1 else cells[0]
        
        # Try finding link with href containing "/mobilelegends/" and hero name
        hero_links = hero_cell.find_all("a", href=True)
        for link in hero_links:
            href = link.get("href", "")
            # Check if this is a hero link (not team, tournament, etc.)
            if "/mobilelegends/" in href and not any(x in href.lower() for x in ["/mpl/", "/team", "/tournament", "/league", "/special:", "/index.php"]):
                title = link.get("title", "")
                if title and not title.startswith("Category:"):
                    hero_name = title
                    break
                # Fallback to link text
                text = link.get_text(strip=True)
                if text:
                    hero_name = text
                    break
        
        if not hero_name:
            continue

        # Clean hero name
        hero_name = hero_name.replace("[e]", "").replace("[h]", "").strip()
        
        # VALIDATION: Check if this is a valid hero name
        if hero_name not in VALID_HEROES:
            # Try case-insensitive match
            hero_match = None
            for valid_hero in VALID_HEROES:
                if valid_hero.lower() == hero_name.lower():
                    hero_match = valid_hero
                    break
            
            if not hero_match:
                # Skip non-hero entries (like team names)
                continue
            else:
                hero_name = hero_match

        # 2. PICK DATA
        # Table structure from HTML (20 columns total):
        # Col 0: Rank
        # Col 1: Hero (with icon and name)
        # Col 2: Pick ∑ (total)
        # Col 3: Pick W (wins)
        # Col 4: Pick L (losses)
        # Col 5: WR (win rate %)
        # Col 6: %T (% of total games)
        # Col 7-10: Blue Side stats
        # Col 11-14: Red Side stats
        # Col 15: Bans ∑ (ban count)
        # Col 16: Bans %T
        # Col 17: P&B ∑ (picks + bans total)
        # Col 18: P&B %T
        # Col 19: Details (show/x buttons)
        
        if len(cells) < 16:
            continue
        
        try:
            # Extract numeric values, removing all non-digit characters
            pick_total_text = cells[2].get_text(strip=True)
            pick_wins_text = cells[3].get_text(strip=True)
            pick_losses_text = cells[4].get_text(strip=True)
            ban_count_text = cells[15].get_text(strip=True)
            
            # Remove any non-numeric characters (commas, spaces, etc.)
            pick_total = int(re.sub(r'\D', '', pick_total_text)) if pick_total_text else 0
            pick_wins = int(re.sub(r'\D', '', pick_wins_text)) if pick_wins_text else 0
            pick_losses = int(re.sub(r'\D', '', pick_losses_text)) if pick_losses_text else 0
            ban_count = int(re.sub(r'\D', '', ban_count_text)) if ban_count_text else 0
            
            # Skip if no valid data
            if pick_total == 0 and pick_wins == 0 and pick_losses == 0:
                continue
                
        except (ValueError, IndexError) as e:
            # Debug: print which hero failed
            print(f"    ⚠ Parse error for {hero_name}: {str(e)}")
            continue

        hero_data.append({
            "hero": hero_name,
            "pick_total": pick_total,
            "pick_wins": pick_wins,
            "pick_losses": pick_losses,
            "ban_count": ban_count,
            "win_rate": round((pick_wins / pick_total * 100), 2) if pick_total else 0,
            "tournament_year": tournament.get("year"),
            "tournament_title": tournament.get("title"),
            "tournament_url": tournament.get("url")
        })

    return hero_data

# ---------------------------
# Tournaments list
# ---------------------------
tournaments = [
    # ===== 2018 =====
    {"year": 2018, "title": "MPL Indonesia Season 1", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_1/Statistics"},
    {"year": 2018, "title": "MPL MYSG Season 1", "url": "https://liquipedia.net/mobilelegends/MPL/MYSG/Season_1/Statistics"},
    {"year": 2018, "title": "MPL Philippines Season 1", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_1/Statistics"},
    {"year": 2018, "title": "MSC 2018", "url": "https://liquipedia.net/mobilelegends/MSC/2018/Statistics"},
    {"year": 2018, "title": "MPL MYSG Season 2", "url": "https://liquipedia.net/mobilelegends/MPL/MYSG/Season_2/Statistics"},
    {"year": 2018, "title": "MPL Indonesia Season 2", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_2/Statistics"},

    # ===== 2019–2020 =====
    {"year": 2019, "title": "MPL Philippines Season 2", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_2/Statistics"},
    {"year": 2019, "title": "MPL MYSG Season 3", "url": "https://liquipedia.net/mobilelegends/MPL/MYSG/Season_3/Statistics"},
    {"year": 2019, "title": "MPL Indonesia Season 3", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_3/Statistics"},
    {"year": 2019, "title": "MPL Philippines Season 3", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_3/Statistics"},
    {"year": 2019, "title": "MSC 2019", "url": "https://liquipedia.net/mobilelegends/MSC/2019/Statistics"},
    {"year": 2019, "title": "MPL Philippines Season 4", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_4/Statistics"},
    {"year": 2019, "title": "MPL MYSG Season 4", "url": "https://liquipedia.net/mobilelegends/MPL/MYSG/Season_4/Statistics"},
    {"year": 2019, "title": "MPL Myanmar Season 3", "url": "https://liquipedia.net/mobilelegends/MPL/Myanmar/Season_3/Statistics"},
    {"year": 2019, "title": "MPL Indonesia Season 4", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_4/Statistics"},
    {"year": 2020, "title": "MPL Indonesia Season 5", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_5/Statistics"},
    {"year": 2020, "title": "MPL MYSG Season 5", "url": "https://liquipedia.net/mobilelegends/MPL/MYSG/Season_5/Statistics"},
    {"year": 2020, "title": "MPL Philippines Season 5", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_5/Statistics"},
    {"year": 2020, "title": "MPL Myanmar Season 4", "url": "https://liquipedia.net/mobilelegends/MPL/Myanmar/Season_4/Statistics"},
    {"year": 2020, "title": "MPLI 4 Nation Cup", "url": "https://liquipedia.net/mobilelegends/MPLI_4_Nation_Cup/Statistics"},
    {"year": 2020, "title": "MPL Indonesia Season 6", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_6/Statistics"},
    {"year": 2020, "title": "MPL Philippines Season 6", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_6/Statistics"},
    {"year": 2020, "title": "MPL MYSG Season 6", "url": "https://liquipedia.net/mobilelegends/MPL/MYSG/Season_6/Statistics"},
    {"year": 2020, "title": "MPL Myanmar Season 5", "url": "https://liquipedia.net/mobilelegends/MPL/Myanmar/Season_5/Statistics"},
    {"year": 2020, "title": "ONE Esports MPL Invitational 2020", "url": "https://liquipedia.net/mobilelegends/ONE_Esports_MPL_Invitational/2020/Statistics"},

    # ===== 2021 =====
    {"year": 2021, "title": "MPL Indonesia Season 7", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_7/Statistics"},
    {"year": 2021, "title": "MPL Singapore Season 1", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_1/Statistics"},
    {"year": 2021, "title": "MPL Philippines Season 7", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_7/Statistics"},
    {"year": 2021, "title": "MPL Malaysia Season 7", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_7/Statistics"},
    {"year": 2021, "title": "MSC 2021", "url": "https://liquipedia.net/mobilelegends/MSC/2021/Statistics"},
    {"year": 2021, "title": "MPL Singapore Season 2", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_2/Statistics"},
    {"year": 2021, "title": "MPL Malaysia Season 8", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_8/Statistics"},
    {"year": 2021, "title": "MPL Philippines Season 8", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_8/Statistics"},
    {"year": 2021, "title": "MPL Indonesia Season 8", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_8/Statistics"},
    {"year": 2021, "title": "ONE Esports MPL Invitational 2021", "url": "https://liquipedia.net/mobilelegends/ONE_Esports_MPL_Invitational/2021/Statistics"},

    # ===== 2022 =====
    {"year": 2022, "title": "MPL Indonesia Season 9", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_9/Statistics"},
    {"year": 2022, "title": "MPL Malaysia Season 9", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_9/Statistics"},
    {"year": 2022, "title": "MPL Philippines Season 9", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_9/Statistics"},
    {"year": 2022, "title": "MPL Singapore Season 3", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_3/Statistics"},
    {"year": 2022, "title": "MPL MENA Spring 2022", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/2022/Spring/Statistics"},
    {"year": 2022, "title": "MSC 2022", "url": "https://liquipedia.net/mobilelegends/MSC/2022/Statistics"},
    {"year": 2022, "title": "Liga Latam Season 2", "url": "https://liquipedia.net/mobilelegends/Liga_Latam/Season_2/Statistics"},
    {"year": 2022, "title": "MPL Singapore Season 4", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_4/Statistics"},
    {"year": 2022, "title": "MPL MENA Fall 2022", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/2022/Fall/Statistics"},
    {"year": 2022, "title": "MPL Malaysia Season 10", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_10/Statistics"},
    {"year": 2022, "title": "MPL Philippines Season 10", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_10/Statistics"},
    {"year": 2022, "title": "MPL Indonesia Season 10", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_10/Statistics"},
    {"year": 2022, "title": "ONE Esports MPL Invitational 2022", "url": "https://liquipedia.net/mobilelegends/ONE_Esports_MPL_Invitational/2022/Statistics"},

    # ===== 2023 =====
    {"year": 2023, "title": "MPL Indonesia Season 11", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_11/Statistics"},
    {"year": 2023, "title": "MPL Singapore Season 5", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_5/Statistics"},
    {"year": 2023, "title": "MPL Malaysia Season 11", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_11/Statistics"},
    {"year": 2023, "title": "MPL Philippines Season 11", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_11/Statistics"},
    {"year": 2023, "title": "MPL MENA Spring 2023", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/2023/Spring/Statistics"},
    {"year": 2023, "title": "ESL Snapdragon Pro Series SEA 3", "url": "https://liquipedia.net/mobilelegends/ESL/Snapdragon_Pro_Series/Season_3/SEA/Challenge_Finals/Statistics"},
    {"year": 2023, "title": "Liga Latam 2023", "url": "https://liquipedia.net/mobilelegends/Liga_Latam/2023/Statistics"},
    {"year": 2023, "title": "NACT Fall 2023", "url": "https://liquipedia.net/mobilelegends/NACT/2023/Fall/Statistics"},
    {"year": 2023, "title": "MLBB Continental Championship Season 2", "url": "https://liquipedia.net/mobilelegends/MLBB_Continental_Championships/Season_2/Statistics"},
    {"year": 2023, "title": "MPL Cambodia Autumn 2023", "url": "https://liquipedia.net/mobilelegends/MPL/Cambodia/2023/Autumn/Statistics"},
    {"year": 2023, "title": "MPL Malaysia Season 12", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_12/Statistics"},
    {"year": 2023, "title": "MTC Turkiye Season 2", "url": "https://liquipedia.net/mobilelegends/MTC_Turkiye_Championship/Season_2/Statistics"},
    {"year": 2023, "title": "MPL Indonesia Season 12", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_12/Statistics"},
    {"year": 2023, "title": "MPL MENA Fall 2023", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/2023/Fall/Statistics"},
    {"year": 2023, "title": "MPL Singapore Season 6", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_6/Statistics"},
    {"year": 2023, "title": "MPL Philippines Season 12", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_12/Statistics"},
    {"year": 2023, "title": "ONE Esports MPL Invitational 2023", "url": "https://liquipedia.net/mobilelegends/ONE_Esports_MPL_Invitational/2023/Statistics"},

    # ===== 2024 =====
    {"year": 2024, "title": "Games of the Future 2024", "url": "https://liquipedia.net/mobilelegends/Games_of_the_Future/2024/Statistics"},
    {"year": 2024, "title": "MPL LATAM Season 1", "url": "https://liquipedia.net/mobilelegends/MPL/LATAM/Season_1/Statistics"},
    {"year": 2024, "title": "NACT Spring 2024", "url": "https://liquipedia.net/mobilelegends/NACT/2024/Spring/Statistics"},
    {"year": 2024, "title": "MTC Turkiye Season 3", "url": "https://liquipedia.net/mobilelegends/MTC_Turkiye_Championship/Season_3/Statistics"},
    {"year": 2024, "title": "MPL Cambodia Season 6", "url": "https://liquipedia.net/mobilelegends/MPL/Cambodia/Season_6/Statistics"},
    {"year": 2024, "title": "MPL Philippines Season 13", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_13/Statistics"},
    {"year": 2024, "title": "MLBB Continental Championship Season 3", "url": "https://liquipedia.net/mobilelegends/MLBB_Continental_Championships/Season_3/Statistics"},
    {"year": 2024, "title": "MPL Malaysia Season 13", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_13/Statistics"},
    {"year": 2024, "title": "MPL Indonesia Season 13", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_13/Statistics"},
    {"year": 2024, "title": "MPL MENA Season 5", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/Season_5/Statistics"},
    {"year": 2024, "title": "MPL Singapore Season 7", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_7/Statistics"},
    {"year": 2024, "title": "Snapdragon Pro Series APAC 5", "url": "https://liquipedia.net/mobilelegends/ESL/Snapdragon_Pro_Series/Season_5/APAC/Challenge_Finals/Statistics"},
    {"year": 2024, "title": "MPL Singapore Season 8", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_8/Statistics"},
    {"year": 2024, "title": "MPL LATAM Season 2", "url": "https://liquipedia.net/mobilelegends/MPL/LATAM/Season_2/Statistics"},
    {"year": 2024, "title": "MPL MENA Season 6", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/Season_6/Statistics"},
    {"year": 2024, "title": "MTC Turkiye Season 4", "url": "https://liquipedia.net/mobilelegends/MTC_Turkiye_Championship/Season_4/Statistics"},
    {"year": 2024, "title": "MPL Philippines Season 14", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_14/Statistics"},
    {"year": 2024, "title": "MPL Cambodia Season 7", "url": "https://liquipedia.net/mobilelegends/MPL/Cambodia/Season_7/Statistics"},
    {"year": 2024, "title": "NACT Fall 2024", "url": "https://liquipedia.net/mobilelegends/NACT/2024/Fall/Statistics"},
    {"year": 2024, "title": "MLBB Continental Championship Season 4", "url": "https://liquipedia.net/mobilelegends/MLBB_Continental_Championships/Season_4/Statistics"},
    {"year": 2024, "title": "MPL Indonesia Season 14", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_14/Statistics"},
    {"year": 2024, "title": "MPL Malaysia Season 14", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_14/Statistics"},

    # ===== 2025 =====
    {"year": 2025, "title": "Snapdragon Pro Series APAC 6", "url": "https://liquipedia.net/mobilelegends/ESL/Snapdragon_Pro_Series/Season_6/APAC/Challenge_Finals/Statistics"},
    {"year": 2025, "title": "Snapdragon Pro Series Masters 2025", "url": "https://liquipedia.net/mobilelegends/ESL/Snapdragon_Pro_Series/2025/Masters/Statistics"},
    {"year": 2025, "title": "MLBB Super Cup Invitational 2025", "url": "https://liquipedia.net/mobilelegends/MLBB_Super_Cup_Invitational/2025/Statistics"},
    {"year": 2025, "title": "MPL Cambodia Season 8", "url": "https://liquipedia.net/mobilelegends/MPL/Cambodia/Season_8/Statistics"},
    {"year": 2025, "title": "MTC Turkiye Championship Season 5", "url": "https://liquipedia.net/mobilelegends/MTC_Turkiye_Championship/Season_5/Statistics"},
    {"year": 2025, "title": "MPL MENA Season 7", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/Season_7/Statistics"},
    {"year": 2025, "title": "MLBB Continental Championships Season 5", "url": "https://liquipedia.net/mobilelegends/MLBB_Continental_Championships/Season_5/Statistics"},
    {"year": 2025, "title": "MPL Philippines Season 15", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_15/Statistics"},
    {"year": 2025, "title": "MPL Singapore Season 9", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_9/Statistics"},
    {"year": 2025, "title": "MPL LATAM Season 3", "url": "https://liquipedia.net/mobilelegends/MPL/LATAM/Season_3/Statistics"},
    {"year": 2025, "title": "MPL Indonesia Season 15", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_15/Statistics"},
    {"year": 2025, "title": "MPL Malaysia Season 15", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_15/Statistics"},
    {"year": 2025, "title": "MPL MENA Season 8", "url": "https://liquipedia.net/mobilelegends/MPL/MENA/Season_8/Statistics"},
    {"year": 2025, "title": "MTC Turkiye Championship Season 6", "url": "https://liquipedia.net/mobilelegends/MTC_Turkiye_Championship/Season_6/Statistics"},
    {"year": 2025, "title": "MPL Philippines Season 16", "url": "https://liquipedia.net/mobilelegends/MPL/Philippines/Season_16/Statistics"},
    {"year": 2025, "title": "MPL Singapore Season 10", "url": "https://liquipedia.net/mobilelegends/MPL/Singapore/Season_10/Statistics"},
    {"year": 2025, "title": "MPL Indonesia Season 16", "url": "https://liquipedia.net/mobilelegends/MPL/Indonesia/Season_16/Statistics"},
    {"year": 2025, "title": "MPL LATAM Season 4", "url": "https://liquipedia.net/mobilelegends/MPL/LATAM/Season_4/Statistics"},
    {"year": 2025, "title": "MLBB Continental Championships Season 6", "url": "https://liquipedia.net/mobilelegends/MLBB_Continental_Championships/Season_6/Statistics"},
    {"year": 2025, "title": "MLBB Super League Season 2", "url": "https://liquipedia.net/mobilelegends/MLBB_Super_League/Season_2/Statistics"},
    {"year": 2025, "title": "MLBB China Masters 2025", "url": "https://liquipedia.net/mobilelegends/MLBB_China_Masters/2025/Statistics"},
    {"year": 2025, "title": "MPL Malaysia Season 16", "url": "https://liquipedia.net/mobilelegends/MPL/Malaysia/Season_16/Statistics"},
    {"year": 2025, "title": "MPL Cambodia Season 9", "url": "https://liquipedia.net/mobilelegends/MPL/Cambodia/Season_9/Statistics"},
    {"year": 2025, "title": "Games of the Future 2025", "url": "https://liquipedia.net/mobilelegends/Games_of_the_Future/2025/Statistics"},
]

# ---------------------------
# Safe request with retries and proxy
# ---------------------------
def safe_get(url: str, timeout=REQUEST_TIMEOUT, retries=RETRIES) -> requests.Response:
    """Fetch URL with retry logic and rotating proxy"""
    delay = 1.0
    for attempt in range(1, retries + 1):
        proxy = get_next_proxy()
        try:
            r = requests.get(
                url,
                headers=HEADERS,
                cookies=COOKIES,
                proxies=proxy,
                timeout=timeout
            )
            if r.status_code == 200:
                return r
        except requests.RequestException as e:
            if attempt == retries:
                print(f"    ✗ Failed after {retries} attempts: {str(e)[:50]}")
        time.sleep(delay)
        delay *= RETRY_BACKOFF
    return None

# ---------------------------
# Worker: fetch + parse tournament
# ---------------------------
def process_tournament(tournament: Dict) -> tuple:
    """Process single tournament and return (rows, debug_info)"""
    url = tournament["url"]
    title = tournament["title"]
    
    print(f"\n[DEBUG] Processing: {title}")
    print(f"        URL: {url}")
    
    response = safe_get(url)
    if not response:
        print(f"    ✗ No response received")
        return [], {"title": title, "heroes": [], "error": "No response"}

    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table")
    
    if not tables:
        print(f"    ✗ No tables found")
        return [], {"title": title, "heroes": [], "error": "No tables"}

    all_rows = []
    heroes_found = set()
    
    for table in tables:
        try:
            hero_rows = parse_stats_table(table, tournament)
            if hero_rows:
                all_rows.extend(hero_rows)
                for row in hero_rows:
                    heroes_found.add(row["hero"])
        except Exception as e:
            print(f"    ⚠ Error parsing table: {str(e)[:50]}")
            continue

    heroes_list = sorted(list(heroes_found))
    
    if heroes_list:
        print(f"    ✓ Found {len(heroes_list)} heroes: {', '.join(heroes_list[:10])}")
        if len(heroes_list) > 10:
            print(f"      ... and {len(heroes_list) - 10} more")
    else:
        print(f"    ✗ No heroes found")
    
    debug_info = {
        "title": title,
        "heroes": heroes_list,
        "count": len(heroes_list),
        "error": None if heroes_list else "No heroes parsed"
    }
    
    return all_rows, debug_info

# ---------------------------
# Main runner
# ---------------------------
def main(tournaments_list: List[Dict], max_workers=MAX_WORKERS):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"MLBB Tournament Scraper")
    print(f"{'='*70}")
    print(f"Tournaments to scrape: {len(tournaments_list)}")
    print(f"Thread workers: {max_workers}")
    print(f"Proxies: {', '.join(PROXIES_LIST)}")
    print(f"{'='*70}\n")
    
    # Prepare master CSV
    master_fields = ["hero", "pick_total", "pick_wins", "pick_losses", "ban_count", 
                     "win_rate", "tournament_year", "tournament_title", "tournament_url"]
    master_file = open(MASTER_CSV, "w", newline="", encoding="utf-8")
    master_writer = csv.DictWriter(master_file, fieldnames=master_fields)
    master_writer.writeheader()

    summary = {
        "total_tournaments": 0,
        "total_rows": 0,
        "successful": [],
        "failed": []
    }

    print(f"{'='*70}")
    print(f"SCRAPING PROGRESS")
    print(f"{'='*70}\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_t = {executor.submit(process_tournament, t): t for t in tournaments_list}
        
        for future in as_completed(future_to_t):
            t = future_to_t[future]
            summary["total_tournaments"] += 1
            
            try:
                rows, debug_info = future.result()
            except Exception as e:
                rows = []
                debug_info = {"title": t["title"], "heroes": [], "error": str(e)}
                print(f"\n[ERROR] Exception in {t['title']}: {str(e)[:100]}")

            # Save debug info
            if debug_info.get("error"):
                summary["failed"].append(debug_info)
            else:
                summary["successful"].append(debug_info)

            # Write per-tournament CSV
            pername = re.sub(r"[^\w\-]+", "_", t["title"]).strip("_")[:120]
            perpath = os.path.join(OUTPUT_DIR, f"{pername}.csv")
            
            with open(perpath, "w", newline="", encoding="utf-8") as pf:
                w = csv.DictWriter(pf, fieldnames=master_fields)
                w.writeheader()
                
                for r in rows:
                    rec = {k: r.get(k, 0) for k in master_fields}
                    w.writerow(rec)
                    master_writer.writerow(rec)
                    summary["total_rows"] += 1

            # Show current progress
            success_count = len(summary["successful"])
            fail_count = len(summary["failed"])
            progress_pct = (summary["total_tournaments"] / len(tournaments_list)) * 100
            
            print(f"\n{'─'*70}")
            print(f"Progress: {summary['total_tournaments']}/{len(tournaments_list)} ({progress_pct:.1f}%)")
            print(f"Success: {success_count} | Failed: {fail_count} | Total Rows: {summary['total_rows']}")
            print(f"{'─'*70}")

    master_file.close()

    # Final summary
    print(f"\n\n{'='*70}")
    print(f"FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"Total tournaments processed: {summary['total_tournaments']}")
    print(f"Successful: {len(summary['successful'])}")
    print(f"Failed: {len(summary['failed'])}")
    print(f"Total hero-stat rows written: {summary['total_rows']}")
    print(f"Master CSV: {MASTER_CSV}")
    print(f"Per-tournament CSVs: ./{OUTPUT_DIR}/")
    
    if summary["failed"]:
        print(f"\n{'='*70}")
        print(f"FAILED TOURNAMENTS ({len(summary['failed'])})")
        print(f"{'='*70}")
        for fail in summary["failed"]:
            print(f"  ✗ {fail['title']}")
            print(f"    Error: {fail.get('error', 'Unknown')}")
    
    if summary["successful"]:
        print(f"\n{'='*70}")
        print(f"SUCCESSFUL TOURNAMENTS - HERO COUNTS")
        print(f"{'='*70}")
        for success in summary["successful"][:20]:  # Show first 20
            print(f"  ✓ {success['title']}: {success['count']} heroes")
        if len(summary["successful"]) > 20:
            print(f"  ... and {len(summary['successful']) - 20} more")
    
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    start = time.time()
    main(tournaments, max_workers=MAX_WORKERS)
    elapsed = time.time() - start
    print(f"Finished in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"{'='*70}\n")