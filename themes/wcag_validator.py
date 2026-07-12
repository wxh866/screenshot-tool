"""WCAG对比度验证器 - 从现有项目theme_colors.py移植"""
from typing import Tuple, List


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """十六进制颜色转RGB"""
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """RGB转十六进制颜色"""
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def relative_luminance(hex_color: str) -> float:
    """计算相对亮度（WCAG 2.1标准）"""
    r, g, b = hex_to_rgb(hex_color)
    rsrgb = [c / 255.0 for c in (r, g, b)]
    linear = []
    for val in rsrgb:
        if val <= 0.03928:
            linear.append(val / 12.92)
        else:
            linear.append(((val + 0.055) / 1.055) ** 2.4)
    r_lin, g_lin, b_lin = linear
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def calc_contrast(color1: str, color2: str) -> float:
    """计算WCAG对比度比值

    返回值 >= 4.5 表示通过AA标准（常规文字）
    >= 3.0 表示通过AA大文字标准
    """
    l1 = relative_luminance(color1)
    l2 = relative_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    if darker == 0:
        return float('inf')
    return (lighter + 0.05) / (darker + 0.05)


def check_contrast(fg: str, bg: str, level: str = "AA",
                   size: str = "normal") -> Tuple[bool, float]:
    """检查前景色与背景色的对比度是否达标

    Args:
        fg: 前景色（文字色）
        bg: 背景色
        level: "AA" (4.5:1) 或 "AAA" (7:1)
        size: "normal" (>=14px常规) 或 "large" (>=18px大字)

    Returns:
        (是否达标, 实际对比度值)
    """
    ratio = calc_contrast(fg, bg)
    if size == "large":
        threshold = 3.0
    else:
        threshold = {"AA": 4.5, "AAA": 7.0}.get(level, 4.5)
    return ratio >= threshold, ratio


def lighten(hex_color: str, factor: float = 0.2) -> str:
    """使颜色变亮"""
    r, g, b = [min(255, int(c + (255 - c) * factor)) for c in hex_to_rgb(hex_color)]
    return rgb_to_hex(r, g, b)


def darken(hex_color: str, factor: float = 0.2) -> str:
    """使颜色变暗"""
    r, g, b = [max(0, int(c * (1 - factor))) for c in hex_to_rgb(hex_color)]
    return rgb_to_hex(r, g, b)


def validate_theme(theme_data: dict) -> List[str]:
    """验证主题颜色的一致性规则

    检查项：
        1. 文字/背景对比度是否达标（WCAG AA）
        2. 边框色与背景色是否有足够区分
    """
    issues = []
    colors = theme_data.get("colors", theme_data)

    # 对比度检查
    bg_card = colors.get("background", {}).get("card", "")
    bg_elev = colors.get("background", {}).get("elevated", "")
    txt_primary = colors.get("text", {}).get("primary", "")
    txt_secondary = colors.get("text", {}).get("secondary", "")
    txt_tertiary = colors.get("text", {}).get("tertiary", "")

    checks = [
        ("主文字-卡片背景", txt_primary, bg_card, 4.5),
        ("次文字-卡片背景", txt_secondary, bg_card, 4.5),
        ("辅助文字-卡片背景", txt_tertiary, bg_card, 3.0),
    ]

    for label, fg, bg, required in checks:
        if not fg or not bg or fg.startswith('rgba') or bg.startswith('rgba'):
            continue
        ok, ratio = check_contrast(fg, bg)
        if not ok:
            issues.append(f"[对比度不足] {label}: {ratio:.1f}:1 < 要求 {required}:1")

    # 边框可见性
    border = colors.get("border", {}).get("default", "")
    border_strong = colors.get("border", {}).get("strong", "")
    for label, bd, bg_ref in [("默认边框-卡片背景", border, bg_card),
                               ("强调边框-卡片背景", border_strong, bg_card)]:
        if bd and bg_ref and bd.lower() == bg_ref.lower():
            issues.append(f"[边框不可见] {label}: 边框色与背景色相同")

    return issues


class WCAGValidator:
    """WCAG 2.1验证器类"""

    AA_NORMAL = 4.5
    AA_LARGE = 3.0
    AAA_NORMAL = 7.0
    AAA_LARGE = 4.5

    @classmethod
    def validate(cls, fg_color: str, bg_color: str,
                 is_large_text: bool = False) -> Tuple[bool, float]:
        """验证颜色组合是否符合WCAG标准"""
        return check_contrast(fg_color, bg_color,
                              "AA" if not is_large_text else "AA",
                              "large" if is_large_text else "normal")

    @classmethod
    def find_valid_fg(cls, bg_color: str, is_large_text: bool = False) -> str:
        """为背景色找到符合WCAG标准的前景色"""
        candidates = ["#FFFFFF", "#000000", "#202020", "#F0F0F0"]
        for fg in candidates:
            is_valid, ratio = cls.validate(fg, bg_color, is_large_text)
            if is_valid:
                return fg
        black_ratio = calc_contrast("#000000", bg_color)
        white_ratio = calc_contrast("#FFFFFF", bg_color)
        return "#000000" if black_ratio > white_ratio else "#FFFFFF"
