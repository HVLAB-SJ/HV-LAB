@echo off
chcp 65001 > nul
echo.
set /p V="Version: "
git add .
git commit -m "v%V%"
git push origin master
git tag v%V%
git push origin v%V%
echo.
echo Done! Check https://github.com/HVLAB-SJ/HV-LAB/actions
pause 