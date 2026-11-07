import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT=Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0,str(BACKEND_ROOT))

from app.database import Base,SessionLocal
from app.models import DocumentStatus,PolicyDocument
from app.schemas import DocumentOut
def check_schema()->None:
    document=PolicyDocument(
        id="demo-document-id",
        filename="policy.txt.txt",
        stored_path="data/uploads/policy.txt.txt",
        content_type="text/plain",
        topic="人才政策",
        effective_date=None,
        status=DocumentStatus.ready,
        chunk_count=0,
        index_version=1,
        created_at=datetime.now(),
    )
    #ORM对象-》pydantic模型转换
    output=DocumentOut.model_validate(document)
    print("Schema转换结果：")
    print(output)
"""
检查 SQLAlchemy Base.metadata 是否成功收集到所有 ORM 模型数据表
用来排查经典问题：Base.metadata.create_all() 建不出表。

from app import models # noqa: F401
导入 models 模块，目的：加载所有模型类（PolicyDocument 等）到内存
SQLAlchemy 原理：
只有当 class PolicyDocument(...) 代码被 Python 执行，模型才会注册进 Base.metadata
如果模型文件从未导入，metadata 不知道存在这张表，建表会直接跳过！
# noqa: F401
Flake8/Pylint 静态检查标记：消除「导入了但是没使用」的警告。
我们只是触发模块加载，不使用里面的变量，必然报 F401，注释屏蔽告警。

Base.metadata.tables
metadata：元数据容器，保存所有已扫描数据表信息
.tables 字典：{表名: Table对象}
.keys()：打印所有识别到的数据表名称

"""
def check_metadate()->None:
    from app import  models # noqa
    print("ORM注册表：")
    print(Base.metadata.tables.keys())
# 作用：打印当前应用中所有以 /api 开头的接口路径，用来验证路由是否成功注册到 FastAPI 实例。
def check_routes()->None:
    import main
    routes=[route.path for route in main.app.routes if route.path.startswith("/api")]
    print("API路由：")
    print(routes)
# 直接连接数据库，查询 policy_documents 表全部数据，打印核心字段，快速查看数据库内文档状态
def check_database_rows()->None:
    with SessionLocal() as session:
        rows=list(session.scalars(select(PolicyDocument)).all())
        print("文档记录：")
        print([
            (row.filename,row.topic,row.status.value,row.chunk_count) for row in rows
        ])
def main_script()->None:
    check_schema()
    print()
    check_metadate()
    print()
    check_routes()
    print()
    check_database_rows()
if __name__=="__main__":
    main_script()