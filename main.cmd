::%windir%\System32\cmd.exe "/K" C:\Anaconda3\Scripts\activate.bat C:\Anaconda3
@CALL "C:\Anaconda3\Scripts\activate.bat"

D:
cd D:\public\repo\GLOBAL_BGD_BREAKAGE_ALERTS

python D:\public\repo\GLOBAL_BGD_BREAKAGE_ALERTS\main.py

set /p choice= "Press to continue exit" 