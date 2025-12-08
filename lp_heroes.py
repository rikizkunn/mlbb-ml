import requests
from bs4 import BeautifulSoup
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------
# COOKIES & HEADERS
# ---------------------------------
cookies = {
    '_pk_id.1.4442': '49e248808a9df0bd.1764516360.',
    'AMP_MKTG_e0b3a97842': 'JTdCJTdE',
    '_pk_ses.1.4442': '1',
    '_gid': 'GA1.2.1907129899.1765175641',
    'CI': '466613080',
    '_ga_3TE8DNE0DL': 'GS2.1.s1765175640$o3$g1$t1765176873$j1$l0$h0',
    '_ga': 'GA1.1.873935266.1764516355',
    '_ga_98E1TX5TKZ': 'GS2.1.s1765175641$o4$g1$t1765176873$j1$l0$h0',
    'AMP_e0b3a97842': 'JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjI4OTkwMTE2NC1lNGQzLTQ3M2YtYjgwMy02ZDc2NDA4OTAwNDUlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzY1MTc1NjQyMDExJTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc2NTE3Njg3NDA1OCUyQyUyMmxhc3RFdmVudElkJTIyJTNBMjM3JTJDJTIycGFnZUNvdW50ZXIlMjIlM0EyMSU3RA==',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    'accept-language': 'en-US,en;q=0.9,id;q=0.8',
    'user-agent': 'Mozilla/5.0',
}

BASE = "https://liquipedia.net"

# ---------------------------------
# STEP 1 — Fetch hero list
# ---------------------------------
print("Fetching hero list...")
resp = requests.get(f"{BASE}/mobilelegends/Portal:Heroes", headers=headers, cookies=cookies)
soup = BeautifulSoup(resp.text, "html.parser")

all_heroes_header = soup.find("div", string=lambda s: s and "All Heroes" in s)
if not all_heroes_header:
    raise Exception("Cannot find All Heroes grid")

hero_grid = all_heroes_header.find_next("div")

hero_links = []
for a in hero_grid.select("div.sapphire-theme-dark-bg.zoom-container > a"):
    href = a.get("href")
    title = a.get("title")
    if href and title:
        hero_links.append({
            "name": title.strip(),
            "url": BASE + href
        })

print(f"Heroes found: {len(hero_links)}")   # should be 130


# ---------------------------------
# STEP 2 — Parse a hero page
# ---------------------------------
def parse_hero_page(hero):

    url = hero["url"]

    try:
        resp = requests.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract name cleanly (remove [e][h])
        header = soup.find("div", class_="infobox-header")

        if header:
            for btn in header.find_all("span", class_="infobox-buttons"):
                btn.decompose()     # removes [e][h]

            hero_name = header.get_text(strip=True)
        else:
            hero_name = hero["name"]

        role = None
        lane = None

        for desc in soup.find_all("div", class_="infobox-cell-2 infobox-description"):
            label = desc.get_text(strip=True)
            value_div = desc.find_next_sibling("div")

            if not value_div:
                continue
            
            value = value_div.get_text(" ", strip=True)

            if label == "Role:":
                role = value

            if label == "Lane:":
                lane = value

        print("✓", hero_name)
        return {"Name": hero_name, "Role": role, "Lane": lane}

    except Exception as e:
        print("Error:", hero["name"], url, str(e))
        return {"Name": hero["name"], "Role": None, "Lane": None}


# ---------------------------------
# STEP 3 — Multithreaded scraping
# ---------------------------------
dataset = []
MAX_THREADS = 15

print("Scraping hero pages with threads...")

with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(parse_hero_page, hero) for hero in hero_links]
    
    for f in as_completed(futures):
        dataset.append(f.result())


# ---------------------------------
# STEP 4 — Save CSV
# ---------------------------------
with open("mlbb_heroes.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["Name", "Role", "Lane"])
    writer.writeheader()
    writer.writerows(dataset)

print("DONE! Saved: mlbb_heroes.csv")