@echo off
REM DFS Behavioral Parser - Windows Setup Script

echo ========================================
echo DFS Behavioral Parser Setup
echo ========================================
echo.

REM Create directory structure
echo Creating directory structure...
mkdir C:\Users\ebgne\dfs-behavioral-parser
mkdir C:\Users\ebgne\dfs-behavioral-parser\docs
mkdir C:\Users\ebgne\dfs-behavioral-parser\docs\design
mkdir C:\Users\ebgne\dfs-behavioral-parser\docs\future
mkdir C:\Users\ebgne\dfs-behavioral-parser\docs\architecture

echo.
echo Directory structure created!
echo.
echo Next steps:
echo 1. Copy all files from the 'docs' folder to: C:\Users\ebgne\dfs-behavioral-parser\docs
echo 2. Open Claude Code desktop app
echo 3. Open folder: C:\Users\ebgne\dfs-behavioral-parser
echo 4. Copy the prompt from CLAUDE_CODE_PROMPT.md
echo 5. Paste into Claude Code and let it build!
echo.
echo ========================================
echo Setup complete!
echo ========================================

pause
