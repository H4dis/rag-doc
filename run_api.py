import sys
from pathlib import Path

# اضافه کردن مسیر src
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )