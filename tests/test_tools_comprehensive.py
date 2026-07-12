"""全部12个绘图工具 + 撤销/重做的全面功能测试

通过 EditorController 公共 Slot（QML 实际调用的接口）驱动每个工具，
验证：标注数据正确性、渲染像素可见性、破坏性工具真实改图、撤销/重做可用。

参考项目（来自项目 reference 列表）：
- Flameshot (高星截图标注)
- ShareX (标注工具集)
- JamTools (智能选区 / GrabCut)
"""
import sys
import os
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import numpy as np


def _gradient_image():
    """生成带渐变/条纹的测试底图（纯色图会让马赛克/高亮无可见效果）"""
    arr = np.zeros((300, 400, 3), dtype=np.uint8)
    for x in range(400):
        arr[:, x, 0] = int(50 + x / 400 * 200)          # R 渐变
        arr[:, x, 1] = int(100 - x / 400 * 80)           # G 渐变
        arr[:, x, 2] = min(255, int(150 + (x % 80) * 2))  # B 条纹
    return Image.fromarray(arr)


class TestAllToolsComprehensive(unittest.TestCase):
    """全部绘图工具全面功能测试"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="screenshot_tools_test_")
        cls.base_path = os.path.join(cls.tmpdir, "base.png")
        cls.test_img = _gradient_image()
        cls.test_img.save(cls.base_path)

    def setUp(self):
        from controllers.editor_controller import EditorController
        from core.undo_manager import UndoManager
        UndoManager.instance().clear()
        self.ec = EditorController()
        self.ec._working_image_path = self.base_path
        self.ec._original_image_path = self.base_path

    # ===== 辅助方法 =====
    def _get_annotations(self):
        import json
        return json.loads(self.ec.getAnnotationsJson())

    def _set_color_width(self, color="#FF0000", width=5):
        self.ec.setColor(color)
        self.ec.setWidth(width)

    def _drive_drag(self, tool, p1, p2, color="#FF0000", width=5):
        """选择工具并拖拽（press -> move -> release）"""
        self.ec.selectTool(tool)
        self._set_color_width(color, width)
        self.ec.mousePress(p1[0], p1[1])
        self.ec.mouseMove((p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2)
        self.ec.mouseRelease(p2[0], p2[1])

    def _count_colored(self, img_rgba, target=(255, 0, 0), tol=60):
        arr = np.array(img_rgba.convert("RGB"))
        r, g, b = target
        mask = ((arr[:, :, 0] > r - tol) & (arr[:, :, 1] < g + tol) &
                (arr[:, :, 2] < b + tol))
        return int(mask.sum())

    def _render(self):
        base = Image.open(self.ec._working_image_path)
        return self.ec._renderAnnotationsOnImage(base)

    # ===== 1. 矩形 =====
    def test_rect_tool(self):
        """矩形：拖拽生成2点标注，渲染后红色像素可见"""
        self._drive_drag("rect", (50, 50), (200, 150))
        anns = self._get_annotations()
        self.assertEqual(len(anns), 1)
        self.assertEqual(anns[0]["tool_type"], "rect")
        self.assertEqual(anns[0]["points"], [[50, 50], [200, 150]])
        self.assertEqual(anns[0]["color"], "#FF0000")
        self.assertEqual(anns[0]["width"], 5)
        # 渲染可见
        rendered = self._render()
        red = self._count_colored(rendered, (255, 0, 0))
        self.assertGreater(red, 50, "矩形红色描边应可见")

    # ===== 2. 圆/椭圆 =====
    def test_circle_tool(self):
        """圆：拖拽生成椭圆标注，渲染后蓝色像素可见"""
        self._drive_drag("circle", (60, 60), (220, 160), color="#0000FF", width=4)
        anns = self._get_annotations()
        self.assertEqual(anns[0]["tool_type"], "circle")
        self.assertEqual(len(anns[0]["points"]), 2)
        rendered = self._render()
        blue = self._count_colored(rendered, (0, 0, 255))
        self.assertGreater(blue, 50, "椭圆描边应可见")

    # ===== 3. 直线 =====
    def test_line_tool(self):
        """直线：2点标注，渲染可见"""
        self._drive_drag("line", (10, 10), (300, 200), color="#00FF00", width=6)
        anns = self._get_annotations()
        self.assertEqual(anns[0]["tool_type"], "line")
        rendered = self._render()
        green = self._count_colored(rendered, (0, 255, 0))
        self.assertGreater(green, 20, "直线应可见")

    # ===== 4. 箭头 =====
    def test_arrow_tool(self):
        """箭头：2点标注，渲染可见（线+箭头头）"""
        self._drive_drag("arrow", (20, 20), (280, 180), color="#FF0000", width=4)
        anns = self._get_annotations()
        self.assertEqual(anns[0]["tool_type"], "arrow")
        self.assertEqual(len(anns[0]["points"]), 2)
        rendered = self._render()
        red = self._count_colored(rendered, (255, 0, 0))
        self.assertGreater(red, 30, "箭头应可见")

    # ===== 5. 画笔 =====
    def test_brush_tool(self):
        """画笔：press+move+release 收集多个点，渲染可见"""
        self.ec.selectTool("brush")
        self._set_color_width("#FF0000", 6)
        self.ec.mousePress(50, 50)
        for i in range(1, 20):
            self.ec.mouseMove(50 + i * 8, 50 + (i % 3) * 5)
        self.ec.mouseRelease(50 + 19 * 8, 50 + 2 * 5)
        anns = self._get_annotations()
        self.assertEqual(anns[0]["tool_type"], "brush")
        self.assertGreaterEqual(len(anns[0]["points"]), 20, "画笔应收集多个轨迹点")
        rendered = self._render()
        red = self._count_colored(rendered, (255, 0, 0))
        self.assertGreater(red, 100, "画笔轨迹应可见")

    # ===== 6. 高亮 =====
    def test_highlight_tool(self):
        """高亮：半透明填充，渲染后该区域与原图有差异"""
        self._drive_drag("highlight", (40, 40), (160, 120), color="#FFCC02", width=20)
        anns = self._get_annotations()
        self.assertEqual(anns[0]["tool_type"], "highlight")
        rendered = self._render()
        base_arr = np.array(self.test_img)
        ren_arr = np.array(rendered.convert("RGB"))
        diff = np.abs(ren_arr.astype(int) - base_arr.astype(int))
        self.assertGreater(diff.sum(), 1000, "高亮区域应改变像素")

    # ===== 7. 马赛克（破坏性）=====
    def test_mosaic_tool(self):
        """马赛克：拖拽后真正改图（像素块化）+ 压入撤销备份"""
        self.ec.selectTool("mosaic")
        self.ec.mousePress(50, 50)
        self.ec.mouseMove(120, 110)
        self.ec.mouseRelease(200, 200)
        # 破坏性：备份栈 +1，底图已更新
        self.assertEqual(len(self.ec._image_backup_stack), 1,
                         "马赛克应压入1个撤销备份")
        self.assertNotEqual(self.ec._working_image_path, self.base_path)
        # 区域被像素化：块内空间方差应趋近0
        work = np.array(Image.open(self.ec._working_image_path).convert("RGB"))
        block = work[50:200, 50:200]
        # 取一个 8x8 子块检查是否均一（逐通道计算空间方差）
        sub = block[0:8, 0:8]
        spatial_std = sub.reshape(-1, 3).std(axis=0)
        self.assertLess(spatial_std.max(), 5, "马赛克块内像素应被平均（低空间方差）")

    # ===== 8. 橡皮擦（破坏性）=====
    def test_eraser_tool(self):
        """橡皮擦：从原图还原像素。先在区域打马赛克改变底图，再擦除还原"""
        # 1) 马赛克改变 working
        self.ec.selectTool("mosaic")
        self.ec.mousePress(50, 50)
        self.ec.mouseRelease(200, 200)
        self.assertEqual(len(self.ec._image_backup_stack), 1)
        # 2) 橡皮擦擦除同一区域
        self.ec.selectTool("eraser")
        self.ec.setWidth(15)
        self.ec.mousePress(120, 120)
        self.ec.mouseMove(130, 130)
        self.ec.mouseRelease(140, 140)
        self.assertEqual(len(self.ec._image_backup_stack), 2,
                         "橡皮擦应再压入1个备份")
        # 擦除区域应恢复到与原始底图一致（检查完全在橡皮擦笔触半径内的区域）
        orig = np.array(self.test_img)
        work = np.array(Image.open(self.ec._working_image_path).convert("RGB"))
        region_diff = np.abs(work[125:135, 125:135].astype(int) -
                             orig[125:135, 125:135].astype(int)).max()
        self.assertLess(region_diff, 5, "橡皮擦区域应还原为原图像素")

    # ===== 9. 水印（预览非破坏 + 提交破坏）=====
    def test_watermark_preview_and_commit(self):
        """水印：拖参数只更新预览（不烘焙/不压栈）；点'应用到截图'才破坏"""
        self.ec.selectTool("watermark")
        self.assertIsNotNone(self.ec._wm_preview, "进入水印应显示默认预览")
        # 模拟拖动大小/改文字（多次调用 updateWatermarkPreview）
        for size in (40, 80, 120, 200):
            self.ec.updateWatermarkPreview("机密", 25, size, 28, "tile")
            self.assertEqual(len(self.ec._image_backup_stack), 0,
                             "拖滑块不应烘焙水印")
            self.assertEqual(self.ec._wm_preview["size"], size)
        self.assertEqual(self.ec._working_image_path, self.base_path)
        # 提交
        self.ec.setWatermarkParams("机密", 25, 120, 28, "tile")
        self.assertEqual(len(self.ec._image_backup_stack), 1,
                         "提交后应产生1个破坏性备份")
        self.assertIsNone(self.ec._wm_preview, "提交后预览应清除")
        self.assertNotEqual(self.ec._working_image_path, self.base_path)
        # 水印应真正改变图片
        work = np.array(Image.open(self.ec._working_image_path).convert("RGB"))
        diff = np.abs(work.astype(int) - np.array(self.test_img).astype(int)).max()
        self.assertGreater(diff, 0, "水印应改变图片像素")

    # ===== 10. 文字（多行/加粗/背景持久化）=====
    def test_text_tool(self):
        """文字：点选定位 -> setTextAnnotation 提交，properties 持久化"""
        self.ec.selectTool("text")
        self.ec.mousePress(100, 100)
        ok = self.ec.setTextAnnotation("你好世界", 24, True, True)
        self.assertTrue(ok, "setTextAnnotation 应返回 True")
        anns = self._get_annotations()
        self.assertEqual(len(anns), 1)
        self.assertEqual(anns[0]["tool_type"], "text")
        self.assertEqual(anns[0]["points"], [[100, 100]])
        self.assertEqual(anns[0]["properties"]["text"], "你好世界")
        self.assertTrue(anns[0]["properties"]["bold"])
        self.assertTrue(anns[0]["properties"]["background"])
        # 渲染后该区域应出现文字像素（与原图不同）
        rendered = self._render()
        ren_arr = np.array(rendered.convert("RGB"))
        base_arr = np.array(self.test_img)
        region = np.abs(ren_arr[90:160, 90:260].astype(int) -
                        base_arr[90:160, 90:260].astype(int))
        self.assertGreater(region.sum(), 500, "文字应渲染到图片")

    # ===== 11. 智能选区（GrabCut）=====
    def test_smart_select_tool(self):
        """智能选区：拖拽选区 -> 运行 GrabCut -> 生成前景掩码并改变背景"""
        self.ec.selectTool("smart_select")
        self.ec.mousePress(50, 50)
        self.ec.mouseMove(120, 120)
        self.ec.mouseRelease(250, 250)
        # 修复后：GrabCut 真正执行。智能选区为破坏性工具，标注被引擎记录、
        # 图片被修改并压入撤销备份（控制器侧 _annotations 会被清空属正常）
        self.assertEqual(len(self.ec._engine.annotations), 1,
                         "智能选区应生成1个标注记录")
        self.assertEqual(self.ec._engine.annotations[0].tool_type.value, "smart_select")
        self.assertEqual(len(self.ec._image_backup_stack), 1,
                         "智能选区(GrabCut)应压入1个撤销备份")
        work = np.array(Image.open(self.ec._working_image_path).convert("RGB"))
        diff = np.abs(work.astype(int) - np.array(self.test_img).astype(int)).max()
        self.assertGreater(diff, 0, "智能选区应改变图片（背景处理）")

    # ===== 12. 多边形（双击闭合）=====
    def test_polygon_tool(self):
        """多边形：多次点选顶点 -> finishPolygon 闭合完成"""
        self.ec.selectTool("polygon")
        self.ec.mousePress(50, 50)
        self.ec.mousePress(150, 50)
        self.ec.mousePress(150, 150)
        self.ec.finishPolygon(50, 150)
        anns = self._get_annotations()
        self.assertEqual(len(anns), 1)
        self.assertEqual(anns[0]["tool_type"], "polygon")
        self.assertGreaterEqual(len(anns[0]["points"]), 3,
                                "多边形闭合后至少3个顶点")
        rendered = self._render()
        red = self._count_colored(rendered, (255, 0, 0))
        self.assertGreater(red, 30, "多边形描边应可见")

    # ===== 撤销/重做 =====
    def test_undo_redo_non_destructive(self):
        """撤销/重做：普通标注可撤销再重做"""
        self._drive_drag("rect", (50, 50), (200, 150))
        self.assertTrue(self.ec.canUndo())
        self.ec.undo()
        self.assertEqual(len(self._get_annotations()), 0, "撤销后标注应清空")
        self.assertFalse(self.ec.canUndo())
        self.assertTrue(self.ec.canRedo())
        self.ec.redo()
        self.assertEqual(len(self._get_annotations()), 1, "重做后标注应恢复")

    def test_undo_destructive(self):
        """撤销破坏性工具：还原底图"""
        self.ec.selectTool("mosaic")
        self.ec.mousePress(50, 50)
        self.ec.mouseRelease(200, 200)
        self.assertTrue(self.ec.canUndo())
        self.ec.undo()
        self.assertEqual(len(self.ec._image_backup_stack), 0,
                         "撤销后应清空备份栈")
        # 撤销后底图内容应还原为原图（备份即原始渲染结果，路径为临时文件属正常）
        restored = np.array(Image.open(self.ec._working_image_path).convert("RGB"))
        self.assertTrue(np.array_equal(restored, np.array(self.test_img)),
                        "撤销后底图内容应还原为原图")
        self.assertEqual(len(self._get_annotations()), 0)

    def test_clear_all(self):
        """清除所有标注"""
        self._drive_drag("rect", (50, 50), (200, 150))
        self._drive_drag("line", (10, 10), (100, 100))
        self.ec.clearAll()
        self.assertEqual(len(self._get_annotations()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
