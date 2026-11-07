from backend.app.database import engine,SessionLocal
import sys
from pathlib import Path
from sqlalchemy import inspect,text

def main()->None:
    print("数据库名称:",engine.url.database)
    print("数据库驱动：",engine.url.drivername)
    with SessionLocal() as session:
        result=session.execute(text("select 1")).scalar()
        print("select 1 结果：",result)
    table_names=inspect(engine).get_table_names()
    print("当前数据表：",table_names)
if __name__=="__main__":
    main()