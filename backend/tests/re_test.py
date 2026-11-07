import re

test_doc = """
为落实相关工作，特制定本管理办法。

第一章 总体规定
本章节用于说明制度适用范围与基本原则。
本办法适用于公司各业务部门。

一、适用对象
全体在职员工均需要遵守本管理办法。

二. 时间要求
本办法自发布之日起正式生效。

1. 职责划分
行政部门负责制度宣贯与监督执行。

2、违规处理
出现违规行为，将按照公司规定予以处置。

第三章 附则
本办法由行政部负责解释。
"""
HEADING_PATTERN = re.compile(
    r"(?m)^([第][一二三四五六七八九十百]+[章节条]\s*.*|[一二三四五六七八九十]+[、.]\s*.*|\d+[.、]\s*.*)$"
)
print("==1. finditer：获取全部标题匹配对象（matches） ====================")
matches=list(HEADING_PATTERN.finditer(test_doc))
for idx,m in enumerate(matches):
    print(f"\nmatch[{idx}]:")
    print(f"  span() = {m.span()}")
    print(f"  start()= {m.start()}, end()={m.end()}")
    print(f"  group(0)={repr(m.group(0))}")
    print(f"  group(1)={repr(m.group(1))}")
print("\n=== 2. fullmatch：逐行判断某一行是不是标题 ====================")
lines=test_doc.splitlines()
for line in lines:
    res=HEADING_PATTERN.fullmatch(line)
    if res:
        print(f"【识别为标题行】 {repr(line)} → group1={repr(res.group(1))}")
print("\n==3. search：演示search（注意：不推荐用来识别整行标题，做对比） ====================")
# search只要字符串里面存在片段就命中，不需要整行匹配
demo_line="随便写的文字 一、这里混了一个序号 后面继续文字"
s_res=HEADING_PATTERN.search(demo_line)
print(f"demo_line={repr(demo_line)}")
print(f"search结果:{s_res}")
print("\n=== 4. 模拟 split_policy_text 内部逻辑：切分 sections（标题+正文片段） ====================")
sections=[]
if not matches:
    sections=[(None,test_doc)]
else:
    # 提取标题之前的前置内容
    if matches[0].start()>0:
        pre_text=test_doc[:matches[0].start()]
        sections.append((None,pre_text))
    for index,match in enumerate(matches):
        if index+1 <len(matches):
            next_title_start=matches[index+1].start()
        else:
            next_title_start=len(test_doc)
        title=match.group(0).strip()
        body_chunk=test_doc[match.start():next_title_start]
        sections.append((title,body_chunk))
for i,(sec_title,sec_body) in enumerate(sections):
    print(f"\n==== section[{i}] 标题={repr(sec_title)} ====")
    print(f"section正文片段:\n{sec_body}")

