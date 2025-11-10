import os
import time
import re
import feedparser
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from telegram import Bot
from datetime import datetime
from dateutil import parser as date_parser

# --- Настройки ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNELS = ["@finanosint", "@time_n_John"]

# --- Инициализация ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=TELEGRAM_TOKEN)

# --- Фильтры ---
FILTERS = {
    "SVO": [
        r"\bsvo\b", r"\bспецоперация\b", r"\bspecial military operation\b",
        r"\bвойна\b", r"\bwar\b", r"\bconflict\b", r"\bконфликт\b",
        r"\bнаступление\b", r"\boffensive\b", r"\bатака\b", r"\battack\b",
        r"\bудар\b", r"\bstrike\b", r"\bобстрел\b", r"\bshelling\b",
        r"\bдрон\b", r"\bdrone\b", r"\bmissile\b", r"\bракета\b",
        r"\bэскалация\b", r"\bescalation\b", r"\bмобилизация\b", r"\bmobilization\b",
        r"\bфронт\b", r"\bfrontline\b", r"\bзахват\b", r"\bcapture\b",
        r"\bосвобождение\b", r"\bliberation\b", r"\bбой\b", r"\bbattle\b",
        r"\bпотери\b", r"\bcasualties\b", r"\bпогиб\b", r"\bkilled\b",
        r"\bранен\b", r"\binjured\b", r"\bпленный\b", r"\bprisoner of war\b",
        r"\bпереговоры\b", r"\btalks\b", r"\bперемирие\b", r"\bceasefire\b",
        r"\bсанкции\b", r"\bsanctions\b", r"\bоружие\b", r"\bweapons\b",
        r"\bпоставки\b", r"\bsupplies\b", r"\bhimars\b", r"\batacms\b",
        r"\bhour ago\b", r"\bчас назад\b", r"\bminutos atrás\b", r"\b小时前\b"
    ],
    "Crypto": [
        r"\bbitcoin\b", r"\bbtc\b", r"\bбиткоин\b", r"\b比特币\b",
        r"\bethereum\b", r"\beth\b", r"\bэфир\b", r"\b以太坊\b",
        r"\bbinance coin\b", r"\bbnb\b", r"\busdt\b", r"\btether\b",
        r"\bxrp\b", r"\bripple\b", r"\bcardano\b", r"\bada\b",
        r"\bsolana\b", r"\bsol\b", r"\bdoge\b", r"\bdogecoin\b",
        r"\bavalanche\b", r"\bavax\b", r"\bpolkadot\b", r"\bdot\b",
        r"\bchainlink\b", r"\blink\b", r"\btron\b", r"\btrx\b",
        r"\bcbdc\b", r"\bcentral bank digital currency\b", r"\bцифровой рубль\b",
        r"\bdigital yuan\b", r"\beuro digital\b", r"\bdefi\b", r"\bдецентрализованные финансы\b",
        r"\bnft\b", r"\bnon-fungible token\b", r"\bsec\b", r"\bцб рф\b",
        r"\bрегуляция\b", r"\bregulation\b", r"\bзапрет\b", r"\bban\b",
        r"\bмайнинг\b", r"\bmining\b", r"\bhalving\b", r"\bхалвинг\b",
        r"\bволатильность\b", r"\bvolatility\b", r"\bcrash\b", r"\bкрах\b",
        r"\bhour ago\b", r"\bчас назад\b", r"\b刚刚\b", r"\bدقائق مضت\b"
    ],
    "Pandemic": [
        r"\bpandemic\b", r"\bпандемия\b", r"\b疫情\b", r"\bجائحة\b",
        r"\boutbreak\b", r"\bвспышка\b", r"\bэпидемия\b", r"\bepidemic\b",
        r"\bvirus\b", r"\bвирус\b", r"\bвирусы\b", r"\b变异株\b",
        r"\bvaccine\b", r"\bвакцина\b", r"\b疫苗\b", r"\bلقاح\b",
        r"\bbooster\b", r"\bбустер\b", r"\bревакцинация\b",
        r"\bquarantine\b", r"\bкарантин\b", r"\b隔离\b", r"\bحجر صحي\b",
        r"\blockdown\b", r"\bлокдаун\b", r"\b封锁\b",
        r"\bmutation\b", r"\bмутация\b", r"\b变异\b",
        r"\bstrain\b", r"\bштамм\b", r"\bomicron\b", r"\bdelta\b",
        r"\bbiosafety\b", r"\bбиобезопасность\b", r"\b生物安全\b",
        r"\blab leak\b", r"\bлабораторная утечка\b", r"\b实验室泄漏\b",
        r"\bgain of function\b", r"\bусиление функции\b",
        r"\bwho\b", r"\bвоз\b", r"\bcdc\b", r"\bроспотребнадзор\b",
        r"\binfection rate\b", r"\bзаразность\b", r"\b死亡率\b",
        r"\bhospitalization\b", r"\bгоспитализация\b",
        r"\bhour ago\b", r"\bчас назад\b", r"\bقبل ساعات\b", r"\b刚刚报告\b"
    ]
}

COMPILED_FILTERS = {
    cat: [re.compile(p, re.IGNORECASE) for p in patterns]
    for cat, patterns in FILTERS.items()
}

# --- Источники ---
SOURCES = [
    {"name": "The Economist", "rss": "https://www.economist.com/rss/latest/rss.xml"},
    {"name": "Bloomberg", "rss": "https://feeds.bloomberg.com/markets/news.rss"},
    {"name": "RAND Corporation", "rss": "https://www.rand.org/rss.xml"},
    {"name": "CSIS", "rss": "https://www.csis.org/rss.xml"},
    {"name": "Atlantic Council", "rss": "https://www.atlanticcouncil.org/feed/"},
    {"name": "Chatham House", "rss": "https://www.chathamhouse.org/feed"},
    {"name": "Foreign Affairs", "rss": "https://www.foreignaffairs.com/rss.xml"},
    {"name": "CFR", "rss": "https://www.cfr.org/rss.xml"},
    {"name": "BBC Future", "rss": "https://www.bbc.com/future/rss"},
    {"name": "Future Timeline", "rss": "https://futuretimeline.net/blog.rss"},
    {"name": "Carnegie Endowment", "rss": "https://carnegieendowment.org/feed"},
    {"name": "Bruegel", "rss": "https://bruegel.org/feed/"},
    {"name": "E3G", "rss": "https://e3g.org/feed/"},
    {"name": "Good Judgment", "custom_parser": lambda: scrape_good_judgment()},
    {"name": "Metaculus", "custom_parser": lambda: scrape_metaculus()},
    {"name": "DNI Global Trends", "custom_parser": lambda: scrape_odni()},
]

# --- Парсеры ---
def scrape_good_judgment():
    url = "https://goodjudgment.com/blog"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        posts = soup.find_all('article', class_='post') or soup.find_all('div', class_='blog-post')
        for post in posts:
            title_tag = post.find('h2') or post.find('h3')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link_tag = title_tag.find('a')
            if not link_tag:
                continue
            link = link_tag.get('href')
            if not link.startswith('http'):
                link = "https://goodjudgment.com" + link
            summary_tag = post.find('p')
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            pub_date = datetime.now().isoformat()

            if article_exists(link):
                continue
            category = classify_article(title, summary)
            if category:
                save_article(title, link, summary, pub_date, "Good Judgment", category)
                send_to_telegram(title, link, "Good Judgment", category)
    except Exception as e:
        print(f"❌ Ошибка парсинга Good Judgment: {e}")

def scrape_metaculus():
    url = "https://www.metaculus.com/questions/"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.find_all('div', class_='question-card') or soup.find_all('div', class_='question-list-item')
        for item in items:
            title_tag = item.find('a', class_='title-link') or item.find('h3').find('a')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = "https://www.metaculus.com" + title_tag.get('href')
            summary_tag = item.find('div', class_='blurb') or item.find('p')
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            pub_date = datetime.now().isoformat()

            if article_exists(link):
                continue
            category = classify_article(title, summary)
            if category:
                save_article(title, link, summary, pub_date, "Metaculus", category)
                send_to_telegram(title, link, "Metaculus", category)
    except Exception as e:
        print(f"❌ Ошибка парсинга Metaculus: {e}")

def scrape_odni():
    url = "https://www.dni.gov/index.php/gt2040-home"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.find_all('div', class_='article') or soup.find_all('div', class_='press-release')
        for article in articles:
            title_tag = article.find('h3') or article.find('h2')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link_tag = title_tag.find('a')
            if link_tag:
                link = link_tag.get('href')
                if not link.startswith('http'):
                    link = "https://www.dni.gov" + link
            else:
                link = url
            summary_tag = article.find('p')
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            pub_date = datetime.now().isoformat()

            if article_exists(link):
                continue
            category = classify_article(title, summary)
            if category:
                save_article(title, link, summary, pub_date, "DNI Global Trends", category)
                send_to_telegram(title, link, "DNI Global Trends", category)
    except Exception as e:
        print(f"❌ Ошибка парсинга DNI: {e}")

# --- Функции ---
def contains_keywords(text, category):
    if not text:
        return False
    return any(pattern.search(text) for pattern in COMPILED_FILTERS[category])

def classify_article(title, summary):
    text = f"{title} {summary}".lower()
    for category in ["SVO", "Crypto", "Pandemic"]:
        if contains_keywords(text, category):
            return category
    return None

def is_recent(entry, max_hours=2):
    try:
        pub = date_parser.parse(entry.published)
        now = datetime.now(pub.tzinfo)
        diff_hours = (now - pub).total_seconds() / 3600
        return diff_hours < max_hours
    except:
        return True

def article_exists(url):
    response = supabase.table("news_articles").select("id").eq("url", url).execute()
    return len(response.data) > 0

def save_article(title, url, description, pub_date, source, category):
    supabase.table("news_articles").insert({
        "title": title,
        "url": url,
        "description": description or "",
        "pub_date": pub_date,
        "source_name": source,
        "category": category
    }).execute()

def send_to_telegram(title, url, source, category):
    message = (
        f"[{category}] {title}\n"
        f"Источник: <a href='{url}'>{source}</a>"
    )
    for channel in CHANNELS:
        try:
            bot.send_message(chat_id=channel, text=message, parse_mode="HTML", disable_web_page_preview=False)
            print(f"✅ Отправлено в {channel}: {title}")
        except Exception as e:
            print(f"❌ Ошибка отправки в {channel}: {e}")

# --- Основной цикл ---
def fetch_from_rss(source):
    try:
        feed = feedparser.parse(source["rss"])
        if feed.bozo:
            print(f"⚠️ Ошибка парсинга RSS {source['name']}: {feed.bozo_exception}")
            return
        for entry in feed.entries:
            url = entry.link
            title = entry.title.strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            pub_date = entry.get("published", datetime.now().isoformat())

            if not url or not title:
                continue

            if not is_recent(entry, max_hours=2):
                continue

            if article_exists(url):
                continue

            category = classify_article(title, summary)
            if category:
                save_article(title, url, summary, pub_date, source["name"], category)
                send_to_telegram(title, url, source["name"], category)

    except Exception as e:
        print(f"❌ Ошибка обработки {source['name']}: {e}")

def fetch_and_process():
    for source in SOURCES:
        if "custom_parser" in source:
            source["custom_parser"]()
        else:
            fetch_from_rss(source)

if __name__ == "__main__":
    print("🚀 Background Worker запущен. Ожидание 14 минут между проверками...")
    while True:
        print(f"\n🕒 Проверка источников: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        fetch_and_process()
        print(f"⏳ Следующая проверка через 14 минут...")
        time.sleep(14 * 60)
