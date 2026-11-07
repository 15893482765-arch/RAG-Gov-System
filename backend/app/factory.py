from fastapi import FastAPI
from app.api import document, chat, configuration, evaluation

from app.config import get_settings
settings=get_settings()
def create_app()->FastAPI:

    app=FastAPI(
        title=settings.app_name,
        description="FastAPI+LangChain政策知识库问答系统",
        version="1.0.0"
    )
    for router in (document.router,chat.router,configuration.router,evaluation.router):
        app.include_router(router, prefix=settings.api_prefix)

    @app.get("/")
    async def root():
        return{
            "name":settings.app_name,
            "docs":"/docs",
            "message":"服务已启动"
        }
    return app

