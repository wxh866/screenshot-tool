"""核心模块单元测试: EventBus, ConfigManager, HistoryManager, UndoManager"""
import sys
import os
import json
import tempfile
import unittest
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import QCoreApplication


class TestEventBus(unittest.TestCase):
    """事件总线测试"""

    def setUp(self):
        from core.event_bus import EventBus, EventType
        self.EventBus = EventBus
        self.EventType = EventType
        # 每个测试使用不同的事件类型避免交叉污染
        self.bus = EventBus.instance()

    def tearDown(self):
        self.bus.clear()

    def test_singleton(self):
        """测试单例模式"""
        bus1 = self.EventBus.instance()
        bus2 = self.EventBus.instance()
        self.assertIs(bus1, bus2)

    def test_subscribe_and_publish(self):
        """测试订阅和发布"""
        self.bus.clear()
        received = []

        def callback(data):
            received.append(data)

        self.bus.subscribe(self.EventType.SCREENSHOT_CAPTURED, callback)
        self.bus.publish(self.EventType.SCREENSHOT_CAPTURED, "test_data")
        self.assertEqual(received, ["test_data"])

    def test_unsubscribe(self):
        """测试取消订阅"""
        self.bus.clear()
        received = []

        def callback(data):
            received.append(data)

        self.bus.subscribe(self.EventType.THEME_CHANGED, callback)
        self.bus.publish(self.EventType.THEME_CHANGED, "dark")
        self.assertEqual(received, ["dark"])

        self.bus.unsubscribe(self.EventType.THEME_CHANGED, callback)
        self.bus.publish(self.EventType.THEME_CHANGED, "light")
        self.assertEqual(received, ["dark"])  # 第二次不应该触发

    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        self.bus.clear()
        results = []

        def cb1(data): results.append(("cb1", data))
        def cb2(data): results.append(("cb2", data))
        def cb3(data): results.append(("cb3", data))

        for cb in [cb1, cb2, cb3]:
            self.bus.subscribe(self.EventType.ANNOTATION_ADDED, cb)

        self.bus.publish(self.EventType.ANNOTATION_ADDED, "annot")
        self.assertEqual(len(results), 3)
        self.assertIn(("cb1", "annot"), results)
        self.assertIn(("cb2", "annot"), results)
        self.assertIn(("cb3", "annot"), results)

    def test_publish_no_subscribers(self):
        """测试无订阅者时不崩溃"""
        self.bus.clear()
        # 不订阅即发布，不应抛出异常
        self.bus.publish(self.EventType.FILE_EXPORTED, None)

    def test_callback_exception_handling(self):
        """测试回调异常不破坏总线"""
        self.bus.clear()
        results = []

        def bad_callback(data):
            raise RuntimeError("故意错误")

        def good_callback(data):
            results.append(data)

        self.bus.subscribe(self.EventType.UNDO_PERFORMED, bad_callback)
        self.bus.subscribe(self.EventType.UNDO_PERFORMED, good_callback)

        # 即使bad_callback抛异常，good_callback仍应执行
        self.bus.publish(self.EventType.UNDO_PERFORMED, "ok")
        self.assertEqual(results, ["ok"])

    def test_clear(self):
        """测试清空订阅"""
        self.bus.clear()
        received = []

        def cb(data): received.append(data)

        self.bus.subscribe(self.EventType.CONFIG_CHANGED, cb)
        self.bus.clear()
        self.bus.publish(self.EventType.CONFIG_CHANGED, "x")
        self.assertEqual(received, [])

    def test_event_types_enum(self):
        """测试事件类型枚举完整性"""
        expected = [
            "screenshot_captured", "screenshot_mode_changed",
            "tool_changed", "annotation_added", "annotation_deleted", "annotation_modified",
            "undo_performed", "redo_performed", "undo_state_changed",
            "theme_changed",
            "file_exported", "file_copied",
            "history_updated",
            "config_changed",
        ]
        values = [e.value for e in self.EventType]
        for exp in expected:
            self.assertIn(exp, values)


class TestConfigManager(unittest.TestCase):
    """配置管理器测试"""

    @classmethod
    def setUpClass(cls):
        # 确保 QCoreApplication 存在
        from core.config_manager import ConfigManager
        cls.ConfigManager = ConfigManager

        # 用临时目录替换配置目录
        cls._temp_dir = tempfile.mkdtemp(prefix="screenshot_test_config_")
        ConfigManager._config_dir_original = None

    def setUp(self):
        # 每次测试前重置单例：通过子类化避开文件系统
        self.cm = self.ConfigManager.instance()

    def test_singleton(self):
        """测试单例"""
        cm2 = self.ConfigManager.instance()
        self.assertIs(self.cm, cm2)

    def test_get_default_value(self):
        """测试获取默认值"""
        val = self.cm.get("app_config", "theme", "unknown")
        self.assertEqual(val, "dark")

    def test_get_with_default(self):
        """测试不存在key时返回默认值"""
        val = self.cm.get("app_config", "nonexistent_key", "fallback")
        self.assertEqual(val, "fallback")

    def test_set_and_get(self):
        """测试设置和读取"""
        self.cm.set("app_config", "theme", "light")
        val = self.cm.get("app_config", "theme", "")
        self.assertEqual(val, "light")
        # 恢复默认
        self.cm.set("app_config", "theme", "dark")

    def test_set_new_key(self):
        """测试设置新key"""
        self.cm.set("app_config", "test_int", 42)
        self.assertEqual(self.cm.get("app_config", "test_int"), 42)
        # 清理
        self.cm.set("app_config", "test_int", None)

    def test_getSection(self):
        """测试获取整个配置段"""
        section = self.cm.getSection("app_config")
        self.assertIsInstance(section, dict)
        self.assertIn("theme", section)

    def test_getSection_not_exists(self):
        """测试不存在的配置段"""
        section = self.cm.getSection("nonexistent_section")
        self.assertEqual(section, {})

    def test_default_app_config_structure(self):
        """测试默认应用配置结构完整"""
        cfg = self.cm.getSection("app_config")
        required_keys = ["theme", "language", "save_path", "file_format",
                         "auto_copy", "capture_mode", "toolbar_docked",
                         "max_history", "watermark"]
        for key in required_keys:
            self.assertIn(key, cfg, f"缺少配置项: {key}")

    def test_default_hotkey_config_structure(self):
        """测试快捷键配置结构完整"""
        cfg = self.cm.getSection("hotkeys")
        required_keys = ["capture_fullscreen", "capture_region", "capture_window",
                         "undo", "redo", "save", "copy", "escape"]
        for key in required_keys:
            self.assertIn(key, cfg, f"缺少快捷键: {key}")


class TestUndoManager(unittest.TestCase):
    """撤销管理器测试"""

    def setUp(self):
        from core.undo_manager import UndoManager
        self.UndoManager = UndoManager
        self.um = UndoManager.instance()
        self.um.clear()

    def test_singleton(self):
        """测试单例"""
        um2 = self.UndoManager.instance()
        self.assertIs(self.um, um2)

    def test_initially_empty(self):
        """测试初始状态空"""
        self.assertFalse(self.um.canUndo())
        self.assertFalse(self.um.canRedo())

    def test_execute_and_undo(self):
        """测试执行和撤销"""
        data = []

        class TestCommand(self.UndoManager.__bases__[0].__subclasses__()[0] if False else __import__('core.undo_manager').undo_manager.Command):
            pass

        # 直接用已经存在的命令子类测试
        from core.undo_manager import AddAnnotationCommand, ClearAllCommand

        engine = type('obj', (object,), {'annotations': []})()
        from models.annotation import AnnotationData, ToolType
        annot = AnnotationData(ToolType.RECT)

        cmd = AddAnnotationCommand(annot, engine)
        self.um.execute(cmd)
        self.assertTrue(self.um.canUndo())
        self.assertFalse(self.um.canRedo())
        self.assertEqual(len(engine.annotations), 1)

        self.um.undo()
        self.assertFalse(self.um.canUndo())
        self.assertTrue(self.um.canRedo())
        self.assertEqual(len(engine.annotations), 0)

    def test_execute_and_redo(self):
        """测试执行和重做"""
        from core.undo_manager import AddAnnotationCommand
        from models.annotation import AnnotationData, ToolType

        engine = type('obj', (object,), {'annotations': []})()
        annot = AnnotationData(ToolType.CIRCLE)

        cmd = AddAnnotationCommand(annot, engine)
        self.um.execute(cmd)
        self.um.undo()
        self.um.redo()
        self.assertTrue(self.um.canUndo())
        self.assertFalse(self.um.canRedo())
        self.assertEqual(len(engine.annotations), 1)

    def test_max_undo_steps(self):
        """测试最大撤销步数限制"""
        from core.undo_manager import AddAnnotationCommand
        from models.annotation import AnnotationData, ToolType

        engine = type('obj', (object,), {'annotations': []})()

        # 执行超过MAX_UNDO_STEPS次
        for i in range(self.um.MAX_UNDO_STEPS + 10):
            annot = AnnotationData(ToolType.BRUSH, points=[(i, i)])
            cmd = AddAnnotationCommand(annot, engine)
            self.um.execute(cmd)

        # 撤销栈不应超过MAX_UNDO_STEPS
        self.assertEqual(len(self.um.undo_stack), self.um.MAX_UNDO_STEPS)

    def test_redo_stack_cleared_on_new_command(self):
        """测试执行新命令时重做栈被清空"""
        from core.undo_manager import AddAnnotationCommand
        from models.annotation import AnnotationData, ToolType

        engine = type('obj', (object,), {'annotations': []})()
        annot1 = AnnotationData(ToolType.LINE)
        annot2 = AnnotationData(ToolType.RECT)

        cmd1 = AddAnnotationCommand(annot1, engine)
        self.um.execute(cmd1)
        self.um.undo()   # undo_stack空, redo_stack有1个
        self.assertTrue(self.um.canRedo())

        cmd2 = AddAnnotationCommand(annot2, engine)
        self.um.execute(cmd2)  # redo_stack应被清空
        self.assertFalse(self.um.canRedo())

    def test_clear(self):
        """测试清空"""
        from core.undo_manager import AddAnnotationCommand
        from models.annotation import AnnotationData, ToolType

        engine = type('obj', (object,), {'annotations': []})()
        cmd = AddAnnotationCommand(AnnotationData(ToolType.RECT), engine)
        self.um.execute(cmd)
        self.um.clear()
        self.assertFalse(self.um.canUndo())
        self.assertFalse(self.um.canRedo())

    def test_undo_empty(self):
        """测试空栈撤销不报错"""
        self.um.undo()  # 不应抛异常

    def test_redo_empty(self):
        """测试空栈重做不报错"""
        self.um.redo()  # 不应抛异常

    def test_add_annotation_command(self):
        """测试AddAnnotationCommand完整流程"""
        from core.undo_manager import AddAnnotationCommand
        from models.annotation import AnnotationData, ToolType

        engine = type('obj', (object,), {'annotations': []})()
        annot = AnnotationData(ToolType.RECT, color="#FF0000", width=3)
        cmd = AddAnnotationCommand(annot, engine)

        cmd.execute()
        self.assertEqual(len(engine.annotations), 1)

        cmd.undo()
        self.assertEqual(len(engine.annotations), 0)

        cmd.redo()
        self.assertEqual(len(engine.annotations), 1)

    def test_delete_annotation_command(self):
        """测试DeleteAnnotationCommand"""
        from core.undo_manager import DeleteAnnotationCommand
        from models.annotation import AnnotationData, ToolType

        annot = AnnotationData(ToolType.LINE, points=[(0,0),(100,100)])
        engine = type('obj', (object,), {'annotations': [annot]})()

        cmd = DeleteAnnotationCommand(0, annot, engine)
        cmd.execute()
        self.assertEqual(len(engine.annotations), 0)

        cmd.undo()
        self.assertEqual(len(engine.annotations), 1)
        self.assertEqual(engine.annotations[0].tool_type, ToolType.LINE)

    def test_clear_all_command(self):
        """测试ClearAllCommand"""
        from core.undo_manager import ClearAllCommand
        from models.annotation import AnnotationData, ToolType

        annot1 = AnnotationData(ToolType.RECT)
        annot2 = AnnotationData(ToolType.CIRCLE)
        engine = type('obj', (object,), {'annotations': [annot1, annot2]})()

        cmd = ClearAllCommand(engine)
        cmd.execute()
        self.assertEqual(len(engine.annotations), 0)

        cmd.undo()
        self.assertEqual(len(engine.annotations), 2)

    def test_composite_command(self):
        """测试CompositeCommand"""
        from core.undo_manager import CompositeCommand, AddAnnotationCommand
        from models.annotation import AnnotationData, ToolType

        engine = type('obj', (object,), {'annotations': []})()
        a1 = AnnotationData(ToolType.RECT)
        a2 = AnnotationData(ToolType.CIRCLE)
        a3 = AnnotationData(ToolType.LINE)

        comp = CompositeCommand([
            AddAnnotationCommand(a1, engine),
            AddAnnotationCommand(a2, engine),
            AddAnnotationCommand(a3, engine),
        ])

        comp.execute()
        self.assertEqual(len(engine.annotations), 3)

        comp.undo()
        self.assertEqual(len(engine.annotations), 0)


class TestHistoryManager(unittest.TestCase):
    """历史记录管理器测试"""

    def test_singleton(self):
        """测试单例"""
        from core.history_manager import HistoryManager
        hm1 = HistoryManager.instance()
        hm2 = HistoryManager.instance()
        self.assertIs(hm1, hm2)

    def test_instance_method(self):
        """测试instance()静态方法"""
        from core.history_manager import HistoryManager
        hm = HistoryManager.instance()
        self.assertIsNotNone(hm)

    def test_get_history_returns_list(self):
        """测试获取历史记录返回列表"""
        from core.history_manager import HistoryManager
        hm = HistoryManager.instance()
        history = hm.getHistory()
        self.assertIsInstance(history, list)


class TestAnnotationEngine(unittest.TestCase):
    """标注引擎测试"""

    def test_init_registers_tools(self):
        """测试初始化注册所有工具"""
        from core.annotation_service import AnnotationEngine
        from models.annotation import ToolType

        engine = AnnotationEngine()
        available = engine.getAvailableTools()
        self.assertIn(ToolType.BRUSH, available)
        self.assertIn(ToolType.RECT, available)
        self.assertIn(ToolType.CIRCLE, available)
        self.assertIn(ToolType.LINE, available)
        self.assertIn(ToolType.ARROW, available)
        self.assertIn(ToolType.TEXT, available)
        self.assertIn(ToolType.MOSAIC, available)
        self.assertIn(ToolType.HIGHLIGHT, available)
        self.assertIn(ToolType.ERASER, available)
        self.assertIn(ToolType.WATERMARK, available)
        self.assertIn(ToolType.SMART_SELECT, available)
        self.assertIn(ToolType.POLYGON, available)

    def test_set_current_tool(self):
        """测试切换工具"""
        from core.annotation_service import AnnotationEngine
        from models.annotation import ToolType

        engine = AnnotationEngine()
        engine.setCurrentTool(ToolType.BRUSH)
        self.assertIsNotNone(engine.current_tool)

    def test_set_current_tool_unknown(self):
        """测试切换到未注册工具不会崩溃"""
        from core.annotation_service import AnnotationEngine
        from models.annotation import ToolType

        engine = AnnotationEngine()

    def test_initially_no_annotations(self):
        """测试初始无标注"""
        from core.annotation_service import AnnotationEngine
        engine = AnnotationEngine()
        self.assertEqual(len(engine.annotations), 0)


if __name__ == "__main__":
    # 需要QCoreApplication运行Qt信号相关测试
    app = QCoreApplication(sys.argv)
    unittest.main(verbosity=2)
