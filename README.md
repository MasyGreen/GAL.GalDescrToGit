# Point/Назначение
Скачивание патчей обновлений для Галактики ERP 9.1 с ftp.galaktika.ru

Download patches description for Galaktika ERP 9.1 from ftp.galaktika.ru

Pyton 3.10

# Settings/Настройки config.py

* mailpassword = open key e-mail sender
* mailsmtpserver = smtp server name (smtp.gmail.com)
* mailsmtpport = smtp port (587)
* mailfrom = sender e-mail
* mailto = recipient e-mail
* mailadditiontext = some comment (html style)
* ftphost = ftp adr (ftp.galaktika.ru)
* ftpdir = ftp path (pub/support/galaktika/bug_fix/GAL910/DESCRIPTIONS)
* issendmail = send email (false)
* isincludenewinmail = add in e-mail description for New Issue from last update file 
* isprintdebug = show debug message (true)

***Note that the accepted values for the option are "1", "yes", "true", and "on"***

# Step/Шаги
Work foldr Download
* Delete from work folder all *.txt file/удалить все файлы *.txt из рабочего каталога
* Download file from FTP/Скачиваем реестр описаний файлов обновлений с FTP
* Clear file name/Из имени файла убираем версию
* Decode to UTF8/Перекодируем в UTF8

# Установка

