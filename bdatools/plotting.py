"""绘图公共辅助：统一 matplotlib 样式与中文显示。"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无界面环境也能出图


def setup_style() -> None:
    """设置图表样式，优先使用中文字体，避免中文乱码。"""
    import matplotlib.pyplot as plt

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "PingFang SC",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "Arial Unicode MS",
        "DejaVu Sans",  # 兜底：保证英文可显示
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3


def save_chart(fig, path: str | Path) -> Path:
    """保存图表到指定路径并关闭 figure，返回保存路径。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    matplotlib.pyplot.close(fig)
    return path
