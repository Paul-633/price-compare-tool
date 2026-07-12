@echo off
REM ============================================
REM 电商价格采集对比工具 - 打包脚本
REM ============================================

echo [1/5] 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist price_compare_tool.egg-info rmdir /s /q price_compare_tool.egg-info

echo [2/5] 安装构建依赖...
pip install build wheel --quiet

echo [3/5] 构建分发包...
python setup.py sdist bdist_wheel

echo [4/5] 检查构建结果...
dir dist

echo [5/5] 打包完成！
echo.
echo 分发包位于 dist/ 目录：
echo   - .tar.gz  (源码包)
echo   - .whl     (wheel包)
echo.
echo 安装命令：pip install dist/price_compare_tool-1.2.0-py3-none-any.whl
echo.
pause
