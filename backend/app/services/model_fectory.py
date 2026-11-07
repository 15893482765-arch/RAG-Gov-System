from typing import Any
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from ..config import Settings,get_settings
from ..database import SessionLocal
from ..models import SystemSetting


def create_chat_model(
    temperature: float = 0,
    settings: Settings | None = None,
) -> BaseChatModel:
    settings = settings or get_settings()
    model_name=read_model_setting("model_provider",settings.model_provider)
    if model_name=="deepseek":
            if not settings.deepseek_api_key:
                raise RuntimeError("DEEPSEEK_API_KEY没有配置")
            model= init_chat_model(
                model=read_model_setting("model_name",settings.deepseek_model),
                model_provider="openai",
                api_key=settings.deepseek_api_key,
                base_url=read_model_setting("model_name",settings.deepseek_base_url),
                temperature=temperature
            )
    else:
        from langchain_ollama import ChatOllama
        model=ChatOllama(
            model=read_model_setting("model_name",settings.ollama_model),
            base_url=read_model_setting("model_base_url",settings.ollama_base_url),
            temperature=temperature,
            num_gpu=0
        )
    return model

async def invoke_text(model:BaseChatModel,prompt:str):
    response=await model.ainvoke(prompt)
    if not isinstance(response,AIMessage):
        raise TypeError(f"聊天模型返回了不支持的消息类型,{type(response).__name__}")
    return response.text,dict(response.usage_metadata or {})


# 给定一个key值，通过key值去数据库查询对应的value值，如果没有查询到，返回默认值
def read_model_setting(key:str,default:str)->str:
    # 此处的session也可以通过接口 传递过来
    with SessionLocal() as session:
        systemSetting=session.get(SystemSetting,key)
        if systemSetting and systemSetting.value:
            return systemSetting.value
        return default
