import logging
import aiohttp

class WildberriesParser:
    
    def _get_image_url(self, article: int, order: int = 1) -> str:
       
        article_int = int(article)
        vol = article_int // 100000
        part = article_int // 1000
        
        host = "https://basket-01.wbbasket.ru"
        if 0 <= vol <= 143: host = "https://basket-01.wbbasket.ru"
        elif 144 <= vol <= 287: host = "https://basket-02.wbbasket.ru"
        elif 288 <= vol <= 431: host = "https://basket-03.wbbasket.ru"
        elif 432 <= vol <= 719: host = "https://basket-04.wbbasket.ru"
        elif 720 <= vol <= 1007: host = "https://basket-05.wbbasket.ru"
        else: host = "https://basket-10.wbbasket.ru"
        
        return f"{host}/vol{vol}/part{part}/{article_int}/images/big/{order}.jpg"

    async def search_products(self, query: str, count: int = 20) -> list[dict]:
        """
        Ищет товары по запросу через API и сразу возвращает список с полными данными.
        """
        search_url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&curr=rub&dest=-1257786&query={query}&resultset=catalog&sort=popular&spp=30&suppressSpellcheck=false&limit={count}"
        
        products = []
        try:
            headers = {
                'Accept': '*/*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(search_url) as response:
                    if response.status != 200:
                        logging.error(f"Ошибка запроса к WB API: статус {response.status}")
                        return []
                    data = await response.json(content_type=None)

            if not data.get('data', {}).get('products'):
                logging.warning("WB API вернул успешный ответ, но без товаров.")
                return []

            for item in data['data']['products']:
                price = item.get('salePriceU', 0) / 100
                
                products.append({
                    "store": "🍓 Wildberries",
                    "name": item.get('name', 'Без названия'),
                    "price": price,
                    "price_with_card": None, 
                    "reviews_count": item.get('feedbacks', 0),
                    "rating": item.get('rating', 0),
                    "purchases_count": item.get('ordersCount', 0),
                    "article": item.get('id'),
                    "url": f"https://www.wildberries.ru/catalog/{item.get('id')}/detail.aspx",
                    "image_url": self._get_image_url(item.get('id'), order=1),
                })
            
            logging.info(f"Успешно найдено {len(products)} товаров на Wildberries.")
            return products

        except Exception as e:
            logging.error(f"Критическая ошибка при парсинге Wildberries: {e}")
            return []

    async def get_product_data(self, article: str) -> dict | None:
        logging.warning("Метод get_product_data для WB API не используется. Используйте search_products.")
        return None

    def quit(self):
        logging.info("Парсер WB (API) не требует закрытия драйвера.")