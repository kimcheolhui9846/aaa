# Validation commands by language

| Language | Debug-output search | Lint / static check |
|---|---|---|
| Python | `grep -rnE "print\(|breakpoint\(|pdb\.set_trace|TODO|FIXME" --include=*.py .` | `ruff check .` (if installed), `python -m py_compile <files>` |
| C++ | `grep -rnE "cerr|printf\(\"DEBUG|TODO|FIXME" --include=*.cpp .` | `g++ -std=c++17 -Wall -Wextra -fsyntax-only <files>` |
| Java | `grep -rnE "System\.(out|err)\.print|TODO|FIXME" --include=*.java .` | `javac -Xlint:all *.java` |
| JavaScript | `grep -rnE "console\.(log|debug)|debugger|TODO|FIXME" --include=*.js .` | `node --check <file>` |

On Windows PowerShell use `Select-String -Path <glob> -Pattern '<regex>'` instead of `grep`.
`print` is legitimate when it produces the required output: check each hit, do not delete blindly.
