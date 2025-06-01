# 🌍 Telegram-бот для автоматизации создания контента о путешествиях  

Telegram-бот, разработанный для автоматизации создания и публикации контента о путешествиях (тексты + изображения) и публикации в Telegram-канал.  
Поддерживает генерацию текстов через **YandexGPT** и **OpenAI**, изображений через **Yandex.Art**, планирование публикаций и анализ статистики.  

---

## 📌 Основные функции  
- **Генерация тем:** Выбор из предложенных, перегенерация новых или ввод пользовательской темы.  
- **Создание текста:** Генерация текстов в 4 стилях (непринуждённый, профессиональный, юмористический, поэтический) через YandexGPT или OpenAI.  
- **Генерация изображений:** Автоматическое создание промптов или ручной ввод через Yandex.Art.  
- **Планирование публикаций:** Настройка даты, времени и частоты публикации.  
- **Просмотр постов:** Интерфейс с пагинацией для управления запланированными постами.  
- **Анализ статистики:** Мониторинг просмотров, реакций и комментариев через Telegram API.  

---

## 🛠️ Технологии  
- **Фреймворки:** Aiogram, Aiogram-Dialog, SQLAlchemy  
- **База данных:** SQLite  
- **API:** YandexGPT, Yandex.Art, OpenAI, Telegram Bot API  
- **Планировщик задач:** APScheduler  
- **Хостинг:** [selectel.ru](https://selectel.ru/?ref_code=fa0eda2547)   

---

## 📁 Структура проекта  
```bash  
travel-content-bot/  
│  
├── main.py                 # Точка входа  
├── requirements.txt        # Зависимости  
├── .env                    # Переменные окружения  
├── README.md               # Это описание  
├── LICENSE.md              # Лицензия GNU GPL-3.0  
├── bot/  
│   ├── dialogs/            # Диалоги через aiogram-dialog  
│   ├── handlers/           # Обработчики событий  
│   ├── keyboards/          # Клавиатура и кнопки  
│   ├── middlewares/        # Middleware (например, проверка прав администратора)  
├── config/  
│   ├── env.py              # Настройки через .env  
│   ├── config.py           # Конфигурация проекта  
│   └── logging_config.py  # Логирование  
├── database/  
│   ├── models.py           # ORM-модели базы данных  
│   └── db.py               # Работа с базой  
├── openai_api/  
│   └── client.py           # Интеграция с OpenAI  
├── yandex_gpt/  
│   └── client.py           # Интеграция с YandexGPT  
├── yandex_art/  
│   └── client.py           # Генерация изображений  
├── telegram_api/  
│   └── client.py           # Публикация постов и статистика  
├── scheduler/  
│   └── scheduler.py        # Планирование публикаций  
└── media/                  # Скриншоты и изображения  
```  

---

## 🚀 Установка и запуск  

### **1. Клонируйте репозиторий**  
```bash  
git clone https://github.com/dn0sh/travel-content-bot.git  
cd travel-content-bot  
```

### **2. Установите зависимости**  
```bash  
pip install -r requirements.txt  
```

### **3. Настройте переменные окружения**  
Создайте файл `.env` с данными:  
```env  
TELEGRAM_BOT_TOKEN=ваш_токен_bot  
TELEGRAM_ADMIN_IDS=ваш_id_telegram  
YANDEX_FOLDER_ID=ваш_folder_id  
YANDEX_GPT_API_KEY=ваш_ключ_yandexgpt  
YANDEX_ART_API_KEY=ваш_ключ_yandexart  
OPENAI_API_KEY=ваш_ключ_openai  
TIME_ZONE=Europe/Moscow  
```

### **4. Запустите бота**  
```bash  
python main.py  
```

---

## 📸 Примеры работы  
![Скриншоты](_examples/*.jpg)  

---

## 📄 Лицензия  
Проект распространяется под лицензией [GNU General Public License v3.0](LICENSE.md).  
Автор: [Дмитрий Шамараев](https://t.me/turmerig)  

---

## 📈 Планы по развитию  
### **1. Управление администраторами через QR-коды**  
- Генерация уникальных токенов и QR-кодов для приглашения новых админов.  
- Удаление администраторов через интерфейс бота.  

### **2. Расширение тематики**  
- Добавление категорий: **технологии**, **образование**, **здоровье**, **бизнес** и др.  
- Настройка ИИ-моделей для генерации контента в новых нишах.  

### **3. Улучшение интерфейса**  
- Фильтры постов (по дате, статусу, популярности).  
- Массовое планирование публикаций.  

### **4. Многоязычность**  
- Поддержка английского, испанского и других языков.  

### **5. Интеграция новых ИИ-сервисов**  
- Подключение DALL·E, Stable Diffusion и других моделей.  

---

## 📬 Контакты  
Telegram: [@turmerig](https://t.me/turmerig)  
Email: turmerig0@gmail.com  
GitHub: [github.com/dn0sh](https://github.com/dn0sh)  

---

## 🤝 Как внести вклад  
1. Fork репозитория.  
2. Создайте ветку `feature/ваше-изменение`.  
3. Отправьте Pull Request.  
4. Добавьте issue с описанием бага или идеи.  

---

## 📚 Полезные ссылки  
- [GNU GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.txt) — текст лицензии  
- [Telegram Bot API](https://core.telegram.org/bots/api) — документация  
- [YandexGPT](https://cloud.yandex.ru/services/llm/yandexgpt) — документация  
- [OpenAI API](https://platform.openai.com/docs) — документация  
- [Selectel.ru](https://https://selectel.ru/?ref_code=fa0eda2547) — хостинг проекта  

---

## 📋 Поддержка и обратная связь  
- Сообщайте о багах: [issues GitHub](https://github.com/dn0sh/travel-content-bot/issues)  
- Запрашивайте новые функции: [Telegram](https://t.me/turmerig)  
- Связь с автором: turmerig0@gmail.com  

---

## 🧪 Тестирование  
Для запуска тестов:  
```bash  
pytest tests/  
```  
Тесты проверяют:  
- Корректность генерации текста и изображений.  
- Работу планировщика.  
- Интеграцию с API (YandexGPT, OpenAI, Telegram).  

---

## 📦 Требования к системе  
- Python 3.11+  
- SQLite 3.35+  
- Активные API-ключи: YandexGPT, Yandex.Art, OpenAI (опционально)  
