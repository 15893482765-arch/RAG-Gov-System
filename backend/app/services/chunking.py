from dataclasses import dataclass,field
import re


HEADING_PATTERN = re.compile(
    r"(?m)^([第][一二三四五六七八九十百]+[章节条]\s*.*|[一二三四五六七八九十]+[、.]\s*.*|\d+[.、]\s*.*)$"
)
@dataclass
class ChunkDraft:
    content:str
    section:str|None
    page:int|None
    is_parent:bool
    parent_index:int|None=None
    metadata:dict=field(default_factory=dict)
def _windows(text: str, size: int, overlap: int) -> list[str]:
    #
    text = text.strip()
    if not text:
        return []
    #保存切好的块
    chunks: list[str] = []
    #start 当前块的起始下标
    start = 0
    while start < len(text):
        # end：理论窗口结束位置，不能超过文本总长度
        end = min(len(text), start + size)
        if end < len(text):
            # 从右往左找标点，返回下标；找不到返回 -1
            # max(...) 获取区间内最靠右的那个标点位置
            punctuation = max(text.rfind(mark, start, end) for mark in "。；！？\n")
            # 标点必须落在窗口后半段才做截断。 目的：避免窗口刚开头遇到一个句号，把块切得特别短；只有过半之后遇到句号，才在此处切。
            if punctuation > start + size // 2:
                # 把结束位置挪到标点后面，把句号包含进当前块。
                end = punctuation + 1
        # 举例：size=500，从 start 开始 500 字符位置之前，如果在后 250 字符出现句号，就直接在句号切分，而不是硬切 500 字符。
        chunks.append(text[start:end].strip())
        # 已经读到文本末尾，退出循环。
        if end >= len(text):
            break
        #计算下一个块的起始位置
        start = max(start + 1, end - overlap)
    return [chunk for chunk in chunks if chunk]
def _windows2(text:str,size:int,overlap:int)->list[str]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter=RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    chunks=text_splitter.split_text(text)
    return chunks
def split_policy_text(
    text: str,
    page: int | None = None,
    parent_size: int = 1200,
    child_size: int = 420,
    child_overlap: int = 80,
) -> list[ChunkDraft]:
    match_list = list(HEADING_PATTERN.finditer(text))
    if not match_list:
        sections = [(None, text)]
    else:
        sections = []
        if match_list[0].start() > 0:
            content = text[0:match_list[0].start()]
            sections.append((None, content))
        for index, match in enumerate(match_list):
            if index + 1 < len(match_list):
                next_title_start = match_list[index + 1].start()
            else:
                next_title_start = len(text)
            content = text[match.start():next_title_start]
            sections.append((match.group(1), content))

    # 第一层循环，获取章节以及章节的全部内容
    drafts: list[ChunkDraft] = []
    for i, (sec_title, sec_body) in enumerate(sections):
        # 通过_windows 方法进行章节内容的切分
        for j, draft in enumerate(_windows(sec_body, parent_size, 100),start=1):
            # 整个章节的内容切割两次，第一次是按照1200字，第二次是按照420个字切分
            parent_index=len(drafts)
            drafts.append(ChunkDraft(
                content=draft,
                section=sec_title,
                page=page,
                is_parent=True
            ))
            # 根据draft 继续切分
            for k, child_draft in enumerate(_windows(draft, child_size, child_overlap)):
                drafts.append(ChunkDraft(
                    content=child_draft,
                    section=sec_title,
                    page=page,
                    is_parent=False,
                    parent_index=parent_index
                ))

    return drafts












