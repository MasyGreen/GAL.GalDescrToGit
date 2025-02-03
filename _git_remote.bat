@ECHO =====================Attention!!!============================
@ECHO Remote add
@ECHO =====================Attention!!!============================
CHCP 65001
pause
@ECHO =====================Список существующих============================
git remote -v
@ECHO =====================Удаление============================
git remote rm origingit
git remote rm originbit
git remote rm origin
git remote -v
@ECHO =====================Добавление============================
git remote add origingit git@github.com:MasyGreen/GAL.GalDescrToGit.git
git remote add originbit git@bitbucket.org:masygreen/GAL.GalDescrToGit.git
git remote add origin git@192.168.177.75:masygreen/GAL.GalDescrToGit.git
@ECHO =====================Список существующих============================
git remote -v
pause