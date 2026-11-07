from typing import Any


def reciprocal_rank_fusion(
        result_list:list[list[dict[str,Any]]],
        k:int=60
)->list[dict[str,Any]]:
    # fused 这个字典中  只有一个k和一个v ，不同的k 对应不同v
    fused:dict[str,dict[str,Any]]={}
    for results in result_list:
        for rank,item in enumerate(results,start=1):
            chunk_id=item['chunk_id']
            # 如果chunk_id 不在字典列表中，说明是第一次处理
            if chunk_id not in fused:
                fused[chunk_id]={**item,"rrf_score":0.0,"source":list()}
            fused[chunk_id]['rrf_score']+=1/(k+rank)
            fused[chunk_id]['source'].append(item.get("source","unknown"))
    # 此时的字典依然成型
    print(fused)
    print("-----------------------------")
    print(fused.values())
    print("=============================")
    a=sorted(fused.values(),key=lambda item:item['rrf_score'],reverse=True)
    print(a)
    return a
import math


def normalize_logit(value: float) -> float:
    return 1 / (1 + math.exp(-max(-30, min(30, value))))

from typing import Any
def filter_evidence(evidence:list[dict[str,Any]],min_score:float)->list[dict]:
    return[
        item for item in evidence if float(item.get("evidence_score",0))>=min_score

    ]
import re
# 正则：匹配文本里的引用标记，例如 [1] [2] [10]，捕获括号里面的数字
CITATION_PATTERN = re.compile(r"\[(\d+)\]")
def validate_citations(answer:str,evidence:list[dict])->tuple[str,list[int]]:
    """
      校验回答里的角标引用标记 [数字]，过滤无效引用；返回清理后的回答 + 合法引用编号列表
      :param answer: LLM输出的回答文本，里面带有 [1][2] 这类引用标记
      :param evidence: RAG检索出来的证据片段列表，长度N，合法引用编号是 1~N
      :return: (清理后的回答文本, 真正有效的引用id有序列表)
      """
    #提取answer中的序号
    r1=CITATION_PATTERN.findall(answer)
    cited=set()
    for value in r1:
        cited.add(int(value))
    print("--------------")
    print(cited)
    #根据证据中的list长度，获取一个set集合
    valid=set()
    # 合法引用集合：evidence一共多少条，合法编号就是 {1,2,3,...,len(evidence)}
    for i in range(1,len(evidence)+1):
        valid.add(i)
    print("--------------")
    print(valid)
    # 从answer文本中提取所有中括号里面的数字，转成整数集合
    # cited={int(value) for value in CITATION_PATTERN.findall(answer)}
    #算出无效引用：回答中标注了，但不在合法编号范围内的数字
    invalid=cited-valid
    # 如果存在无效引用，把文本里对应的[x]全部删除掉
    if invalid:
        for value in invalid:
            answer=answer.replace(f"[{value}]","")
    # 返回：清理完的回答，同时取【即被引用，又合法】的编号，排序后返回list
    return answer,sorted(cited & valid)
if __name__ == '__main__':
    validate_citations('向量数据库[2]，大模型幻觉[4]，Reranker[3]',[{},{},{},{}])

    set1=list({1,2,3,5,4})
    print("set1",set1)