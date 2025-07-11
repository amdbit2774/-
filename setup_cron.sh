#!/bin/bash
# Скрипт для настройки автоматического запуска бота каждые 2 часа

# Определяем путь к скрипту
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SCRIPT_PATH="$SCRIPT_DIR/telegram_poster.py"
LOG_PATH="$SCRIPT_DIR/bot.log"

# Проверяем наличие скрипта
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Скрипт не найден: $SCRIPT_PATH"
    exit 1
fi

# Определяем путь к Python
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Python3 не найден в PATH"
    exit 1
fi

echo "🔧 Настройка автоматического запуска бота каждые 2 часа..."
echo "   Скрипт: $SCRIPT_PATH"
echo "   Python: $PYTHON_PATH"
echo "   Логи: $LOG_PATH"

# Создаем cron job
CRON_JOB="0 */2 * * * cd $SCRIPT_DIR && $PYTHON_PATH $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Проверяем, существует ли уже такая задача
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "⚠️  Задача для этого скрипта уже существует в crontab"
    echo "   Показать существующие задачи: crontab -l"
    echo "   Для замены задачи сначала удалите старую: crontab -e"
    exit 1
fi

# Добавляем новую задачу
echo "📝 Добавляем новую cron задачу..."
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron задача успешно добавлена!"
    echo ""
    echo "📋 Детали задачи:"
    echo "   Расписание: каждые 2 часа (в 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00)"
    echo "   Команда: $CRON_JOB"
    echo ""
    echo "🔍 Полезные команды:"
    echo "   Просмотр всех задач: crontab -l"
    echo "   Редактирование задач: crontab -e"
    echo "   Просмотр логов: tail -f $LOG_PATH"
    echo "   Удаление всех задач: crontab -r"
    echo ""
    echo "⚡ Первый запуск произойдет в ближайшее время, кратное 2 часам"
    echo "   Или запустите вручную для проверки: $PYTHON_PATH $SCRIPT_PATH"
else
    echo "❌ Ошибка при добавлении cron задачи"
    exit 1
fi 