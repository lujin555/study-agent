"""评测集：针对知识库里的真实资料（docs/CS-Notes/）出题。

结构说明：
- question         用户会问的问题
- expected         期望回答里出现的关键词（用于判定「生成正确」）
- expected_source  该问题答案所在的源文档（检索评估时作为标注；None 表示资料里没有，测幻觉）

覆盖 13 份 CS-Notes 笔记：GPT 系列 / InstructGPT / OpenMMLab / 人体姿态估计 /
C++ OOP / STL map / C++ 面试题 / 费曼学习法 / 排序算法。
"""

EVAL_QUESTIONS = [
    # ===================== AI 大模型 =====================
    {
        "question": "GPT-1 是基于什么架构的？",
        "expected": "Transformer",
        "expected_source": "GPT123.md",
    },
    {
        "question": "InstructGPT 的训练流程包括哪几个步骤？",
        "expected": "奖励模型",
        "expected_source": "instructGPT.md",
    },
    {
        "question": "OpenMMLab 是基于什么深度学习框架的？",
        "expected": "PyTorch",
        "expected_source": "openmmlab.md",
    },
    {
        "question": "MMDetection 是用来做什么的？",
        "expected": "目标检测",
        "expected_source": "openmmlab.md",
    },
    {
        "question": "MMPose 是用来做什么的？",
        "expected": "姿态估计",
        "expected_source": "openmmlab.md",
    },
    # ===================== 人体姿态估计 =====================
    {
        "question": "人体姿态估计的输出是什么？",
        "expected": "关键点",
        "expected_source": "HumanPoseEstimation.md",
    },
    {
        "question": "常见的人脸、手势、人体分别有多少个关键点？",
        "expected": "68",
        "expected_source": "HumanPoseEstimation.md",
    },
    {
        "question": "DeepPose 是哪一年提出的？",
        "expected": "2014",
        "expected_source": "HumanPoseEstimation.md",
    },
    {
        "question": "HRNet 的核心思路是什么？",
        "expected": "高分辨率",
        "expected_source": "HumanPoseEstimation.md",
    },
    {
        "question": "OpenPose 属于哪一类姿态估计方法？",
        "expected": "自底向上",
        "expected_source": "HumanPoseEstimation.md",
    },
    {
        "question": "SMPL 人体参数化模型用多少个顶点建模？",
        "expected": "6890",
        "expected_source": "HumanPoseEstimation.md",
    },
    # ===================== C++ =====================
    {
        "question": "C++ 面向对象的三大特性是什么？",
        "expected": "封装",
        "expected_source": "OOP.md",
    },
    {
        "question": "std::map 的底层数据结构是什么？",
        "expected": "红黑树",
        "expected_source": "Maps_and_Multimaps.md",
    },
    {
        "question": "map 和 multimap 有什么区别？",
        "expected": "重复键",
        "expected_source": "Maps_and_Multimaps.md",
    },
    {
        "question": "为什么 C++ 类的成员函数要把声明和定义分开？",
        "expected": "隐藏实现",
        "expected_source": "interview_questions_cpp.md",
    },
    # ===================== 学习方法 =====================
    {
        "question": "费曼学习法可以简化为哪四个单词？",
        "expected": "Concept",
        "expected_source": "Feynman_Technique.md",
    },
    # ===================== 排序算法 =====================
    {
        "question": "选择排序有什么鲜明特点？",
        "expected": "输入无关",
        "expected_source": "sort.md",
    },
    {
        "question": "C++ 标准库的 sort 函数定义在哪个头文件里？",
        "expected": "algorithm",
        "expected_source": "stlsort.md",
    },
    # ===================== 资料里没有的（测幻觉，期望诚实拒答） =====================
    {
        "question": "计算机网络 TCP 三次握手的详细过程是什么？",
        "expected": None,
        "expected_source": None,
    },
    {
        "question": "Redis 有哪几种持久化方式？",
        "expected": None,
        "expected_source": None,
    },
    {
        "question": "法国大革命发生在哪一年？",
        "expected": None,
        "expected_source": None,
    },
]
