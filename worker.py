# russia_thinktank_bot.py
import json
import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import schedule
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ================== НАСТРОЙКИ ==================
# 🔑 Токен берется из переменной окружения (для Render.com)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("❌ Ошибка: переменная окружения TELEGRAM_TOKEN не установлена")

CHANNEL_ID = os.getenv('CHANNEL_ID', "@time_n_John")  # Можно также задать через переменную окружения

# 🔌 Прокси (можно задать через переменные окружения)
PROXY_TYPE = os.getenv('PROXY_TYPE', '')  # socks5, http
PROXY_HOST = os.getenv('PROXY_HOST', '')
PROXY_PORT = os.getenv('PROXY_PORT', '')
PROXY_USER = os.getenv('PROXY_USER', '')
PROXY_PASS = os.getenv('PROXY_PASS', '')

PROXY = {}
if PROXY_TYPE and PROXY_HOST and PROXY_PORT:
    proxy_url = f"{PROXY_TYPE}://"
    if PROXY_USER and PROXY_PASS:
        proxy_url += f"{PROXY_USER}:{PROXY_PASS}@"
    proxy_url += f"{PROXY_HOST}:{PROXY_PORT}"
    PROXY = {
        "http": proxy_url,
        "https": proxy_url
    }

# ================== ВСЕ ИСТОЧНИКИ (КАНАЛЫ) ==================
SOURCES = [
    # Основные международные аналитические центры
    {"name": "BBC News Russia", "url": "https://feeds.bbci.co.uk/news/world/europe/rss.xml"},
    {"name": "Foreign Affairs", "url": "https://www.foreignaffairs.com/rss.xml"},
    {"name": "CSIS", "url": "https://www.csis.org/rss.xml"},
    {"name": "Atlantic Council", "url": "https://www.atlanticcouncil.org/feed/"},
    {"name": "RAND Corporation", "url": "https://www.rand.org/rss.xml"},
    {"name": "Carnegie Endowment", "url": "https://carnegieendowment.org/rss/rss.xml"},
    {"name": "Council on Foreign Relations", "url": "https://www.cfr.org/rss.xml"},
    {"name": "Chatham House", "url": "https://www.chathamhouse.org/rss"},
    {"name": "Brookings Institution", "url": "https://www.brookings.edu/feed/"},
    {"name": "The Diplomat", "url": "https://thediplomat.com/feed/"},
    
    # Новостные агентства с фокусом на Россию/Европу
    {"name": "Reuters: Russia", "url": "https://www.reuters.com/world/europe/rss.xml"},
    {"name": "Reuters: Ukraine", "url": "https://www.reuters.com/world/europe/ukraine/rss.xml"},
    {"name": "Al Jazeera: Russia", "url": "https://www.aljazeera.com/tag/russia/rss.xml"},
    {"name": "Al Jazeera: Ukraine", "url": "https://www.aljazeera.com/tag/ukraine/rss.xml"},
    {"name": "DW News: Russia", "url": "https://rss.dw.com/xml/rss-ru-russia"},
    {"name": "DW News: Eastern Europe", "url": "https://rss.dw.com/xml/rss-en-eastern-europe"},
    {"name": "The Moscow Times", "url": "https://www.themoscowtimes.com/rss/news"},
    {"name": "Kyiv Independent", "url": "https://kyivindependent.com/feed/"},
    
    # Экономические и энергетические источники
    {"name": "Bloomberg: Russia", "url": "https://www.bloomberg.com/feed/tag/russia"},
    {"name": "Financial Times: Russia", "url": "https://www.ft.com/world/europe/russia?format=rss"},
    {"name": "OilPrice.com", "url": "https://oilprice.com/rss/main"},
    
    # Военная аналитика
    {"name": "Institute for the Study of War", "url": "https://www.understandingwar.org/feed"},
    {"name": "RUSI", "url": "https://rusi.org/rss-feed"},
    
    # Другие важные источники
    {"name": "Politico Europe", "url": "https://www.politico.eu/feed/"},
    {"name": "Eurasia Group", "url": "https://www.eurasiagroup.net/feed"},
    {"name": "World Economic Forum", "url": "https://www.weforum.org/rss"},
    {"name": "RFE/RL", "url": "https://www.rferl.org/api/feeds/rss/list/175"},
    {"name": "The Economist: Russia", "url": "https://www.economist.com/sections/europe-102.xml"}
]

# ================== ВСЕ ФИЛЬТРЫ (КЛЮЧЕВЫЕ СЛОВА) ==================
KEYWORDS = [
    # Россия и связанные термины
    r"\brussia\b", r"\brussian\b", r"\brussians\b", r"\brus\b", r"\brusso\b", r"\brusophobia\b",
    r"\bputin\b", r"\bmoscow\b", r"\bkremlin\b", r"\bsiberia\b", r"\bru\b", r"\brus\b",
    r"\bkaliningrad\b", r"\bsevastopol\b", r"\bvolgograd\b", r"\byekaterinburg\b",
    
    # Украина и связанные термины
    r"\bukraine\b", r"\bukrainian\b", r"\bukrainians\b", r"\bkiev\b", r"\bkyiv\b", r"\bkharkiv\b",
    r"\bkherson\b", r"\bodesa\b", r"\bodessa\b", r"\bdnipro\b", r"\bzelensky\b", r"\bzelenskyy\b",
    r"\bzelenksiy\b", r"\bbucha\b", r"\birpin\b", r"\bcrimea\b", r"\bkrasnodar\b", r"\bdonbas\b",
    r"\bmaidan\b", r"\bsamara\b", r"\bdonetsk\b", r"\bluhansk\b", r"\bmariupol\b", r"\bbakhmut\b",
    
    # Санкции и экономика
    r"\bsanction[s]?\b", r"\bembargo\b", r"\brestrictions?\b", r"\bblacklist\b", r"\bfrozen assets\b",
    r"\bgazprom\b", r"\bnovatek\b", r"\brosgaz\b", r"\bnord\s?stream\b", r"\bturkstream\b",
    r"\boil\s?price\b", r"\bgas\s?price\b", r"\bruble\b", r"\brubel\b", r"\brub\b", r"\bcbr\b",
    r"\binflation\b", r"\breserve[s]?\b", r"\bswift\b", r"\bmir\b", r"\bspfs\b", r"\bimport\s?ban\b",
    r"\beurozone\b", r"\bg7\b", r"\bimf\b", r"\bworld bank\b", r"\bcentral\s?bank\b",
    
    # Военные термины и персоналии
    r"\bwagner\b", r"\bprigozhin\b", r"\bshoigu\b", r"\bgrushko\b", r"\bvostok\b", r"\bzenit\b",
    r"\bkalibr\b", r"\byars\b", r"\bavangard\b", r"\bsarmat\b", r"\bizhev\b", r"\bseverodvinsk\b",
    r"\bmilitary\s?exercis\b", r"\bnuclear\b", r"\bstrategic\s?forces\b", r"\bssbn\b", r"\bssbn\b",
    r"\btank\b", r"\btanks\b", r"\bdrone[s]?\b", r"\buav[s]?\b", r"\bmissile[s]?\b", r"\bmig\b",
    r"\bsu\b", r"\baircraft [^s]", r"\bnato\b", r"\bwto\b", r"\bsea\b", r"\bnavy\b", r"\bblack\s?sea\b",
    r"\barctic\b", r"\bmedvedev\b", r"\bpeskov\b", r"\blavrov\b", r"\bpatrushev\b", r"\bnaryshkin\b",
    
    # Дипломатия и переговоры
    r"\bdiplomat[sic]?\b", r"\btalks\b", r"\bnegotiat\b", r"\bmeeting[s]?\b", r"\bsummit[s]?\b",
    r"\bambassador\b", r"\bconsul\b", r"\bminister\b", r"\bforeign\s?minister\b", r"\bpeace\b",
    r"\btruce\b", r"\bceasefire\b", r"\bgrain\s?deal\b", r"\bgrain\s?corridor\b", r"\bgrain\s?initiative\b",
    
    # Интеграция и союзы
    r"\beaeu\b", r"\beurasia[n]?\b", r"\bbrics\b", r"\bbrics\+\b", r"\bshanghai\s?cooperation\b",
    r"\bcollective\s?security\b", r"\bcsto\b", r"\beuroasia\b", r"\bbelt\s?and\s?road\b",
    
    # Связанные страны и регионы
    r"\bbelarus\b", r"\bmoldova\b", r"\bgeorgia\b", r"\bazerbaijan\b", r"\barmenia\b",
    r"\bkazakhstan\b", r"\buzbekistan\b", r"\bkyrgyzstan\b", r"\bturkmenistan\b", r"\btajikistan\b",
    r"\bbaltic\b", r"\bestonia\b", r"\blatvia\b", r"\blithuania\b", r"\bfinland\b", r"\bsweden\b",
    r"\bpoland\b", r"\bromania\b", r"\bmoldova\b", r"\bcaucasus\b", r"\btransnistria\b", r"\bnagorno\b",
    
    # Специальные операции и события
    r"\bspecial\s?operation\b", r"\bopt\s?\d+\b", r"\bmobilization\b", r"\bpartial\s?mobilization\b",
    r"\breferendum\b", r"\bannexation\b", r"\boccupation\b", r"\bterritorial\s?integrity\b",
    
    # Геополитические термины
    r"\bgeopoliti[cs]\b", r"\bsecurity\s?council\b", r"\bunited\s?nations\b", r"\bunesco\b", r"\bi\w{2}o\b",
    r"\bsecurity\s?guarantee[s]?\b", r"\bcollective\s?west\b", r"\beast\s?west\b", r"\bdivide\b",
    r"\bsubversive\b", r"\bhybrid\s?war\b", r"\bdisinformation\b", r"\bpropaganda\b"
]

SEEN_FILE = "seen_links.json"
MAX_SEEN = 5000
MAX_PER_RUN = 7
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 15))  # Интервал проверки в минутах

# ================== ЛОГИРОВАНИЕ ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ================== ЗАГОЛОВКИ И СЕССИЯ ==================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Accept': 'application/rss+xml, application/xml;q=0.9, */*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)

    # Подключаем прокси, если указан
    if PROXY:
        session.proxies.update(PROXY)
        log.info(f"Используется прокси: {PROXY.get('https') or PROXY.get('http')}")
    return session

# ================== УТИЛИТЫ ==================
def load_seen_links() -> set:
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data[-MAX_SEEN:])
        except Exception as e:
            log.error(f"Ошибка чтения seen_links.json: {e}")
    return set()

def save_seen_link(link: str, seen: set):
    seen.add(link)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen)[-MAX_SEEN:], f)

def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        # Используем тот же прокси, что и для RSS
        proxies = PROXY if PROXY else None
        r = requests.post(url, data=payload, proxies=proxies, timeout=15)
        r.raise_for_status()
        log.info("Сообщение отправлено в Telegram")
    except Exception as e:
        log.error(f"Ошибка отправки в Telegram: {e}")

def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

def translate_to_russian(text: str) -> str:
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as e:
        log.warning(f"Перевод не удался: {e}")
        return text

def get_summary(title: str) -> str:
    low = title.lower()
    if re.search(r"sanction|ban|restrict|embargo|blacklist", low):
        return "📊 Введены новые санкции или ограничения."
    if re.search(r"attack|strike|bomb|war|invasion|conflict|battle|offensive", low):
        return "⚔️ Сообщается о военных действиях или ударах."
    if re.search(r"putin|kremlin|moscow|kreml|government", low):
        return "🏛️ Заявление или действие со стороны Кремля."
    if re.search(r"economy|rub[lb]e|oil|gas|gazprom|nord\s?stream|inflation|cb|reserve", low):
        return "💸 Новости экономики, нефти, газа или рубля."
    if re.search(r"diplomat|talks|negotiat|meeting|summit|lavrov|peskov|ambassador", low):
        return "🤝 Дипломатические переговоры или контакты."
    if re.search(r"wagner|prigozhin|shoigu|medvedev|patrushev|naryshkin", low):
        return "👔 События с российскими военными или политиками."
    if re.search(r"nuclear|missile|strategic|hypersonic|avangard|sarmat", low):
        return "☢️ События, связанные с ядерным оружием или ракетами."
    if re.search(r"ukraine|ukrainian|kyiv|kiev|zelensky|donbas|crimea", low):
        return "🇺🇦 Новости, связанные с Украиной."
    if re.search(r"brics|eaeu|shos|csto|eurasian|asia", low):
        return "🌐 Развитие евразийской интеграции или BRICS."
    return "📰 Важное событие, связанное с Россией."

# ================== ПАРСИНГ RSS ==================
def fetch_rss_news() -> list:
    seen = load_seen_links()
    result = []
    session = create_session()

    for src in SOURCES:
        if len(result) >= MAX_PER_RUN:
            break
        try:
            log.info(f"Парсинг: {src['name']}")
            resp = session.get(src["url"].strip(), timeout=30)
            
            if resp.status_code != 200:
                log.warning(f"{src['name']}: HTTP {resp.status_code}, пропускаем")
                continue

            # Проверка: действительно ли это XML?
            content = resp.text.strip()
            if not (content.startswith('<?xml') or '<rss' in content[:200] or '<feed' in content[:200]):
                log.warning(f"{src['name']}: Получен не XML-контент. Пропускаем.")
                continue

            soup = BeautifulSoup(resp.content, "xml")
            for item in soup.find_all("item"):
                if len(result) >= MAX_PER_RUN:
                    break

                title_tag = item.find("title")
                link_tag = item.find("link") or item.find("guid")
                if not title_tag or not link_tag:
                    continue

                title = clean_text(title_tag.get_text())
                link = clean_text(link_tag.get_text() if hasattr(link_tag, 'get_text') else link_tag.text)
                if not title or not link:
                    continue

                if not any(re.search(kw, title, re.IGNORECASE) for kw in KEYWORDS):
                    continue

                if link in seen:
                    continue

                ru_title = translate_to_russian(title)
                summary = get_summary(title)
                msg = f"*📰 {ru_title}*\n\n{summary}\n\n[Источник]({link})"
                if len(msg) > 4000:  # Ограничение Telegram
                    msg = msg[:3997] + "..."
                result.append({"msg": msg, "link": link})

        except Exception as e:
            log.error(f"Ошибка при парсинге {src['name']}: {e}")

    return result

# ================== ОСНОВНОЙ ЦИКЛ ==================
def job():
    log.info("Запуск проверки новостей...")
    news = fetch_rss_news()
    if not news:
        log.info("Новостей не найдено.")
        return

    seen = load_seen_links()
    for item in news:
        send_to_telegram(item["msg"])
        save_seen_link(item["link"], seen)
        time.sleep(1.5)

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    log.info(f"Бот запущен. Проверка каждые {CHECK_INTERVAL} минут.")
    
    job()  # ✅ Первая проверка сразу после запуска
    
    schedule.every(CHECK_INTERVAL).minutes.do(job)  # ✅ Проверка согласно настройкам

    while True:
        schedule.run_pending()
        time.sleep(1)
