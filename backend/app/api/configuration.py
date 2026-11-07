from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.models import SystemSetting
from app.schemas import ModelConfigOut, ModelConfigIn

router=APIRouter(prefix="/config",tags=['configuration'])
# 保存model
@router.put("/model",response_model=ModelConfigOut)
async def update_model_config(
            payload:ModelConfigIn,
            session:Session=Depends(get_session)
    ):
    # 获取参数之后，保存到 表中即可
    # 此处是两个字段，每一次需要保存 三条记录
    """
         key               value
       model_provider      deepseek|ollama
       model_name          deepseek-v4-flash
       model_base_url      url的值
    """
    settings=get_settings()
    if payload.provider=="deepseek":
        default_model=settings.deepseek_model
        default_base_url=settings.deepseek_base_url
    else:
        default_model=settings.ollama_model
        default_base_url=settings.ollama_base_url

    provider_row=session.get(SystemSetting,"model_provider")
    if provider_row:
        provider_row.value=payload.provider
    else:
        session.add(SystemSetting(
            key="model_provider",value=payload.provider
        ))

    name_row=session.get(SystemSetting,"model_name")
    model_name=payload.model or default_model
    if name_row:
        name_row.value=model_name
    else:
        session.add(SystemSetting(
            key="model_name",value=model_name
        ))

    url_row=session.get(SystemSetting,"model_base_url")
    base_url=payload.base_url or default_base_url
    if url_row:
        url_row.value=base_url
    else:
        session.add(SystemSetting(
            key="model_base_url",value=base_url
        ))
    session.commit()


    return ModelConfigOut(
        provider=payload.provider,
        model=model_name,
        base_url=base_url,
        configured=True
    )

# 查询model信息
@router.get("/model",response_model=ModelConfigOut)
async def get_model_config(
        session:Session=Depends(get_session)
):
    config_rows=session.query(SystemSetting).all()
    settings=get_settings()
    result_dict=dict()
    for item in config_rows:
        result_dict[item.key]=item.value
    provider=result_dict.get("model_provider",settings.model_provider)
    if provider=="deepseek":
        model=result_dict.get("model_name",settings.deepseek_model)
        base_url=result_dict.get("model_base_url",settings.deepseek_base_url)
    else:
        model = result_dict.get("model_name", settings.ollama_model)
        base_url = result_dict.get("model_base_url", settings.ollama_base_url)
    return ModelConfigOut(
        provider=provider,
        model=model,
        base_url=base_url,
        configured=True
    )
