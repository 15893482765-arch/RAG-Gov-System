import asyncio
import sys
from pathlib import Path
BACKEND_ROOT=Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0,str(BACKEND_ROOT))
from backend.app.services.model_fectory import create_chat_model,invoke_text
async def main()->None:
    model=create_chat_model(0)
    answer,usage=await invoke_text(
        model,
        "请用一句话回答：RAG系统的作用是什么？"
    )
    print("模型回答：")
    print(answer)
    print("Token用量：")
    print(usage)

if __name__=="__main__":
    asyncio.run(main())