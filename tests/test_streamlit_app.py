"""Streamlit 输入界面的无浏览器回归测试。"""

import unittest

from streamlit.testing.v1 import AppTest


class TestStreamlitInputs(unittest.TestCase):
    def test_agent_task_can_be_edited(self):
        app = AppTest.from_file("../app.py").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.selectbox), 1)
        self.assertEqual(len(app.text_area), 1)
        self.assertEqual(len(app.form_submit_button), 1)

        task_input = app.text_area(key="agent_task")
        task_input.set_value("只计算当前患者的心率，不评估ASA")
        self.assertEqual(
            app.text_area(key="agent_task").value,
            "只计算当前患者的心率，不评估ASA",
        )

    def test_twin_lab_reacts_to_blood_pressure_and_faults(self):
        app = AppTest.from_file("../app.py").run(timeout=20)
        app.session_state["main_workspace_tab"] = "数字孪生推演"
        app.run(timeout=20)
        self.assertFalse(app.exception)

        app.slider(key="twin_sbp_陈伟").set_value(185).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertIn("III 级", app.metric[2].value)

        app.segmented_control(key="twin_scenario").set_value("波形平直").run(
            timeout=20
        )
        self.assertFalse(app.exception)
        self.assertTrue(app.error)


if __name__ == "__main__":
    unittest.main()
