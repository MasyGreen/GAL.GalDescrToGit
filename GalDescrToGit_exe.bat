@ECHO OFF
CHCP 65001
CLS
SET PYNAME=GalDescrToGit
rmdir "build" /s /q
if exist %PYNAME%.exe del %PYNAME%.exe
if exist *.log del *.log
if exist *.spec del *.spec
pyinstaller -F -i "Icon.ico" %PYNAME%.py
if exist *.log del *.log
if exist *.spec del *.spec
rmdir "build" /s /q