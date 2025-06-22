@echo off
set /p V="버전: "
git add .
git commit -m "v%V%"
git push
git tag v%V%
git push origin v%V%
echo Done! Check https://github.com/HVLAB-SJ/HV-LAB/actions
pause 