@echo off
echo Starting HTML combination...
echo. > ../new_combined.html

for /r %%f in (*.html) do (
   echo Adding: %%~nxf
   echo # Start File: %%~nxf >> ../new_combined.html
   type "%%f" >> ../new_combined.html
   echo # End File: %%~nxf >> ../new_combined.html
)

echo.
echo Finished! Check new_combined.html
pause