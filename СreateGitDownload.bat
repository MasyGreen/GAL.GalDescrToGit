rem Загрузка FTP+отправка e-mail, фиксация и отправка GIT
%~d0
cd "%~p0"
@call cls
@ECHO OFF
CHCP 65001
CLS

rem Каталог с загруженными файлами
SET download_path=%~d0%~p0\Download\
@ECHO ***1N Download path = %download_path%

rem Переход в каталог Download
@ECHO ***2N Move to download
cd /D "%download_path%"

git init
git config --global user.name "****"
git config --global user.email ***@***.com
git config receive.denyCurrentBranch ignore
git config --global http.sslVerify false
git add .
git commit -m "init"
git remote -v
git remote rm origin
git remote add origingit ssh://*****.git
git remote -v
pause
