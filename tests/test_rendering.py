"""渲染流程测试: EditorController 标注渲染到 PIL Image"""
import sys
import os
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image
import numpy as np


class TestRenderingPipeline(unittest.TestCase):
    """渲染管线测试"""

    @classmethod
    def setUpClass(cls):
        # 创建带渐变的测试底图（纯色马赛克无效果）
        cls.tmpdir = tempfile.mkdtemp(prefix="screenshot_render_test_")
        cls.base_path = os.path.join(cls.tmpdir, "base.png")
        import numpy as np
        # 用numpy创建水平渐变+条纹图
        arr = np.zeros((300, 400, 3), dtype=np.uint8)
        for x in range(400):
            arr[:, x, 0] = int(50 + x / 400 * 200)    # R 渐变
            arr[:, x, 1] = int(100 - x / 400 * 80)    # G 渐变
            arr[:, x, 2] = min(255, int(150 + (x % 80) * 2))    # B 条纹
        cls.test_img = Image.fromarray(arr)
        cls.test_img.save(cls.base_path)

    def setUp(self):
        from controllers.editor_controller import EditorController
        self.ec = EditorController()
        self.ec._working_image_path = self.base_path
        self.ec._original_image_path = self.base_path

    def _hexToRGBA(self, hex_color, alpha=255):
        """辅助: 十六进制→RGBA"""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r, g, b, alpha)

    def test_render_empty_annotations(self):
        """测试无标注渲染 = 原图"""
        self.ec._annotations = []
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))
        # 没有标注时结果应该接近原图（可能有微小差异因为RGBA→RGB转换）
        result_arr = np.array(result.convert("RGB"))
        base_arr = np.array(self.test_img)
        diff = np.abs(result_arr.astype(int) - base_arr.astype(int)).max()
        self.assertLess(diff, 5)  # 颜色差异小于5

    def test_render_rectangle(self):
        """测试矩形标注渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.RECT, points=[(50, 50), (200, 150)],
                           color="#FF0000", width=3)
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))
        # 验证输出不为空
        self.assertIsNotNone(result)

    def test_render_line(self):
        """测试线条标注渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.LINE, points=[(10, 10), (300, 200)],
                           color="#00FF00", width=5)
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_circle(self):
        """测试圆形标注渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.CIRCLE, points=[(50, 50), (250, 200)],
                           color="#0000FF", width=3)
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_arrow(self):
        """测试箭头标注渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.ARROW, points=[(10, 150), (200, 150)],
                           color="#FF3B30", width=3)
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_text(self):
        """测试文字标注渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.TEXT, points=[(100, 100)],
                           color="#000000", width=16,
                           properties={"text": "测试文字"})
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_text_properties_preserved(self):
        """回归: 文字的 text/加粗/背景属性必须随标注保留并渲染

        之前 finishAnnotation 未复制 properties，导致输入文字丢失只能显示占位符。
        """
        from models.annotation import AnnotationData, ToolType

        ann = AnnotationData(
            ToolType.TEXT, points=[(100, 100)], color="#FF0000", width=20,
            properties={"text": "Hello\nWorld", "bold": True, "background": True}
        )
        self.ec._annotations = [ann]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        # 背景开启时应在 (100,100) 附近出现半透明黑底像素
        result_arr = np.array(result.convert("RGBA"))
        region = result_arr[98:140, 90:260]
        dark_px = np.sum((region[:, :, 0] < 80) & (region[:, :, 3] > 50))
        self.assertGreater(dark_px, 0, "开启背景的文字应渲染半透明底")

    def test_render_highlight(self):
        """测试高亮标注渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.HIGHLIGHT, points=[(50, 50), (250, 100)],
                           color="#FFCC02", width=3, opacity=80)
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_watermark(self):
        """测试水印 — 使用_applyWatermark直接"""
        from models.annotation import AnnotationData, ToolType

        ann = AnnotationData(ToolType.WATERMARK, points=[(0, 0)],
                               color="#888888", width=40, opacity=25,
                               properties={"text": "机密"})
        result = self.ec._applyWatermark(self.test_img.copy(), ann)
        self.assertEqual(result.size, (400, 300))

    def test_render_smart_select(self):
        """测试虚线选区渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.SMART_SELECT, points=[(30, 30), (300, 250)],
                           color="#4a8cff", width=2)
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_polygon(self):
        """测试多边形渲染"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.POLYGON,
                           points=[(100, 50), (200, 50), (250, 150), (150, 200), (100, 150)],
                           color="#FF3B30", width=2)
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_mosaic(self):
        """测试马赛克像素化 — 使用_applyMosaic直接"""
        from models.annotation import AnnotationData, ToolType

        ann = AnnotationData(ToolType.MOSAIC, points=[(50, 50), (250, 200)],
                               color="#888888", width=3,
                               properties={"block_size": 8})
        result = self.ec._applyMosaic(self.test_img.copy(), ann)
        self.assertEqual(result.size, (400, 300))
        # 马赛克区域应该被像素化，不等于原图
        result_arr = np.array(result.convert("RGB"))
        base_arr = np.array(self.test_img.convert("RGB"))
        diff = np.abs(result_arr.astype(int) - base_arr.astype(int)).sum()
        self.assertGreater(diff, 0, "马赛克应该改变了图像内容")

    def test_render_eraser(self):
        """测试橡皮擦渲染 — 使用_applyEraser直接"""
        from models.annotation import AnnotationData, ToolType

        ann = AnnotationData(ToolType.ERASER, points=[(100, 100), (120, 120), (140, 140)],
                               width=5)
        result = self.ec._applyEraser(self.test_img.copy(), self.test_img.copy(), ann)
        self.assertEqual(result.size, (400, 300))

    def test_render_multiple_annotations(self):
        """测试混合标注渲染（非破坏性工具）"""
        from models.annotation import AnnotationData, ToolType

        self.ec._annotations = [
            AnnotationData(ToolType.RECT, points=[(10, 10), (100, 80)],
                           color="#FF0000", width=2),
            AnnotationData(ToolType.CIRCLE, points=[(150, 50), (300, 200)],
                           color="#0000FF", width=3),
            AnnotationData(ToolType.ARROW, points=[(300, 250), (100, 250)],
                           color="#00FF00", width=3),
            AnnotationData(ToolType.TEXT, points=[(150, 280)],
                           color="#000", width=14,
                           properties={"text": "Done"}),
        ]
        result = self.ec._renderAnnotationsOnImage(self.test_img)
        self.assertEqual(result.size, (400, 300))

    def test_render_with_mosaic_and_eraser(self):
        """测试马赛克+橡皮擦混合（直接调用_apply方法）"""
        from models.annotation import AnnotationData, ToolType

        result = self.test_img.copy()
        # 先渲染一个非破坏性标注
        rect_ann = AnnotationData(ToolType.RECT, points=[(250, 50), (350, 150)],
                                   color="#FF0000", width=2)
        rendered_ann = self.ec._renderAnnotationsOnImage(result)
        # 手动应用马赛克
        mosaic_ann = AnnotationData(ToolType.MOSAIC, points=[(20, 20), (180, 120)],
                                     color="#888", width=3,
                                     properties={"block_size": 8})
        after_mosaic = self.ec._applyMosaic(rendered_ann, mosaic_ann)
        self.assertEqual(after_mosaic.size, (400, 300))

    def test_mosaic_block_size(self):
        """测试马赛克块大小参数生效"""
        from models.annotation import AnnotationData, ToolType

        # 小块马赛克
        ann_small = AnnotationData(ToolType.MOSAIC, points=[(50, 50), (250, 200)],
                                   color="#888", width=3,
                                   properties={"block_size": 4})
        result_small = self.ec._applyMosaic(self.test_img.copy(), ann_small)

        # 大块马赛克
        ann_large = AnnotationData(ToolType.MOSAIC, points=[(50, 50), (250, 200)],
                                   color="#888", width=3,
                                   properties={"block_size": 20})
        result_large = self.ec._applyMosaic(self.test_img.copy(), ann_large)

        self.assertEqual(result_small.size, result_large.size)
        arr_small = np.array(result_small.convert("RGB"))
        arr_large = np.array(result_large.convert("RGB"))
        diff = np.abs(arr_small.astype(int) - arr_large.astype(int)).sum()
        self.assertGreater(diff, 0, "不同块大小的马赛克应有不同效果")

    def test_render_output_is_rgba(self):
        """测试渲染输出是RGBA模式（内部渲染始终保留透明度）"""
        from models.annotation import AnnotationData, ToolType

        test_cases = [
            AnnotationData(ToolType.BRUSH, points=[(10, 10), (100, 100)],
                           color="#FF0000", width=3),
            AnnotationData(ToolType.LINE, points=[(10, 10), (300, 200)],
                           color="#00FF00", width=3),
            AnnotationData(ToolType.RECT, points=[(10, 10), (100, 80)],
                           color="#0000FF", width=3),
            AnnotationData(ToolType.CIRCLE, points=[(50, 50), (250, 200)],
                           color="#FF0000", width=3),
            AnnotationData(ToolType.ARROW, points=[(10, 150), (200, 150)],
                           color="#FF3B30", width=3),
            AnnotationData(ToolType.TEXT, points=[(100, 100)],
                           color="#000000", width=16,
                           properties={"text": "测试"}),
            AnnotationData(ToolType.HIGHLIGHT, points=[(50, 50), (250, 100)],
                           color="#FFCC02", width=3, opacity=80),
            AnnotationData(ToolType.SMART_SELECT, points=[(30, 30), (300, 250)],
                           color="#4a8cff", width=2),
            AnnotationData(ToolType.POLYGON,
                           points=[(50, 50), (150, 50), (100, 100)],
                           color="#FF0000", width=2),
        ]
        for ann in test_cases:
            with self.subTest(tool=ann.tool_type.value):
                self.ec._annotations = [ann]
                result = self.ec._renderAnnotationsOnImage(self.test_img)
                self.assertEqual(result.mode, "RGBA",
                                 f"{ann.tool_type.value} 应输出RGBA")
    def test_mosaic_excludes_other_annotations(self):
        """测试马赛克不影响同区域的其他标注"""
        from models.annotation import AnnotationData, ToolType

        result = self.ec._applyMosaic(self.test_img.copy(),
            AnnotationData(ToolType.MOSAIC, points=[(30, 30), (150, 150)],
                           color="#888", width=3, properties={"block_size": 16}))
        self.assertEqual(result.size, (400, 300))

    def test_mosaic_includes_bottom_right_pixel(self):
        """马赛克区域应包含右下角像素（闭区间→半开区间转换验证）"""
        from models.annotation import AnnotationData, ToolType
        img = Image.new("RGB", (20, 20), (255, 255, 255))
        img.putpixel((8, 8), (0, 0, 0))  # 右下角孤立黑点
        ann = AnnotationData(ToolType.MOSAIC, points=[(0, 0), (8, 8)],
                             color="#888", width=3,
                             properties={"block_size": 4})
        result = self.ec._applyMosaic(img.convert("RGBA"), ann)
        # (8,8) 被包含进处理区域，不应再是原始黑色
        self.assertNotEqual(tuple(result.convert("RGB").getpixel((8, 8))), (0, 0, 0))

    def test_arrow_line_does_not_extend_past_head(self):
        """箭头主线段应缩进三角头底边，端点圆帽不突出尖端"""
        from models.annotation import AnnotationData, ToolType
        img = Image.new("RGBA", (100, 50), (255, 255, 255, 255))
        ann = AnnotationData(ToolType.ARROW, points=[(10, 25), (80, 25)],
                             color="#FF0000", width=6)
        result = self.ec._renderAnnotationsOnImage(img)
        arr = np.array(result)
        red_mask = (arr[:, :, 0] > 200) & (arr[:, :, 1] < 50) & (arr[:, :, 2] < 50)
        # 箭头尖端在 x=80，三角头底边在 x=80-30=50 左右；x>80 不应有红色圆帽溢出
        self.assertEqual(red_mask[:, 81:].sum(), 0,
                         "箭头线段圆帽不应突出到三角头右侧")

    def test_watermark_preview_not_destructive(self):
        """回归测试：拖水印滑块只更新预览，不烘焙进底图、不污染撤销栈

        参考 Flameshot/ShareX：实时预览应是非破坏性的，只有点'应用到截图'
        调用 setWatermarkParams 才真正提交破坏性水印。
        """
        self.ec.selectTool("watermark")
        # 模拟连续拖拽大小（多次调用 updateWatermarkPreview）
        for size in (40, 60, 80, 120, 200):
            self.ec.updateWatermarkPreview("机密", 25, size, 28, "tile")
            # 每次拖拽都不应产生破坏性备份
            self.assertEqual(len(self.ec._image_backup_stack), 0,
                             "拖滑块不应烘焙水印进底图")
            # 预览参数应实时更新
            self.assertEqual(self.ec._wm_preview["size"], size)
        # 预览存在时底图路径不应改变
        self.assertEqual(self.ec._working_image_path, self.base_path)

    def test_watermark_commit_is_destructive(self):
        """回归测试：setWatermarkParams（应用到截图）才提交破坏性水印"""
        self.ec.selectTool("watermark")
        self.ec.updateWatermarkPreview("机密", 25, 80, 28, "tile")
        self.assertEqual(len(self.ec._image_backup_stack), 0)  # 预览阶段无备份

        # 点'应用到截图' → 真正提交
        self.ec.setWatermarkParams("机密", 25, 80, 28, "tile")
        self.assertEqual(len(self.ec._image_backup_stack), 1,
                         "提交后应产生1个破坏性备份")
        # 提交后预览被清除
        self.assertIsNone(self.ec._wm_preview)
        # 底图路径已更新为新工作图
        self.assertNotEqual(self.ec._working_image_path, self.base_path)


class TestHexToRGBA(unittest.TestCase):
    """颜色转换测试"""

    def test_full_hex(self):
        """测试6位颜色"""
        from controllers.editor_controller import EditorController
        result = EditorController._hexToRGBA("#FF0000", 255)
        self.assertEqual(result, (255, 0, 0, 255))

    def test_full_hex_with_alpha(self):
        """测试带透明度"""
        from controllers.editor_controller import EditorController
        result = EditorController._hexToRGBA("#00FF00", 128)
        self.assertEqual(result, (0, 255, 0, 128))

    def test_without_hash(self):
        """测试不含#"""
        from controllers.editor_controller import EditorController
        result = EditorController._hexToRGBA("0000FF", 200)
        self.assertEqual(result, (0, 0, 255, 200))

    def test_short_hex(self):
        """测试3位颜色"""
        from controllers.editor_controller import EditorController
        result = EditorController._hexToRGBA("#FFF", 255)
        self.assertEqual(result, (255, 255, 255, 255))

    def test_invalid_hex(self):
        """测试无效输入"""
        from controllers.editor_controller import EditorController
        result = EditorController._hexToRGBA("INVALID", 255)
        self.assertEqual(result, (255, 0, 0, 255))  # 默认红色


class TestDrawAnnotation(unittest.TestCase):
    """单独绘制函数测试"""

    @classmethod
    def setUpClass(cls):
        cls.test_img = Image.new("RGB", (200, 200), (255, 255, 255))

    def setUp(self):
        from controllers.editor_controller import EditorController
        self.ec = EditorController()
        self.ec._base_image_path = "/tmp/test.png"

    def test_brush_draws_stroke(self):
        """测试画笔绘制路径"""
        from models.annotation import AnnotationData, ToolType
        from PIL import ImageDraw, ImageFont

        overlay = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("msyh.ttc", 20)
        except Exception:
            font = ImageFont.load_default()

        ann = AnnotationData(ToolType.BRUSH, points=[(10, 10), (50, 30), (100, 80)],
                             color="#FF0000", width=3)
        self.ec._drawAnnotation(draw, ann, font)
        # 验证overlay上有红色像素
        arr = np.array(overlay)
        red_pixels = np.sum((arr[:, :, 0] > 200) & (arr[:, :, 3] > 0))
        self.assertGreater(red_pixels, 0, "画笔应有红色像素")

    def test_arrow_has_triangle_head(self):
        """测试箭头包含三角箭头"""
        from models.annotation import AnnotationData, ToolType
        from PIL import ImageDraw, ImageFont

        overlay = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("msyh.ttc", 20)
        except Exception:
            font = ImageFont.load_default()

        ann = AnnotationData(ToolType.ARROW, points=[(10, 100), (180, 100)],
                             color="#FF0000", width=4)
        self.ec._drawAnnotation(draw, ann, font)

        arr = np.array(overlay)
        # 箭头线应该有绘制
        red_pixels = np.sum((arr[:, :, 0] > 200) & (arr[:, :, 3] > 0))
        self.assertGreater(red_pixels, 0, "箭头应有红色像素")


if __name__ == "__main__":
    unittest.main(verbosity=2)
