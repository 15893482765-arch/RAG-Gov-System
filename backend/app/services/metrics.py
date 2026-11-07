import re


def recall_at_k(expected:list[str],retrieved:list[str],k:int)->float:
    if not expected:
        return 1
    return len(set(expected) & set(retrieved[:k])) / len(set(expected))

def reciprocal_rank(excepted:list[str],retrieved:list[str])->float:
    excepted_set=set(excepted)
    for rank,chunk_id in enumerate(retrieved,start=1):
        if chunk_id in excepted_set:
            return 1/ rank
    return 0

def citation_precision(cited:list[str],retrieved:list[str])->float:
    if not cited:
        return 0.0
    return len(set(cited) & set(retrieved)) / len(retrieved)

def extract_facts(text:str)->set[str]:
    return set(
        re.findall(
            r"(?:%|万元|元|天|日|个月|年)?|\d{4}年\d{1,2}月\d{1,2}日\d+(?:\.\d+)?",
            text,
        )
    )

def factual_accuracy(reference:str,answer:str)->float:
    s1=extract_facts(reference)
    if not s1:
        return 1
    s2=extract_facts(answer)
    return len(s1 & s2)/len(s1)


def citation_coverage(answer:str)->float:
    list1=re.split(r"[。！？\n]+",answer)
    list1=[line.strip() for line in list1 if line.strip()]
    factual=[
        line for line in list1 if re.search(r"\d|条件|材料|期限|标准|应当|不得|可以|补贴|申请",line)
    ]
    if not factual:
        return 1
    supported=[
        line for line in factual if re.search(r"\[\d+]", line)

    ]
    return len(supported)/len(factual)
