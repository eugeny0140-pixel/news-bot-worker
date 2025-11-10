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
from supabase import create_client, Client

# ================== НАСТРОЙКИ ==================
# 🔑 Токен берется из переменной окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("❌ Ошибка: переменная окружения TELEGRAM_TOKEN не установлена")

CHANNEL_ID = os.getenv('CHANNEL_ID', "@time_n_John")

# 🗄️ Настройки Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Ошибка: SUPABASE_URL и SUPABASE_KEY обязательны для работы")

# Создаем подключение к Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
log = logging.getLogger(__name__)
log.info("✅ Подключение к Supabase успешно установлено")

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

MAX_PER_RUN = 10
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 15))

# ================== ЛОГИРОВАНИЕ ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ================== ЗАГОЛОВКИ ==================
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Accept': 'application/rss+xml, application/xml;q=0.9, */*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# ================== УТИЛИТЫ ==================
def is_article_published(url: str) -> bool:
    """Проверяет, была ли статья уже опубликована"""
    try:
        response = supabase.table('news_articles').select('id').eq('url', url).execute()
        return bool(response.data)
    except Exception as e:
        log.error(f"Ошибка при проверке публикации: {e}")
        return False

def get_article_category(title: str) -> str:
    """Определяет категорию статьи"""
    low = title.lower()
    if re.search(r"svo|спецоперация|война|war|conflict|конфликт|наступление|offensive", low):
        return "SVO"
    if re.search(r"bitcoin|btc|ethereum|eth|криптовалюта|crypto|цифровой рубль", low):
        return "Crypto"
    if re.search(r"pandemic|пандемия|вирус|virus|вакцина|vaccine|бустер|booster", low):
        return "Pandemic"
    return "Other"

def save_article(title: str, url: str, description: str, pub_date: str, source_name: str):
    """Сохраняет статью в Supabase"""
    category = get_article_category(title)
    
    # Проверяем, не опубликована ли уже статья
    if is_article_published(url):
        log.info(f"ℹ️ Статья уже опубликована: {url}")
        return False
    
    try:
        data = {
            'title': title,
            'url': url,
            'description': description,
            'pub_date': pub_date,
            'source_name': source_name,
            'category': category
        }
        
        supabase.table('news_articles').insert(data).execute()
        log.info(f"✅ Статья сохранена в базу: {url}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка сохранения статьи: {e}")
        return False

def format_message(source_name: str, title: str, link: str, description: str) -> str:
    """Форматирует сообщение в требуемом формате"""
    # Используем только первые 2-3 предложения описания как краткий лит
    sentences = [s.strip() for s in description.split('. ') if s.strip()]
    brief = ". ".join(sentences[:2]) + "." if sentences else ""
    
    # Форматируем сообщение по требуемому шаблону
    return f"*{source_name}*:\n\n{title}\n\n{brief}\n\nИсточник: {link}"

def send_to_telegram(text: str) -> bool:
    """Отправляет сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=payload, timeout=15)
        r.raise_for_status()
        log.info("✅ Сообщение отправлено в Telegram")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка отправки в Telegram: {e}")
        return False

def clean_text(t: str) -> str:
    """Очищает текст от лишних пробелов и переносов"""
    return re.sub(r"\s+", " ", t).strip()

def translate_to_russian(text: str) -> str:
    """Переводит текст на русский язык"""
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except Exception as e:
        log.warning(f"⚠️ Перевод не удался: {e}")
        return text

# ================== ПАРСИНГ RSS ==================
def fetch_rss_news() -> list:
    """Получает новости из RSS-лент"""
    result = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for src in SOURCES:
        if len(result) >= MAX_PER_RUN:
            break
        try:
            log.info(f"🌐 Запрашиваем: {src['name']}")
            resp = session.get(src["url"].strip(), timeout=30)
            
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
                description_tag = item.find("description") or item.find("summary")
                pub_date_tag = item.find("pubDate")

                if not title_tag or not link_tag:
                    continue

                title = clean_text(title_tag.get_text())
                link = clean_text(link_tag.get_text() if hasattr(link_tag, 'get_text') else link_tag.text)
                description = clean_text(description_tag.get_text()) if description_tag else ""
                pub_date = clean_text(pub_date_tag.get_text()) if pub_date_tag else ""

                if not title or not link:
                    continue

                # Проверяем ключевые слова
                if not any(re.search(kw, title, re.IGNORECASE) for kw in KEYWORDS):
                    continue

                # Проверяем, не была ли статья уже опубликована
                if is_article_published(link):
                    continue

                ru_title = translate_to_russian(title)
                description_ru = translate_to_russian(description) if description else ""
                msg = format_message(src['name'], ru_title, link, description_ru)
                
                if len(msg) > 4000:  # Ограничение Telegram
                    msg = msg[:3997] + "..."
                    
                result.append({
                    "msg": msg, 
                    "link": link,
                    "title": title,
                    "description": description,
                    "pub_date": pub_date,
                    "source_name": src['name']
                })

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
            save_article(
                item["title"],
                item["link"],
                item["description"],
                item["pub_date"],
                item["source_name"]
            )
        time.sleep(1.5)

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    log.info(f"🚀 Бот запущен. Проверка каждые {CHECK_INTERVAL} минут.")
    
    # Проверка подключения к Supabase
    try:
        response = supabase.table('news_articles').select('id').limit(1).execute()
        log.info("✅ Подключение к Supabase проверено успешно")
    except Exception as e:
        log.error(f"❌ Ошибка подключения к Supabase: {e}")
        raise SystemExit("Не удалось подключиться к Supabase")
    
    job()  # ✅ Первая проверка сразу после запуска
    
    schedule.every(CHECK_INTERVAL).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
