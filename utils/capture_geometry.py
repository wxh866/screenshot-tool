"""截图几何工具 — DPI 缩放 / 多显示器 / 越界裁剪

集中处理「UI 逻辑坐标 ↔ 屏幕设备像素」的换算，避免把缩放细节散落在各捕获器里。
参考实现：
- Flameshot (flameshot-org/flameshot)：分数缩放下必须用 devicePixelRatio 把选区换算成
  设备像素再抓取，否则 125%/150% 缩放下区域错位（issue #564 / #4171）。
- ShareX：多显示器下按坐标落在哪块屏幕决定抓取来源。
"""

from typing import List, NamedTuple


class ScreenGeom(NamedTuple):
    """单块屏幕的几何描述（逻辑坐标 + 设备像素比）"""
    x: int
    y: int
    width: int
    height: int
    dpr: float = 1.0


def device_rect(logical_rect, dpr):
    """逻辑坐标（UI 像素）→ 设备像素坐标（QScreen.grabWindow 使用）。

    Args:
        logical_rect: (x, y, w, h) 逻辑像素
        dpr: 该屏幕的 devicePixelRatio
    Returns:
        (x, y, w, h) 设备像素（四舍五入）
    """
    x, y, w, h = logical_rect
    return (
        round(x * dpr),
        round(y * dpr),
        round(w * dpr),
        round(h * dpr),
    )


def clamp_rect_to_geometry(rect, geom):
    """将选区裁剪进屏幕设备几何内，避免 grabWindow 越界返回空图。

    Args:
        rect: (x, y, w, h) 拟抓取的设备像素矩形
        geom: ScreenGeom（设备像素，x/y 为屏幕左上角，width/height 为设备尺寸）
    Returns:
        裁剪后的 (x, y, w, h)，宽高至少为 1
    """
    x, y, w, h = rect
    gx, gy, gw, gh = geom.x, geom.y, geom.width, geom.height

    right = min(x + w, gx + gw)
    bottom = min(y + h, gy + gh)
    nx = max(x, gx)
    ny = max(y, gy)
    nw = max(1, right - nx)
    nh = max(1, bottom - ny)
    return (nx, ny, nw, nh)


def virtual_bounding_geometry(screens):
    """所有屏幕逻辑几何的并集（用于覆盖层铺满多屏）。

    Args:
        screens: List[ScreenGeom]
    Returns:
        ScreenGeom，覆盖全部屏幕的最小外接矩形（dpr 取 1，仅用于布局）
    """
    if not screens:
        return ScreenGeom(0, 0, 0, 0, 1.0)
    left = min(s.x for s in screens)
    top = min(s.y for s in screens)
    right = max(s.x + s.width for s in screens)
    bottom = max(s.y + s.height for s in screens)
    return ScreenGeom(left, top, right - left, bottom - top, 1.0)


def screen_index_for_point(point, screens):
    """返回包含某逻辑坐标点的屏幕索引；无命中则取最近屏幕。

    Args:
        point: (x, y) 绝对逻辑坐标
        screens: List[ScreenGeom]
    Returns:
        int 屏幕索引（用于映射回 QScreen 对象）
    """
    if not screens:
        return -1
    px, py = point
    for i, s in enumerate(screens):
        if s.x <= px < s.x + s.width and s.y <= py < s.y + s.height:
            return i
    # 回退：欧氏距离最近的屏幕
    best, best_d = 0, float("inf")
    for i, s in enumerate(screens):
        d = (s.x - px) ** 2 + (s.y - py) ** 2
        if d < best_d:
            best_d, best = d, i
    return best
