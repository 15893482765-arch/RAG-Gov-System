from pathlib import Path
from app.services.document_service import extract_pages
import sys
from pathlib import Path

from scripts.chek_deepseek import BACKEND_ROOT

BACKEND_ROOT=Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0,str(BACKEND_ROOT))
from app.services.chunking import _windows,split_policy_text
from app.services.document_service import extract_pages
# def main()->None:
#     sample_path=BACKEND_ROOT/"sample_data"/"policy_parse.txt"
#     sample_path.parent.mkdir(parents=True,exist_ok=True)
#     sample_path.write_text(
#         "第一章 申请条件\n"
#         "青年人才租房补贴申请人应符合年龄、就业、社保、租房状态等条件。\n"
#         "第二章 办理材料\n"
#         "申请人需要提交身份证、劳动合同、社保缴纳记录和租房材料。\n",
#         encoding="utf-8",
#     )
#     print("一、解析 TXT 文件")
#     pages=extract_pages(sample_path)
#     print("页数：",len(pages))
#     print("第一页页码：",pages[0][0])
#     print("第一页文本：")
#     print(pages[0][1])
#     print("\n二、滑动窗口切分")
#     window_text = "申请条件包括年龄要求、就业要求、社保要求和租房状态要求。办理时需要提交身份证、劳动合同和租房材料。"
#     for index,chunk in enumerate(_windows(window_text,size=30,overlap=8),start=1):
#         print(f"窗口{index}:{chunk}")
#     print("\n三、父子分块")
#     long_text = "第一章 申请条件\n" + (
#             "青年人才租房补贴申请人应符合年龄、就业、社保、租房状态等条件。"
#             * 3
#     )
#     chunks=split_policy_text(
#         long_text,
#         parent_size=100,
#         child_size=70,
#         child_overlap=10
#     )
#     parents=[chunk for chunk in chunks if chunk.is_parent]
#     children=[chunk for chunk in chunks if not chunk.is_parent]
#     print("总块数：", len(chunks))
#     print("父块数：", len(parents))
#     print("子块数：", len(children))
#     print("第一个章节：", chunks[0].section)
#     print("第一个子块父索引：", children[0].parent_index if children else None)
#     print("\n四、解析文件后分块")
#     file_chunks=[]
#     for page,text in pages:
#         file_chunks.extend(
#             split_policy_text(
#                 text,
#                 page=page,
#                 parent_size=120,
#                 child_size=50,
#                 child_overlap=10
#             )
#         )
#     print("文件分块数：", len(file_chunks))
#     print("前 5 个分块：")
#     for chunk in file_chunks[:5]:
#         print(
#             {
#                 "section": chunk.section,
#                 "page": chunk.page,
#                 "is_parent": chunk.is_parent,
#                 "parent_index": chunk.parent_index,
#             }
#         )
def check_split_policy_text():
    sample_data=Path("../sample_data/星河市数字政务服务和政策兑现便利化实施意见.pdf")
    pages=extract_pages(sample_data)
    for index,pageTuple in enumerate(pages):
        page=pageTuple[0]
        content=pageTuple[1]
        drafts=split_policy_text(content,page,1200,100)
        parent=[chunk for chunk in drafts if chunk.is_parent]
        child=[chunk for chunk in drafts if not chunk.is_parent]
        print(f"第{page}页")
        print("总块数：", len(drafts))
        print("父块数：", len(parent))
        print("子块数：", len(child))
        print("以下是当前页切分的情况:")
        print(drafts)


if __name__=="__main__":
    check_split_policy_text()
    # list=[
    #     Path("../sample_data/星河市数字政务服务和政策兑现便利化实施意见.pdf"),
    #     Path("../sample_data/星河市数字政务服务和政策兑现便利化实施意见.docx"),
    #     Path("../sample_data/星河市小微企业数字化补贴细则.txt"),
    # ]
    # for sample_path in list:
    #     pages=extract_pages(sample_path)
    #     # print(pages)
    #     print("页数：",len(pages))
    #     print("第一页页码：",pages[0][0])
    #     print("第一页文本：")
    #     print(pages[0][1])