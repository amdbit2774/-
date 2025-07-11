#!/usr/bin/env python3
"""
Простой скрипт для управления промптом через Telegram бота
"""

import requests
import json
import time
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Конфигурация
BOT_TOKEN = "7493745933:AAF8WpI25Q4I04htDsyowSzrUYbgmee5OVk"
STORY_PROMPT_FILE = Path(__file__).parent / "story_prompt.txt"

def send_message(chat_id, text):
    """Отправляет сообщение через Telegram API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    response = requests.post(url, json=data)
    return response.json()

def get_updates(offset=0):
    """Получает обновления от Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {
        "offset": offset,
        "timeout": 30
    }
    response = requests.get(url, params=params)
    return response.json()

def write_story_prompt(new_prompt):
    """Записывает новый промпт в файл"""
    try:
        with open(STORY_PROMPT_FILE, 'w', encoding='utf-8') as f:
            f.write(new_prompt)
        logging.info(f"Промпт обновлен. Длина: {len(new_prompt)} символов")
        return True
    except Exception as e:
        logging.error(f"Ошибка записи промпта: {e}")
        return False

def run_story_step():
    """Запускает основной скрипт"""
    import subprocess
    try:
        result = subprocess.run(['python3', 'telegram_poster.py'], 
                              capture_output=True, text=True, cwd=Path(__file__).parent)
        if result.returncode == 0:
            return "✅ Шаг истории выполнен успешно!"
        else:
            return f"❌ Ошибка: {result.stderr}"
    except Exception as e:
        return f"❌ Ошибка запуска: {e}"

def main():
    """Основной цикл бота"""
    logging.info("🤖 Запуск бота для управления промптом...")
    
    # Получаем информацию о боте
    bot_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe").json()
    if bot_info['ok']:
        logging.info(f"Бот запущен: @{bot_info['result']['username']}")
    else:
        logging.error("Ошибка получения информации о боте")
        return
    
    last_update_id = 0
    
    logging.info("Бот готов к работе. Ctrl+C для остановки.")
    
    try:
        while True:
            # Получаем обновления
            updates = get_updates(last_update_id + 1)
            
            if updates['ok']:
                for update in updates['result']:
                    last_update_id = update['update_id']
                    
                    if 'message' in update and 'text' in update['message']:
                        message = update['message']
                        chat_id = message['chat']['id']
                        text = message['text']
                        
                        logging.info(f"Получено сообщение: {text[:50]}...")
                        
                        if text.startswith('/start'):
                            # Запуск истории
                            send_message(chat_id, "🚀 Запускаю шаг истории...")
                            result = run_story_step()
                            send_message(chat_id, result)
                            
                        elif len(text) >= 10:
                            # Обновление промпта
                            if write_story_prompt(text):
                                send_message(chat_id, f"✅ Промпт обновлен! Длина: {len(text)} символов")
                            else:
                                send_message(chat_id, "❌ Ошибка при сохранении промпта")
                        else:
                            send_message(chat_id, "❌ Промпт слишком короткий (минимум 10 символов)")
            
            time.sleep(1)  # Небольшая пауза
            
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем")
    except Exception as e:
        logging.error(f"Ошибка: {e}")

if __name__ == "__main__":
    main() 