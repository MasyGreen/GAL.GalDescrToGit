rem Загрузка FTP+отправка e-mail, фиксация и отправка GIT
%~d0
cd "%~p0"
@call cls
@ECHO OFF
CHCP 65001
CLS

@ECHO ***1N Start download/e-mail

rem Запуск функционала: загрузка FTP+отправка e-mail
py -3.8 "GalDescrToGit.py"

rem Каталог с загруженными файлами
SET download_path=%~d0%~p0\Download\
@ECHO ***2N Download path = %download_path%

rem Формирование comment для GIT
set DD=%date:~0,2%
set MM=%date:~3,2%
set YYYY=%date:~6,4%
set DT=_%YYYY%%MM%%DD%

SET DEBUGDATE=%DT%
@ECHO ***3N comment = %DEBUGDATE%

rem Переход в каталог Download
@ECHO ***4N Move to download
cd /D "%download_path%"

@ECHO ***5N Формирование GIT
git add .
git commit -m "%DT%"

@ECHO ***6N Отправка GIT
git push origin master
rem ПРИ ПРОБЛЕМАХ git push -f origin master
rem pause