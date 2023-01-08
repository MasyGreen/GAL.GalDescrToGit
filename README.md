# Назначение
Скачивание патчей обновлений для Galaktika ERP 9.1 с ftp.galaktika.ru
Pyton 3.10

# Настройки config.py

* mailpassword = хеш-пароль для отправки почты 
* mailsmtpserver = имя smtp сервера
* mailsmtpport = порт smtp 587
* mailadr = почтовый ящик отправителя
* ftphost = ftp.galaktika.ru
* ftpdir = pub/support/galaktika/bug_fix/GAL910/DESCRIPTIONS
* issendmail = false (отправлять оповещение)
* isprintdebug = true (выводить отладочные сообщения)

Note that the accepted values for the option are "1", "yes", "true", and "on"

# Алгоритм
* Скачиваем реестр описаний файлов обновлений с FTP
* Из имени файла убираем версию
* Перекодируем в UTF8

# Установка

