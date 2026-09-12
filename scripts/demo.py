"""一键跑通全流程：生成模拟数据 -> 生成完整分析报告。等同于 `bda demo`。"""

from bdatools.cli import main

if __name__ == "__main__":
    main(["demo", "--out", "outputs"])
