import sys
from pathlib import Path
BACKEND_ROOT=Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0,str(BACKEND_ROOT))
from app.database import init_database
def main()->None:
    init_database()
    print("数据库初始化完成")
if __name__=="__main__":
    main()