# worker_simple.py
import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import schedule
from supabase import create_client

# Настройки
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRIMARY_CHANNEL = "@time_n_John"
SECONDARY_CHANNEL = "@finanosint"
CHANNELS = [PRIMARY_CHANNEL, SECONDARY_CHANNEL]

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Рабочие источники (обновленный список)
SOURCES = [
    # Atlantic Council
    {"name": "Atlantic Council", "url": "https://www.atlanticcouncil.org/feed/"},
    # Reuters World
    {"name": "Reuters", "url": "https://www.reuters.com/world/rss.xml"},
    # Al Jazeera
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    # DW News
    {"name": "DW News", "url": "https://rss.dw.com/xml/rss-en-all"},
    # Good Judgment
    {"name": "Good Judgment", "url": "https://goodjudgment.com/feed/"}, # Предполагаемый RSS
    # Johns Hopkins Center for Health Security
    {"name": "Johns Hopkins", "url": "https://www.centerforhealthsecurity.org/feed.xml"}, # Предполагаемый RSS
    # Metaculus
    {"name": "Metaculus", "url": "https://www.metaculus.com/questions/feed/"}, # Предполагаемый RSS
    # DNI Global Trends (официальный сайт может не иметь RSS, пропускаем или используем веб-скрапинг)
    # RAND Corporation
    {"name": "RAND Corporation", "url": "https://www.rand.org/rss.xml"},
    # World Economic Forum
    {"name": "World Economic Forum", "url": "https://www.weforum.org/feed"},
    # CSIS
    {"name": "CSIS", "url": "https://www.csis.org/rss.xml"},
    # Chatham House
    {"name": "Chatham House", "url": "https://www.chathamhouse.org/rss.xml"},
    # The Economist
    {"name": "The Economist", "url": "https://www.economist.com/rss/latest/rss.xml"},
    # Bloomberg
    {"name": "Bloomberg", "url": "https://feeds.bloomberg.com/markets/news.rss"},
    # Reuters Institute
    {"name": "Reuters Institute", "url": "https://reutersinstitute.politics.ox.ac.uk/rss.xml"}, # Предполагаемый RSS
    # Foreign Affairs
    {"name": "Foreign Affairs", "url": "https://www.foreignaffairs.com/rss.xml"},
    # CFR
    {"name": "CFR", "url": "https://www.cfr.org/rss.xml"},
    # BBC Future
    {"name": "BBC Future", "url": "https://www.bbc.com/future/section/technology-future/rss.xml"}, # Один из разделов
    # Carnegie Endowment
    {"name": "Carnegie Endowment", "url": "https://carnegieendowment.org/rss.xml"},
    # Bruegel
    {"name": "Bruegel", "url": "https://www.bruegel.org/rss.xml"},
    # E3G
    {"name": "E3G", "url": "https://e3g.org/feed/"} # Предполагаемый RSS
]

# Расширенные ключевые слова
KEYWORDS = [
    # СВО и Война
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
    
    # Криптовалюта
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
    
    # Пандемия и болезни
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

# Функция для получения RSS
def get_rss_feed(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logging.error(f"Error fetching RSS feed from {url}: {e}")
        return None

# Функция для парсинга RSS
def parse_rss(content):
    try:
        soup = BeautifulSoup(content, 'xml')
        items = soup.find_all('item')
        articles = []
        for item in items:
            title = item.find('title').text if item.find('title') else "No title"
            link = item.find('link').text if item.find('link') else "No link"
            description = item.find('description').text if item.find('description') else "No description"
            pub_date = item.find('pubDate').text if item.find('pubDate') else "Unknown date"
            articles.append({
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date
            })
        return articles
    except Exception as e:
        logging.error(f"Error parsing RSS content: {e}")
        return []

# Функция для проверки ключевых слов
def contains_keywords(text):
    text_lower = text.lower()
    for pattern in KEYWORDS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False

# Функция для перевода
def translate_text(text, target_lang='ru'):
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text)
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return text # Возвращаем оригинальный текст при ошибке

# Функция для отправки в Telegram
def send_to_telegram(message, channel):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": channel,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        logging.info(f"Message sent to {channel}")
    except Exception as e:
        logging.error(f"Error sending message to {channel}: {e}")

# Основная функция
def job():
    logging.info("Starting news check...")
    new_articles = 0
    
    for source in SOURCES:
        logging.info(f"Checking source: {source['name']}")
        rss_content = get_rss_feed(source["url"])
        if rss_content:
            articles = parse_rss(rss_content)
            
            for article in articles:
                title = article['title']
                link = article['link']
                description = article['description']
                pub_date = article['pub_date']
                
                # Проверка на дубликаты в Supabase (предполагаем, что у вас есть таблица 'articles' с колонкой 'title')
                try:
                    existing_article = supabase.table('articles').select('id').eq('title', title).execute()
                    if existing_article.data:
                        logging.info(f"Duplicate article found: {title}")
                        continue # Пропускаем дубликат
                except Exception as e:
                    logging.error(f"Error checking for duplicates: {e}")
                    continue # Продолжаем, если не можем проверить
                
                # Проверка ключевых слов
                if contains_keywords(title) or contains_keywords(description):
                    translated_title = translate_text(title)
                    translated_description = translate_text(description)
                    
                    message = f"<b>{source['name']}</b>\n\n{translated_title}\n\n{translated_description}\n\n{link}"
                    
                    for channel in CHANNELS:
                        send_to_telegram(message, channel)
                    
                    # Сохраняем статью в Supabase
                    try:
                        supabase.table('articles').insert({
                            'title': title,
                            'link': link,
                            'description': description,
                            'pub_date': pub_date,
                            'source_name': source['name']
                        }).execute()
                    except Exception as e:
                        logging.error(f"Error saving article to Supabase: {e}")
                    
                    new_articles += 1
                else:
                    logging.info(f"Article does not match keywords: {title}")
    
    logging.info(f"News check completed. {new_articles} new articles processed.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    job()  # Первая проверка
    schedule.every(15).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
