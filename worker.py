import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time
import os
from supabase import create_client
from telegram.ext import Application
from dateutil import parser as date_parser

# Настройки (берутся из переменных окружения в продакшене)
SUPABASE_URL = os.getenv("SUPABASE_URL", "your-supabase-url")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-supabase-key")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "your-telegram-token")
CHANNEL_IDS = ["@finanosint", "@time_n_John"]

# Инициализация
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Фильтры по категориям
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

# Компиляция регулярных выражений для производительности
COMPILED_FILTERS = {
    cat: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for cat, patterns in FILTERS.items()
}

def scrape_atlantic_council(url="https://www.atlanticcouncil.org/blogs/ukrainealert/"):
    """Парсер для Atlantic Council, особенно раздела UkraineAlert"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'  # Явное указание кодировки
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Поиск всех статей в блоге UkraineAlert
        articles = soup.find_all('article', class_=re.compile('post|article', re.I))
        
        results = []
        for article in articles[:5]:  # Ограничиваем до 5 свежих статей
            try:
                # Извлечение заголовка
                title_tag = article.find(['h2', 'h3', 'h1'], class_=re.compile('title|entry-title', re.I))
                if not title_tag:
                    continue
                    
                title = title_tag.get_text(strip=True)
                
                # Извлечение ссылки
                link_tag = title_tag.find('a') if not hasattr(title_tag, 'href') else title_tag
                if not link_tag:
                    continue
                    
                link = link_tag['href'] if 'href' in link_tag.attrs else None
                if not link:
                    continue
                    
                if not link.startswith('http'):
                    link = f"https://www.atlanticcouncil.org{link}"
                
                # Извлечение краткого описания
                summary_tag = article.find('p', class_=re.compile('excerpt|summary|description', re.I))
                summary = summary_tag.get_text(strip=True) if summary_tag else ""
                
                # Если нет краткого описания, возьмем первый абзац из контента
                if not summary:
                    content_div = article.find('div', class_=re.compile('content|entry-content', re.I))
                    if content_div:
                        first_p = content_div.find('p')
                        summary = first_p.get_text(strip=True) if first_p else ""
                
                # Извлечение даты публикации
                date_tag = article.find('time') or article.find(class_=re.compile('date|time', re.I))
                pub_date = None
                if date_tag:
                    date_str = date_tag.get('datetime', '') or date_tag.get_text(strip=True)
                    try:
                        pub_date = date_parser.parse(date_str).isoformat()
                    except:
                        pub_date = datetime.now().isoformat()
                else:
                    pub_date = datetime.now().isoformat()
                
                results.append({
                    "title": title,
                    "url": link,
                    "summary": summary[:300] + "..." if len(summary) > 300 else summary,  # Ограничиваем длину
                    "pub_date": pub_date,
                    "source": "Atlantic Council"
                })
            except Exception as e:
                print(f"Ошибка при обработке статьи Atlantic Council: {e}")
                continue
                
        return results
    except Exception as e:
        print(f"Критическая ошибка при парсинге Atlantic Council: {e}")
        return []

async def async_send_to_telegram(title, url, source, category, summary=None):
    """Асинхронная отправка сообщения в Telegram"""
    # Форматируем сообщение в требуемом формате
    message = (
        f"<b>{source.upper()}</b>: {title}\n\n"
    )
    
    if summary:
        message += f"{summary}\n\n"
    
    message += f"Источник: <a href='{url}'>{source}</a>"
    
    for channel in CHANNEL_IDS:
        try:
            await application.bot.send_message(
                chat_id=channel,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
            print(f"✅ Отправлено в {channel}: {title[:50]}...")
        except Exception as e:
            print(f"❌ Ошибка отправки в {channel}: {e}")

def send_to_telegram(title, url, source, category, summary=None):
    """Синхронная обертка для отправки сообщения"""
    import asyncio
    asyncio.run(async_send_to_telegram(title, url, source, category, summary))

def classify_article(title, summary):
    """Классификация статьи по категориям"""
    text = f"{title} {summary}".lower()
    
    for category, patterns in COMPILED_FILTERS.items():
        if any(pattern.search(text) for pattern in patterns):
            return category
    return None

def article_exists(url):
    """Проверка существования статьи в базе"""
    try:
        response = supabase.table("news_articles").select("id").eq("url", url).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Ошибка проверки существования статьи: {e}")
        return False

def save_article(title, url, description, pub_date, source, category):
    """Сохранение статьи в базу данных"""
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

def process_atlantic_council_articles():
    """Обработка статей с Atlantic Council"""
    print("🔍 Парсинг статей Atlantic Council...")
    articles = scrape_atlantic_council()
    
    if not articles:
        print("❌ Не удалось получить статьи Atlantic Council")
        return
    
    for article in articles:
        # Проверяем, не существует ли уже такая статья
        if article_exists(article['url']):
            print(f"⏩ Статья уже существует: {article['title'][:50]}...")
            continue
        
        # Классифицируем статью
        category = classify_article(article['title'], article['summary'])
        
        if category:
            print(f"✅ Найдена релевантная статья [{category}]: {article['title']}")
            
            # Сохраняем в базу
            if save_article(
                article['title'],
                article['url'],
                article['summary'],
                article['pub_date'],
                article['source'],
                category
            ):
                # Отправляем в Telegram
                send_to_telegram(
                    article['title'],
                    article['url'],
                    article['source'],
                    category,
                    article['summary']
                )
        else:
            print(f"⏭️ Статья не прошла фильтрацию: {article['title'][:50]}...")

def main():
    """Основная функция"""
    print("🚀 Запуск обработки новостей Atlantic Council...")
    process_atlantic_council_articles()
    print("✅ Обработка завершена")

if __name__ == "__main__":
    main()


