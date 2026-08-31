EVAL_QUESTIONS = [
    {
        "question": "周杰伦的生日是什么时候？",
        "expected": "1979",           # 期望回答里出现的关键词
        "expected_source": "test.pdf",
    },
    {
        "question": "周杰伦获得过哪些重要奖项？",
        "expected": "金曲奖",
        "expected_source": "test.pdf",
    },
    {
        "question": "坚持和行动有什么关系？",      # 跨文档/名言
        "expected": "行动",
        "expected_source": "xx.docx",
    },
    {
        "question": "计算机网络 TCP 三次握手",     # 资料里没有的！测幻觉
        "expected": None,              # 期望：诚实说"没有相关内容"，不许编
        "expected_source": None,
    },
    # ===== 补充：资料里有的（test.pdf 周杰伦） =====
    {
        "question": "周杰伦的妻子叫什么名字？",
        "expected": "昆凌",
        "expected_source": "test.pdf",
    },
    {
        "question": "周杰伦一共获得过多少座金曲奖？",
        "expected": "15",
        "expected_source": "test.pdf",
    },
    {
        "question": "周杰伦在哪一年成为首位在台北大巨蛋开演唱会的歌手？",
        "expected": "2024",
        "expected_source": "test.pdf",
    },
    {
        "question": "周杰伦患有哪种疾病？",
        "expected": "僵直性脊椎炎",
        "expected_source": "test.pdf",
    },
    {
        "question": "周杰伦的母亲叫什么名字？",
        "expected": "叶惠美",
        "expected_source": "test.pdf",
    },
    {
        "question": "周杰伦 2014 年担任了什么形象大使？",
        "expected": "禁毒",
        "expected_source": "test.pdf",
    },
    {
        "question": "周杰伦的音乐风格有什么特点？",
        "expected": "中国风",
        "expected_source": "test.pdf",
    },
    # ===== 补充：资料里有的（xx.docx 名言） =====
    {
        "question": "天才是百分之一的灵感加百分之九十九的汗水，这句话是谁说的？",
        "expected": "爱迪生",
        "expected_source": "xx.docx",
    },
    {
        "question": "资料里'想，全是问题'的下一句是什么？",
        "expected": "做，才有答案",
        "expected_source": "xx.docx",
    },
    {
        "question": "关于'勇气'，我的资料里有什么名言？",
        "expected": "勇气",
        "expected_source": "xx.docx",
    },
    # ===== 补充：资料里没有的（继续测幻觉） =====
    {
        "question": "法国大革命发生在哪一年？",
        "expected": None,
        "expected_source": None,
    },
    {
        "question": "量子力学的基本原理是什么？",
        "expected": None,
        "expected_source": None,
    },
]
