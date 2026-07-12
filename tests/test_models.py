"""数据模型与工具测试: AnnotationData, ScreenshotData, ToolConfig"""
import sys
import json
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAnnotationData(unittest.TestCase):
    """AnnotationData 模型测试"""

    def setUp(self):
        from models.annotation import AnnotationData, ToolType
        self.AnnotationData = AnnotationData
        self.ToolType = ToolType

    def test_default_values(self):
        """测试默认值"""
        ann = self.AnnotationData(self.ToolType.RECT)
        self.assertEqual(ann.tool_type, self.ToolType.RECT)
        self.assertEqual(ann.points, [])
        self.assertEqual(ann.color, "#FF3B30")
        self.assertEqual(ann.width, 3)
        self.assertEqual(ann.opacity, 255)
        self.assertEqual(ann.properties, {})
        self.assertEqual(ann.timestamp, 0.0)

    def test_custom_values(self):
        """测试自定义值"""
        ann = self.AnnotationData(
            tool_type=self.ToolType.LINE,
            points=[(10, 20), (30, 40)],
            color="#00FF00",
            width=5,
            opacity=128,
            properties={"dash": True},
            timestamp=1234567890.0
        )
        self.assertEqual(ann.tool_type, self.ToolType.LINE)
        self.assertEqual(ann.points, [(10, 20), (30, 40)])
        self.assertEqual(ann.color, "#00FF00")
        self.assertEqual(ann.width, 5)
        self.assertEqual(ann.opacity, 128)
        self.assertEqual(ann.properties, {"dash": True})
        self.assertEqual(ann.timestamp, 1234567890.0)

    def test_toDict(self):
        """测试序列化"""
        ann = self.AnnotationData(
            self.ToolType.CIRCLE,
            points=[(0, 0), (100, 100)],
            color="#0000FF",
            width=2,
            opacity=200,
            properties={"filled": True, "block_size": 8},
            timestamp=999.0
        )
        d = ann.toDict()
        self.assertEqual(d["tool_type"], "circle")
        self.assertEqual(d["points"], [(0, 0), (100, 100)])
        self.assertEqual(d["color"], "#0000FF")
        self.assertEqual(d["width"], 2)
        self.assertEqual(d["opacity"], 200)
        self.assertEqual(d["properties"]["filled"], True)
        self.assertEqual(d["properties"]["block_size"], 8)
        self.assertEqual(d["timestamp"], 999.0)

    def test_fromDict_basic(self):
        """测试基本反序列化"""
        data = {
            "tool_type": "arrow",
            "points": [(5, 5), (50, 50)],
            "color": "#FF0000",
            "width": 4,
            "opacity": 255,
            "properties": {},
            "timestamp": 100.0
        }
        ann = self.AnnotationData.fromDict(data)
        self.assertEqual(ann.tool_type, self.ToolType.ARROW)
        self.assertEqual(ann.color, "#FF0000")
        self.assertEqual(ann.width, 4)

    def test_fromDict_defaults(self):
        """测试反序列化默认值"""
        ann = self.AnnotationData.fromDict({"tool_type": "rect"})
        self.assertEqual(ann.tool_type, self.ToolType.RECT)
        self.assertEqual(ann.points, [])
        self.assertEqual(ann.color, "#FF3B30")
        self.assertEqual(ann.width, 3)

    def test_roundtrip(self):
        """测试序列化→反序列化往返"""
        original = self.AnnotationData(
            self.ToolType.MOSAIC,
            points=[(10, 10), (200, 200)],
            color="#888888",
            width=6,
            opacity=255,
            properties={"block_size": 12}
        )
        restored = self.AnnotationData.fromDict(original.toDict())
        self.assertEqual(restored.tool_type, original.tool_type)
        self.assertEqual(restored.points, original.points)
        self.assertEqual(restored.color, original.color)
        self.assertEqual(restored.width, original.width)
        self.assertEqual(restored.properties, original.properties)

    def test_json_serializable(self):
        """测试可JSON序列化"""
        ann = self.AnnotationData(
            self.ToolType.POLYGON,
            points=[(0, 0), (50, 0), (50, 50), (0, 50)],
            color="#FFCC00"
        )
        json_str = json.dumps(ann.toDict(), ensure_ascii=False)
        self.assertIn("polygon", json_str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["tool_type"], "polygon")
        self.assertEqual(len(parsed["points"]), 4)

    def test_all_tool_types(self):
        """测试所有工具类型"""
        cases = {
            "brush": self.ToolType.BRUSH,
            "line": self.ToolType.LINE,
            "rect": self.ToolType.RECT,
            "circle": self.ToolType.CIRCLE,
            "arrow": self.ToolType.ARROW,
            "text": self.ToolType.TEXT,
            "mosaic": self.ToolType.MOSAIC,
            "highlight": self.ToolType.HIGHLIGHT,
            "eraser": self.ToolType.ERASER,
            "watermark": self.ToolType.WATERMARK,
            "smart_select": self.ToolType.SMART_SELECT,
            "polygon": self.ToolType.POLYGON,
        }
        for name, enum_val in cases.items():
            ann = self.AnnotationData(enum_val, color="#000")
            self.assertEqual(ann.tool_type, enum_val)
            d = ann.toDict()
            self.assertEqual(d["tool_type"], name)
            restored = self.AnnotationData.fromDict(d)
            self.assertEqual(restored.tool_type, enum_val)


class TestScreenshotData(unittest.TestCase):
    """ScreenshotData 模型测试"""

    def test_default_values(self):
        """测试默认值"""
        from models.screenshot import ScreenshotData, CaptureMode
        sd = ScreenshotData()
        self.assertEqual(sd.image_path, "")
        self.assertEqual(sd.capture_mode, CaptureMode.FULLSCREEN)
        self.assertEqual(sd.width, 0)
        self.assertEqual(sd.height, 0)
        self.assertEqual(sd.timestamp, 0.0)
        self.assertEqual(sd.dpi_scale, 1.0)

    def test_custom_values(self):
        """测试自定义值"""
        from models.screenshot import ScreenshotData, CaptureMode
        sd = ScreenshotData(
            image_path="/path/to/img.png",
            capture_mode=CaptureMode.REGION,
            width=1920,
            height=1080,
            timestamp=12345.0,
            dpi_scale=1.5
        )
        self.assertEqual(sd.image_path, "/path/to/img.png")
        self.assertEqual(sd.capture_mode, CaptureMode.REGION)
        self.assertEqual(sd.width, 1920)
        self.assertEqual(sd.height, 1080)
        self.assertEqual(sd.dpi_scale, 1.5)

    def test_capture_modes(self):
        """测试所有截图模式"""
        from models.screenshot import CaptureMode
        modes = {
            "fullscreen": CaptureMode.FULLSCREEN,
            "region": CaptureMode.REGION,
            "window": CaptureMode.WINDOW,
            "scrolling": CaptureMode.SCROLLING,
        }
        for name, enum_val in modes.items():
            self.assertEqual(enum_val.value, name)


class TestToolConfig(unittest.TestCase):
    """工具配置测试"""

    def test_every_tool_has_config(self):
        """测试每种工具都有默认配置"""
        from models.annotation import ToolType
        from models.tool_config import DEFAULT_TOOL_CONFIGS

        for tool_type in ToolType:
            with self.subTest(tool=tool_type.value):
                self.assertIn(tool_type, DEFAULT_TOOL_CONFIGS,
                              f"缺少配置: {tool_type.value}")

    def test_config_properties(self):
        """测试配置属性"""
        from models.tool_config import ToolConfig
        from models.annotation import ToolType

        cfg = ToolConfig(ToolType.BRUSH, "#FF6B35", 7, 255, 1, 30)
        self.assertIsInstance(cfg.properties, dict)

    def test_brush_config(self):
        """测试画笔配置"""
        from models.tool_config import DEFAULT_TOOL_CONFIGS
        from models.annotation import ToolType

        cfg = DEFAULT_TOOL_CONFIGS[ToolType.BRUSH]
        self.assertEqual(cfg.default_color, "#FF6B35")
        self.assertEqual(cfg.default_width, 7)
        self.assertEqual(cfg.min_width, 1)
        self.assertEqual(cfg.max_width, 30)

    def test_eraser_config(self):
        """测试橡皮擦配置"""
        from models.tool_config import DEFAULT_TOOL_CONFIGS
        from models.annotation import ToolType

        cfg = DEFAULT_TOOL_CONFIGS[ToolType.ERASER]
        self.assertEqual(cfg.default_width, 15)
        self.assertTrue(cfg.min_width >= 5)

    def test_mosaic_config(self):
        """测试马赛克配置"""
        from models.tool_config import DEFAULT_TOOL_CONFIGS
        from models.annotation import ToolType

        cfg = DEFAULT_TOOL_CONFIGS[ToolType.MOSAIC]
        self.assertEqual(cfg.default_width, 8)
        self.assertTrue(cfg.min_width >= 4)
        self.assertTrue(cfg.max_width <= 30)

    def test_watermark_config(self):
        """测试水印配置"""
        from models.tool_config import DEFAULT_TOOL_CONFIGS
        from models.annotation import ToolType

        cfg = DEFAULT_TOOL_CONFIGS[ToolType.WATERMARK]
        self.assertEqual(cfg.default_opacity, 25)
        self.assertEqual(cfg.default_width, 52)  # 字号

    def test_highlight_config(self):
        """测试高亮配置"""
        from models.tool_config import DEFAULT_TOOL_CONFIGS
        from models.annotation import ToolType

        cfg = DEFAULT_TOOL_CONFIGS[ToolType.HIGHLIGHT]
        self.assertEqual(cfg.default_opacity, 100)  # 半透明
        self.assertEqual(cfg.default_color, "#FFCC02")


class TestBaseTool(unittest.TestCase):
    """工具基类测试"""

    def test_init_properties(self):
        """测试初始化属性"""
        from engines.annotation.base import BaseTool
        from models.annotation import ToolType

        # BaseTool是抽象的，用具体子类
        from engines.annotation.rect import RectTool
        tool = RectTool()
        self.assertEqual(tool.tool_type, ToolType.RECT)
        self.assertEqual(tool.points, [])
        self.assertIsInstance(tool.properties, dict)

    def test_set_properties(self):
        """测试设置属性"""
        from engines.annotation.rect import RectTool
        tool = RectTool()
        tool.setProperties("#FF0000", 5, 128)
        self.assertEqual(tool.color, "#FF0000")
        self.assertEqual(tool.width, 5)
        self.assertEqual(tool.opacity, 128)

    def test_reset(self):
        """测试重置"""
        from engines.annotation.brush import BrushTool
        tool = BrushTool()
        tool.points = [(10, 10), (20, 20)]
        tool.is_active = True
        tool.reset()
        self.assertEqual(tool.points, [])
        self.assertFalse(tool.is_active)

    def test_get_pen(self):
        """测试获取画笔"""
        from engines.annotation.rect import RectTool
        tool = RectTool()
        tool.setProperties("#00FF00", 3)
        pen = tool.getPen()
        self.assertIsNotNone(pen)
        self.assertEqual(pen.width(), 3)

    def test_finish_annotation_clears_points(self):
        """测试完成标注清空点"""
        from engines.annotation.rect import RectTool
        tool = RectTool()
        tool.points = [(0, 0), (100, 100)]
        tool.finishAnnotation()
        self.assertEqual(tool.points, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
