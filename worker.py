import os
import time
import re
import feedparser
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from telegram.ext import Application
from datetime import datetime
from dateutil import parser as date_parser
import html

# --- Настройки из переменных окружения ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNELS = ["@finanosint", "@time_n_John"]

# --- Инициализация ---
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Application.builder().token(TELEGRAM_TOKEN).build()

# --- Фильтры по категориям ---
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

# --- Источники ---
SOURCES = [
    {"name": "The Economist", "rss": "https://www.economist.com/rss/latest/rss.xml"},
    {"name": "Bloomberg", "rss": "https://feeds.bloomberg.com/markets/news.rss"},
    {"name": "RAND Corporation", "rss": "https://www.rand.org/rss.xml"},
    {"name": "CSIS", "rss": "https://www.csis.org/rss.xml"},
    {"name": "Chatham House", "rss": "https://www.chathamhouse.org/feed"},
    {"name": "Foreign Affairs", "rss": "https://www.foreignaffairs.com/rss.xml"},
    {"name": "CFR", "rss": "https://www.cfr.org/rss.xml"},
    {"name": "BBC Future", "rss": "https://www.bbc.com/future/rss"},
    {"name": "Future Timeline", "rss": "https://futuretimeline.net/blog.rss"},
    {"name": "Carnegie Endowment", "rss": "https://carnegieendowment.org/feed"},
    {"name": "Bruegel", "rss": "https://bruegel.org/feed/"},
    {"name": "E3G", "rss": "https://e3g.org/feed/"},
    {"name": "Atlantic Council", "custom_parser": lambda: scrape_atlantic_council()},
    {"name": "Good Judgment", "custom_parser": lambda: scrape_good_judgment()},
    {"name": "Metaculus", "custom_parser": lambda: scrape_metaculus()},
    {"name": "DNI Global Trends", "custom_parser": lambda: scrape_odni()},
]

# --- Компилируем регулярки ---
COMPILED_FILTERS = {
    cat: [re.compile(p, re.IGNORECASE) for p in patterns]
    for cat, patterns in FILTERS.items()
}

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
    try:
        response = supabase.table("news_articles").select("id").eq("url", url).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Ошибка проверки существования статьи: {e}")
        return False

def save_article(title, url, description, pub_date, source, category):
    try:
        supabase.table("news_articles").insert({
            "title": title,
            "url": url,
            "description": description or "",
            "pub_date": pub_date,
            "source_name": source,
            "category": category
        }).execute()
        return True
    except Exception as e:
        print(f"Ошибка сохранения статьи: {e}")
        return False

async def async_send_to_telegram(title, url, source, category, summary=None):
    # Форматируем сообщение в требуемом формате
    message = f"<b>{source.upper()}</b>: {title}\n\n"
    
    if summary:
        # Ограничиваем длину описания
        summary = summary[:500] + "..." if len(summary) > 500 else summary
        message += f"{summary}\n\n"
    
    message += f"Источник: <a href='{url}'>{source}</a>"
    
    for channel in CHANNELS:
        try:
            await app.bot.send_message(
                chat_id=channel,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
            print(f"✅ Отправлено в {channel}: {title[:50]}...")
        except Exception as e:
            print(f"❌ Ошибка отправки в {channel}: {e}")

def send_to_telegram(title, url, source, category, summary=None):
    import asyncio
    asyncio.run(async_send_to_telegram(title, url, source, category, summary))

# --- Специализированный парсер для Atlantic Council ---
def scrape_atlantic_council(url="https://www.atlanticcouncil.org/blogs/ukrainealert/"):
    """Улучшенный парсер для Atlantic Council, особенно раздела UkraineAlert"""
    print("🔍 Парсинг статей Atlantic Council...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        # Увеличиваем таймаут для надежности
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Проверяем на HTTP ошибки
        
        # Явно указываем кодировку
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем статьи в блоге UkraineAlert
        articles = []
        
        # Вариант 1: Ищем по контейнерам статей
        article_containers = soup.find_all('article', class_=lambda x: x and ('post' in x.lower() or 'article' in x.lower()))
        
        if not article_containers:
            # Вариант 2: Ищем по другим признакам
            article_containers = soup.select('div[class*="blog-post"], div[class*="post-"]')
        
        if not article_containers:
            # Вариант 3: Ищем по заголовкам h2/h3 с ссылками
            titles = soup.find_all(['h2', 'h3'])
            for title in titles:
                link = title.find('a')
                if link and '/blogs/ukrainealert/' in link.get('href', ''):
                    article_containers.append(title.parent)
        
        print(f"Найдено контейнеров статей: {len(article_containers)}")
        
        for container in article_containers[:5]:  # Ограничиваем до 5 свежих статей
            try:
                # Ищем заголовок
                title_tag = container.find(['h1', 'h2', 'h3'], class_=lambda x: x and ('title' in x.lower() or 'headline' in x.lower()))
                if not title_tag:
                    # Альтернативный поиск заголовка
                    title_tag = container.select_one('h2 a, h3 a, .post-title a, .entry-title a')
                    if title_tag and title_tag.name == 'a':
                        title = title_tag.get_text(strip=True)
                        link = title_tag.get('href')
                    else:
                        continue
                else:
                    title = title_tag.get_text(strip=True)
                    link_tag = title_tag.find('a')
                    link = link_tag.get('href') if link_tag else None
                
                if not link:
                    continue
                
                # Нормализуем ссылку
                if not link.startswith('http'):
                    if link.startswith('/'):
                        link = f"https://www.atlanticcouncil.org{link}"
                    else:
                        link = f"https://www.atlanticcouncil.org/blogs/ukrainealert/{link}"
                
                # Получаем описание
                summary = ""
                summary_tag = container.find('p', class_=lambda x: x and ('excerpt' in x.lower() or 'summary' in x.lower() or 'description' in x.lower()))
                if not summary_tag:
                    summary_tag = container.select_one('div.entry-content p, .post-content p, .article-content p')
                
                if summary_tag:
                    summary = summary_tag.get_text(strip=True)
                
                # Если нет описания, пробуем получить из meta-тегов при переходе на страницу статьи
                if not summary:
                    try:
                        article_response = requests.get(link, headers=headers, timeout=15)
                        article_response.encoding = 'utf-8'
                        article_soup = BeautifulSoup(article_response.text, 'html.parser')
                        
                        # Ищем первый абзац в основном контенте
                        content_div = article_soup.select_one('div.entry-content, div.post-content, div.article-content, div.blog-content')
                        if content_div:
                            first_p = content_div.find('p')
                            if first_p:
                                summary = first_p.get_text(strip=True)[:300] + "..."
                    except Exception as e:
                        print(f"Не удалось получить описание со страницы статьи: {e}")
                
                # Ищем дату публикации
                pub_date = datetime.now().isoformat()
                date_tag = container.find('time') or container.select_one('time, .date, .published')
                if date_tag:
                    date_str = date_tag.get('datetime') or date_tag.get_text(strip=True)
                    try:
                        if date_str:
                            pub_date_obj = date_parser.parse(date_str)
                            pub_date = pub_date_obj.isoformat()
                    except Exception as e:
                        print(f"Не удалось распарсить дату: {e}")
                
                # Создаем статью
                article = {
                    "title": html.unescape(title),
                    "url": link,
                    "summary": html.unescape(summary) if summary else "Описание отсутствует",
                    "pub_date": pub_date,
                    "source": "Atlantic Council"
                }
                articles.append(article)
                print(f"✅ Найдена статья: {title[:60]}...")
                
            except Exception as e:
                print(f"Ошибка при обработке статьи: {e}")
                continue
        
        if not articles:
            print("⚠️ Статьи не найдены. Структура сайта могла измениться.")
            # Для отладки сохраняем HTML в лог
            print(f"🔍 Фрагмент HTML: {response.text[:500]}...")
        
        return articles
        
    except Exception as e:
        print(f"❌ Критическая ошибка при парсинге Atlantic Council: {e}")
        print(f"Статус ответа: {response.status_code if 'response' in locals() else 'Нет ответа'}")
        return []

# --- Парсеры для других сайтов ---
def scrape_good_judgment():
    print("🔍 Парсинг статей Good Judgment...")
    url = "https://goodjudgment.com/blog"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск статей
        posts = soup.select('article.post, div.blog-post, .post-item')[:5]
        
        for post in posts:
            title_tag = post.select_one('h2, h3, .post-title, .entry-title')
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            link_tag = title_tag.find('a') or post.select_one('a.read-more, a.more-link')
            if not link_tag:
                continue
                
            link = link_tag.get('href')
            if not link.startswith('http'):
                link = "https://goodjudgment.com" + link
                
            summary_tag = post.select_one('p.excerpt, .post-excerpt, .entry-summary, p')
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            
            pub_date = datetime.now().isoformat()
            date_tag = post.select_one('time, .date, .published')
            if date_tag:
                date_str = date_tag.get('datetime') or date_tag.get_text(strip=True)
                try:
                    pub_date = date_parser.parse(date_str).isoformat()
                except:
                    pass
            
            if article_exists(link):
                print(f"⏩ Статья уже существует: {title[:50]}...")
                continue
                
            category = classify_article(title, summary)
            if category:
                print(f"✅ Найдена релевантная статья [{category}]: {title}")
                if save_article(title, link, summary, pub_date, "Good Judgment", category):
                    send_to_telegram(title, link, "Good Judgment", category, summary)
            else:
                print(f"⏭️ Статья не прошла фильтрацию: {title[:50]}...")
                
    except Exception as e:
        print(f"❌ Ошибка парсинга Good Judgment: {e}")

def scrape_metaculus():
    print("🔍 Парсинг статей Metaculus...")
    url = "https://www.metaculus.com/questions/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск вопросов/статей
        items = soup.select('div.question-card, .question-list-item, .forecast-item')[:5]
        
        for item in items:
            title_tag = item.select_one('a.title-link, h3 a, .question-title a')
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            link = "https://www.metaculus.com" + title_tag.get('href')
            
            summary_tag = item.select_one('div.blurb, .question-description, p.description')
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            
            pub_date = datetime.now().isoformat()
            
            if article_exists(link):
                print(f"⏩ Статья уже существует: {title[:50]}...")
                continue
                
            category = classify_article(title, summary)
            if category:
                print(f"✅ Найдена релевантная статья [{category}]: {title}")
                if save_article(title, link, summary, pub_date, "Metaculus", category):
                    send_to_telegram(title, link, "Metaculus", category, summary)
            else:
                print(f"⏭️ Статья не прошла фильтрацию: {title[:50]}...")
                
    except Exception as e:
        print(f"❌ Ошибка парсинга Metaculus: {e}")

def scrape_odni():
    print("🔍 Парсинг статей DNI Global Trends...")
    url = "https://www.dni.gov/index.php/gt2040-home"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск статей/отчетов
        articles = soup.select('div.article, .press-release, .report-item, .content-item')[:5]
        
        for article in articles:
            title_tag = article.select_one('h2, h3, .title, .headline')
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
            
            summary_tag = article.select_one('p.summary, .description, p')
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            
            pub_date = datetime.now().isoformat()
            
            if article_exists(link):
                print(f"⏩ Статья уже существует: {title[:50]}...")
                continue
                
            category = classify_article(title, summary)
            if category:
                print(f"✅ Найдена релевантная статья [{category}]: {title}")
                if save_article(title, link, summary, pub_date, "DNI Global Trends", category):
                    send_to_telegram(title, link, "DNI Global Trends", category, summary)
            else:
                print(f"⏭️ Статья не прошла фильтрацию: {title[:50]}...")
                
    except Exception as e:
        print(f"❌ Ошибка парсинга DNI: {e}")

# --- RSS парсеры ---
def fetch_from_rss(source):
    print(f"🔍 Получение статей из RSS: {source['name']}")
    try:
        feed = feedparser.parse(source["rss"])
        if feed.bozo:
            print(f"⚠️ Ошибка парсинга RSS {source['name']}: {feed.bozo_exception}")
            return
            
        print(f"Получено статей из {source['name']}: {len(feed.entries)}")
        
        for entry in feed.entries[:10]:  # Ограничиваем до 10 свежих статей
            url = entry.link
            title = entry.title.strip()
            summary = entry.get("summary", "") or entry.get("description", "")
            pub_date = entry.get("published", datetime.now().isoformat())
            
            if not url or not title:
                continue
                
            if not is_recent(entry, max_hours=2):
                continue
                
            if article_exists(url):
                print(f"⏩ Статья уже существует: {title[:50]}...")
                continue
                
            category = classify_article(title, summary)
            if category:
                print(f"✅ Найдена релевантная статья [{category}]: {title}")
                if save_article(title, url, summary, pub_date, source["name"], category):
                    send_to_telegram(title, url, source["name"], category, summary)
            else:
                print(f"⏭️ Статья не прошла фильтрацию: {title[:50]}...")
                
    except Exception as e:
        print(f"❌ Ошибка обработки {source['name']}: {e}")

def fetch_and_process():
    for source in SOURCES:
        if "custom_parser" in source:
            print(f"\n🔍 Обработка источника: {source['name']} (кастомный парсер)")
            source["custom_parser"]()
        else:
            print(f"\n🔍 Обработка источника: {source['name']} (RSS)")
            fetch_from_rss(source)

# --- Основной цикл ---
if __name__ == "__main__":
    print("🚀 Background Worker запущен. Ожидание 14 минут между проверками...")
    while True:
        print(f"\n{'='*50}")
        print(f"🕒 Проверка всех источников: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        fetch_and_process()
        print(f"{'='*50}")
        print(f"⏳ Следующая проверка через 14 минут...")
        time.sleep(14 * 60)
