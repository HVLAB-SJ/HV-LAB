@echo off
echo Quick GitHub Update
echo ===================
echo.
git add .
git commit -m "Update"
git push origin master
echo.
echo Done!
pause 