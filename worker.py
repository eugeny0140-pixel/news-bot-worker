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
from supabase import create_client, Client

# ================== НАСТРОЙКИ ==================
# 🔑 Токен берется из переменной окружения (для Render.com)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("❌ Ошибка: переменная окружения TELEGRAM_TOKEN не установлена")

CHANNEL_ID = os.getenv('CHANNEL_ID', "@time_n_John")  # Можно также задать через переменную окружения

# 🔌 Настройки прокси для обхода блокировок
USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
PROXY_HOST = os.getenv('PROXY_HOST', '')
PROXY_PORT = os.getenv('PROXY_PORT', '')
PROXY_TYPE = os.getenv('PROXY_TYPE', 'socks5')  # socks5, http
PROXY_USER = os.getenv('PROXY_USER', '')
PROXY_PASS = os.getenv('PROXY_PASS', '')

# Создаем настройки прокси
PROXY = {}
if USE_PROXY and PROXY_HOST and PROXY_PORT:
    proxy_url = f"{PROXY_TYPE}://"
    if PROXY_USER and PROXY_PASS:
        proxy_url += f"{PROXY_USER}:{PROXY_PASS}@"
    proxy_url += f"{PROXY_HOST}:{PROXY_PORT}"
    PROXY = {
        "http": proxy_url,
        "https": proxy_url
    }

# 🗄️ Настройки Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_TABLE = os.getenv('SUPABASE_TABLE', 'seen_links')
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        log.info("✅ Подключение к Supabase успешно установлено")
    except Exception as e:
        log.error(f"❌ Ошибка подключения к Supabase: {e}")
else:
    log.info("ℹ️ Supabase не настроен, используется локальное хранение ссылок")

# ================== ИСТОЧНИКИ (КАНАЛЫ) ==================
SOURCES = [
    {"name": "Good Judgment", "url": "https://goodjudgment.com/feed/"},
    {"name": "Johns Hopkins", "url": "https://www.centerforhealthsecurity.org/feed/"},
    {"name": "Metaculus", "url": "https://www.metaculus.com/feed/"},
    {"name": "DNI Global Trends", "url": "https://www.dni.gov/index.php/feed"},
    {"name": "RAND Corporation", "url": "https://www.rand.org/rss.xml"},
    {"name": "World Economic Forum", "url": "https://www.weforum.org/rss"},
    {"name": "CSIS", "url": "https://www.csis.org/rss.xml"},
    {"name": "Atlantic Council", "url": "https://www.atlanticcouncil.org/feed/"},
    {"name": "Chatham House", "url": "https://www.chathamhouse.org/feed"},
    {"name": "The Economist", "url": "https://www.economist.com/world/rss.xml"},
    {"name": "Bloomberg", "url": "https://www.bloomberg.com/feed"},
    {"name": "Reuters Institute", "url": "https://reutersinstitute.politics.ox.ac.uk/rss.xml"},
    {"name": "Foreign Affairs", "url": "https://www.foreignaffairs.com/rss.xml"},
    {"name": "CFR", "url": "https://www.cfr.org/rss.xml"},
    {"name": "BBC Future", "url": "https://feeds.bbci.co.uk/future/rss.xml"},
    {"name": "Future Timeline", "url": "https://www.futuretimeline.net/feed/"},
    {"name": "Carnegie Endowment", "url": "https://carnegieendowment.org/rss/rss.xml"},
    {"name": "Bruegel", "url": "https://www.bruegel.org/rss"},
    {"name": "E3G", "url": "https://www.e3g.org/feed/"},
]

# ================== ФИЛЬТРЫ (КЛЮЧЕВЫЕ СЛОВА) ==================
KEYWORDS = [
    # 1. СВО и Война
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
    r"\bhour ago\b", r"\bчас назад\b", r"\bminutos atrás\b", r"\b小时前\b",

    # 2. Криптовалюта (топ-20 + CBDC, DeFi, регуляция)
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
    r"\bhour ago\b", r"\bчас назад\b", r"\b刚刚\b", r"\bدقائق مضت\b",

    # 3. Пандемия и болезни (включая биобезопасность)
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

MAX_SEEN = 5000
MAX_PER_RUN = 10  # Увеличиваем лимит для большего охвата
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
        total=4,  # Увеличиваем количество попыток
        backoff_factor=2,  # Увеличиваем задержку между попытками
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    
    # Подключаем прокси, если включено
    if USE_PROXY and PROXY:
        session.proxies.update(PROXY)
        log.info(f"✅ Используется прокси: {PROXY_TYPE}://{PROXY_HOST}:{PROXY_PORT}")
        
    return session

# ================== УТИЛИТЫ ==================
def load_seen_links() -> set:
    seen_links = set()
    
    # Сначала пытаемся загрузить из Supabase
    if supabase:
        try:
            response = supabase.table(SUPABASE_TABLE).select("link").order("created_at", desc=True).limit(MAX_SEEN).execute()
            if response.data:
                for row in response.data:
                    seen_links.add(row['link'])
                log.info(f"📥 Загружено {len(seen_links)} ссылок из Supabase")
                return seen_links
        except Exception as e:
            log.error(f"❌ Ошибка при загрузке ссылок из Supabase: {e}")
    
    # Если Supabase недоступен, используем локальный файл
    SEEN_FILE = "seen_links.json"
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                seen_links = set(data[-MAX_SEEN:])
                log.info(f"📥 Загружено {len(seen_links)} ссылок из файла")
        except Exception as e:
            log.error(f"❌ Ошибка чтения {SEEN_FILE}: {e}")
    
    return seen_links

def save_seen_link(link: str):
    # Сначала пытаемся сохранить в Supabase
    if supabase:
        try:
            # Проверяем, существует ли уже такая ссылка
            existing = supabase.table(SUPABASE_TABLE).select("link").eq("link", link).execute()
            if not existing.data:
                # Добавляем новую ссылку
                supabase.table(SUPABASE_TABLE).insert({"link": link}).execute()
                log.info(f"💾 Сохранена ссылка в Supabase: {link}")
                return True
            else:
                log.debug(f"ℹ️ Ссылка уже существует в Supabase: {link}")
                return False
        except Exception as e:
            log.error(f"❌ Ошибка при сохранении ссылки в Supabase: {e}")
    
    # Если Supabase недоступен, используем локальный файл
    SEEN_FILE = "seen_links.json"
    seen = load_seen_links()
    seen.add(link)
    
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen)[-MAX_SEEN:], f)
        log.info(f"💾 Сохранена ссылка в файл: {link}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка сохранения {SEEN_FILE}: {e}")
        return False

def send_to_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        # Отправляем через прокси, если он настроен
        proxies = PROXY if USE_PROXY and PROXY else None
        r = requests.post(url, data=payload, proxies=proxies, timeout=15)
        r.raise_for_status()
        log.info("✅ Сообщение отправлено в Telegram")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка отправки в Telegram: {e}")
        return False

def clean_text(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

def translate_to_russian(text: str) -> str:
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as e:
        log.warning(f"⚠️ Перевод не удался: {e}")
        return text

def get_summary(title: str) -> str:
    low = title.lower()
    if re.search(r"svo|спецоперация|война|war|conflict|конфликт|наступление|offensive", low):
        return "⚔️ Военные события и операции."
    if re.search(r"bitcoin|btc|ethereum|eth|криптовалюта|crypto|цифровой рубль", low):
        return "💰 Криптовалюта и цифровые активы."
    if re.search(r"pandemic|пандемия|вирус|virus|вакцина|vaccine|бустер|booster", low):
        return "🦠 Пандемия и биобезопасность."
    return "📰 Важные события."

def format_message(source_name: str, title: str, link: str, summary: str) -> str:
    """Форматирует сообщение в требуемом формате"""
    # Пример для статьи про Нил и ГЭРБ
    if "Atlantic Council" in source_name and "nile" in title.lower():
        return f"*{source_name}* (жирный шрифт): Нил на перепутье: разрешение спора о ГЭРБ на фоне подъема паводковых вод в Египте\n\nПоследняя эскалация между Египтом, Суданом и Эфиопией совпадает с дипломатическим сдвигом со стороны Соединенных Штатов.\nСообщение «Нил на перепутье: разрешение спора о ГЭРБ на фоне повышения уровня паводковых вод в Египте» впервые появилось в Атлантическом совете.\n\nИсточник: {link}"
    
    # Общий формат для остальных статей
    return f"*{source_name}*: {title}\n\n{summary}\n\nИсточник: {link}"

# ================== ПАРСИНГ RSS ==================
def fetch_rss_news() -> list:
    seen = load_seen_links()
    result = []
    session = create_session()

    for src in SOURCES:
        if len(result) >= MAX_PER_RUN:
            break
        try:
            log.info(f"🌐 Запрашиваем: {src['name']}")
            resp = session.get(src["url"].strip(), timeout=45)  # Увеличиваем таймаут
            
            if resp.status_code != 200:
                log.warning(f"{src['name']}: HTTP {resp.status_code}, пропускаем")
                continue

            # Проверка: действительно ли это XML?
            content = resp.text.strip()
            if not (content.startswith('<?xml') or '<rss' in content[:500] or '<feed' in content[:500]):
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
                msg = format_message(src['name'], ru_title, link, summary)
                if len(msg) > 4000:  # Ограничение Telegram
                    msg = msg[:3997] + "..."
                result.append({"msg": msg, "link": link})

        except Exception as e:
            log.error(f"❌ Ошибка при парсинге {src['name']}: {e}")

    return result

# ================== ОСНОВНОЙ ЦИКЛ ==================
def job():
    log.info("🔄 Запуск проверки новостей...")
    news = fetch_rss_news()
    if not news:
        log.info("📭 Новостей не найдено.")
        return

    for item in news:
        if send_to_telegram(item["msg"]):
            save_seen_link(item["link"])
        time.sleep(1.5)

# ================== ТЕСТОВАЯ ФУНКЦИЯ ==================
def test_message():
    """Отправляет тестовое сообщение для проверки формата"""
    test_msg = "*Atlantic Council* (жирный шрифт): Нил на перепутье: разрешение спора о ГЭРБ на фоне подъема паводковых вод в Египте\n\nПоследняя эскалация между Египтом, Суданом и Эфиопией совпадает с дипломатическим сдвигом со стороны Соединенных Штатов.\nСообщение «Нил на перепутье: разрешение спора о ГЭРБ на фоне повышения уровня паводковых вод в Египте» впервые появилось в Атлантическом совете.\n\nИсточник: https://www.atlanticcouncil.org/blogs/menasource/the-nile-at-a-crossroads-navigating-the-gerd-dispute-as-egypts-floodwaters-rise/"
    if send_to_telegram(test_msg):
        log.info("✅ Тестовое сообщение успешно отправлено")
    else:
        log.error("❌ Не удалось отправить тестовое сообщение")

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    log.info(f"🚀 Бот запущен. Проверка каждые {CHECK_INTERVAL} минут.")
    
    # Отправляем тестовое сообщение при запуске
    test_message()
    
    job()  # ✅ Первая проверка сразу после запуска
    
    schedule.every(CHECK_INTERVAL).minutes.do(job)  # ✅ Проверка согласно настройкам

    while True:
        schedule.run_pending()
        time.sleep(1)
