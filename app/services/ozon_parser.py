import asyncio
import logging
import re
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class OzonParser:
    def __init__(self):
        self.driver = None
        self.semaphore = asyncio.Semaphore(1)
        asyncio.create_task(self._init_webdriver())

    async def _init_webdriver(self):
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            self.driver = webdriver.Chrome(options=options)
            logging.info("Драйвер Selenium для Ozon успешно инициализирован.")
        except Exception as e:
            logging.error(f"Не удалось инициализировать драйвер Ozon: {e}")
            self.driver = None

    async def _get_driver(self):
        if self.driver is None:
            await self._init_webdriver()
        try:
            _ = self.driver.window_handles
        except WebDriverException:
            logging.warning("Драйвер Ozon не отвечает. Перезапускаем...")
            await self._init_webdriver()
        if self.driver is None:
            raise ConnectionError("Не удалось запустить драйвер Ozon.")
        return self.driver

    def _parse_price(self, price_str: str) -> int:
        if not price_str: return 0
        return int("".join(filter(str.isdigit, price_str)))

    async def get_product_data(self, article: str) -> dict | None:
        async with self.semaphore:
            try:
                d = await self._get_driver()
                url = f"https://www.ozon.ru/product/{article}/"
                d.get(url)

                wait = WebDriverWait(d, 10)
                wait.until(EC.url_contains(article))
                
                h1_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                name = h1_element.text.strip()
                
                price, price_with_card = 0, 0
                try:
                    price_widget = d.find_element(by='css selector', value='div[data-widget="webPrice"]')
                    prices_text = [p.text for p in price_widget.find_elements(by='css selector', value='span') if '₽' in p.text]
                    if len(prices_text) >= 2:
                        price_with_card = self._parse_price(prices_text[0])
                        price = self._parse_price(prices_text[1])
                    elif len(prices_text) == 1:
                        price = self._parse_price(prices_text[0])
                        price_with_card = price
                except NoSuchElementException: pass

                reviews_count = 0
                rating = 0.0 
                try:
                    all_links = d.find_elements(By.TAG_NAME, "a")
                    for link in all_links:
                        link_text = link.text
                        if "отзыв" in link_text.lower() or "оцен" in link_text.lower():
                            
                            rating_match = re.search(r'(\d\.\d)', link_text)
                            if rating_match:
                                rating = float(rating_match.group(1))

                            
                            reviews_match = re.search(r'(\d[\d\s]*)\s*(отзыв|оцен)', link_text.lower())
                            if reviews_match:
                                reviews_count = int(reviews_match.group(1).replace(" ", ""))
                            
                            if reviews_count > 0: 
                                break
                except Exception as e:
                    logging.warning(f"Ошибка при парсинге отзывов/оценки Ozon: {e}")

                image_url = None
                try:
                    img_container = d.find_element(by='css selector', value='div[data-widget="webGallery"]')
                    img_element = img_container.find_element(by='tag name', value='img')
                    srcset = img_element.get_attribute('srcset')
                    if srcset:
                        sources = [s.strip().split(' ') for s in srcset.split(',')]
                        best_source = max(sources, key=lambda item: int(item[1][:-1]) if len(item) == 2 and item[1].endswith('w') else 0)
                        image_url = best_source[0]
                    else:
                        image_url = img_element.get_attribute('src')
                except Exception: pass

                return {
                    "store": "🔵 Ozon", "name": name, "price": price,
                    "price_with_card": price_with_card, "reviews_count": reviews_count,
                    "rating": rating, 
                    "purchases_count": 0, "article": article, "url": url, "image_url": image_url,
                }
            except TimeoutException:
                logging.error(f"Не удалось загрузить страницу для Ozon артикула {article} (тайм-аут).")
                return None
            except Exception as e:
                logging.error(f"Ошибка при парсинге Ozon артикула {article}: {e}")
                return None

    async def search_and_get_articles(self, query: str, count: int) -> list[str]:
        
        async with self.semaphore:
            try:
                d = await self._get_driver()
                search_url = f"https://www.ozon.ru/search/?text={query.replace(' ', '+')}&from_global=true"
                d.get(search_url)
                
                wait = WebDriverWait(d, 10)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/product/"]')))
                
                link_elements = d.find_elements(by='css selector', value='a[href*="/product/"]')
                unique_articles = []
                for link in link_elements:
                    try:
                        href = link.get_attribute('href')
                        article_match = re.search(r'/product/.*?[-/](\d{9,})/?', href)
                        if article_match:
                            article = article_match.group(1)
                            if article not in unique_articles: unique_articles.append(article)
                    except Exception: continue
                return unique_articles[:count]
            except Exception as e:
                logging.error(f"Ошибка при поиске на Ozon: {e}")
                return []

    def quit(self):
        if self.driver:
            self.driver.quit()
            logging.info("Драйвер Ozon остановлен.")