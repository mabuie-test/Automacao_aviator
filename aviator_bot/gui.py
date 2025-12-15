"""GUI com navegador embutido e persistência de credenciais/endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWebEngineWidgets import QWebEngineView

from . import config
from .runner import check_dependencies, run_loop


class QtLogHandler(QtCore.QObject, logging.Handler):
    """Envio de logs Python para o painel de status da GUI."""

    message_signal = QtCore.pyqtSignal(str)

    def __init__(self) -> None:
        QtCore.QObject.__init__(self)
        logging.Handler.__init__(self)
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        msg = self.format(record)
        self.message_signal.emit(msg)


class RunnerThread(QtCore.QThread):
    finished_signal = QtCore.pyqtSignal(str)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, settings: config.Settings, time_steps: int, warmup_seconds: int) -> None:
        super().__init__()
        self.settings = settings
        self.time_steps = time_steps
        self.warmup_seconds = warmup_seconds

    def run(self) -> None:  # type: ignore[override]
        try:
            config.set_settings(self.settings)
            run_loop(self.time_steps, self.warmup_seconds, settings=self.settings)
            self.finished_signal.emit("Loop encerrado")
        except Exception as exc:  # pylint: disable=broad-except
            self.error_signal.emit(str(exc))


class HealthCheckThread(QtCore.QThread):
    finished_signal = QtCore.pyqtSignal(str)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, settings: config.Settings) -> None:
        super().__init__()
        self.settings = settings

    def run(self) -> None:  # type: ignore[override]
        try:
            config.set_settings(self.settings)
            check_dependencies(self.settings)
            self.finished_signal.emit("Conexões validadas com sucesso.")
        except Exception as exc:  # pylint: disable=broad-except
            self.error_signal.emit(str(exc))


class ConfigForm(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = config.load_persisted_settings()
        self.runner_thread: Optional[RunnerThread] = None
        self.health_thread: Optional[HealthCheckThread] = None
        self.log_handler = QtLogHandler()
        self.log_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
        self.log_handler.message_signal.connect(lambda msg: self._append_status(msg))
        logging.getLogger().addHandler(self.log_handler)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QFormLayout()
        self.aviator_url = QtWidgets.QLineEdit(self.settings.aviator_url)
        self.data_path = QtWidgets.QLineEdit(self.settings.data_path)
        self.platform_user = QtWidgets.QLineEdit(self.settings.platform_user)
        self.platform_password = QtWidgets.QLineEdit(self.settings.platform_password)
        self.platform_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.attach_existing = QtWidgets.QCheckBox("Usar navegador já aberto (debug)")
        self.attach_existing.setChecked(self.settings.attach_to_existing)
        self.chrome_host = QtWidgets.QLineEdit(self.settings.chrome_debug_host)
        self.chrome_port = QtWidgets.QSpinBox()
        self.chrome_port.setMaximum(65535)
        self.chrome_port.setValue(self.settings.chrome_debug_port or 0)
        self.chrome_binary = QtWidgets.QLineEdit(self.settings.chrome_binary or "")
        self.chrome_host.setEnabled(self.attach_existing.isChecked())
        self.chrome_port.setEnabled(self.attach_existing.isChecked())
        self.attach_existing.toggled.connect(self._toggle_debug_fields)

        self.auto_bet = QtWidgets.QCheckBox("Habilitar auto-bet")
        self.auto_bet.setChecked(self.settings.auto_bet)
        self.base_bet = QtWidgets.QDoubleSpinBox()
        self.base_bet.setValue(self.settings.base_bet)
        self.max_bet = QtWidgets.QDoubleSpinBox()
        self.max_bet.setValue(self.settings.max_bet)
        self.confidence_floor = QtWidgets.QDoubleSpinBox()
        self.confidence_floor.setRange(0.0, 1.0)
        self.confidence_floor.setSingleStep(0.05)
        self.confidence_floor.setValue(self.settings.confidence_floor)
        self.streak_window = QtWidgets.QSpinBox()
        self.streak_window.setMinimum(3)
        self.streak_window.setValue(self.settings.streak_window)
        self.warmup_seconds = QtWidgets.QSpinBox()
        self.warmup_seconds.setMinimum(120)
        self.warmup_seconds.setValue(self.settings.warmup_seconds)

        self.bet_selector = QtWidgets.QLineEdit(self.settings.bet_input_selector)
        self.bet_button_selector = QtWidgets.QLineEdit(self.settings.bet_button_selector)
        self.cashout_selector = QtWidgets.QLineEdit(self.settings.cashout_button_selector)
        self.session_ready_selector = QtWidgets.QLineEdit(self.settings.session_ready_selector)
        self.session_ready_timeout = QtWidgets.QSpinBox()
        self.session_ready_timeout.setMinimum(10)
        self.session_ready_timeout.setValue(self.settings.session_ready_timeout)

        form_layout.addRow("Aviator URL", self.aviator_url)
        form_layout.addRow("Arquivo de dados", self.data_path)
        form_layout.addRow("Utilizador", self.platform_user)
        form_layout.addRow("Senha", self.platform_password)
        form_layout.addRow(self.attach_existing)
        form_layout.addRow("Debug Host", self.chrome_host)
        form_layout.addRow("Debug Port", self.chrome_port)
        form_layout.addRow("Binário Opera/Chrome", self.chrome_binary)
        form_layout.addRow(self.auto_bet)
        form_layout.addRow("Aposta Base", self.base_bet)
        form_layout.addRow("Aposta Máxima", self.max_bet)
        form_layout.addRow("Confiança mínima", self.confidence_floor)
        form_layout.addRow("Janela de tendência", self.streak_window)
        form_layout.addRow("Aquecimento (s)", self.warmup_seconds)
        form_layout.addRow("Selector aposta", self.bet_selector)
        form_layout.addRow("Selector botão bet", self.bet_button_selector)
        form_layout.addRow("Selector cashout", self.cashout_selector)
        form_layout.addRow("Selector prontidão", self.session_ready_selector)
        form_layout.addRow("Timeout sessão (s)", self.session_ready_timeout)

        self.start_button = QtWidgets.QPushButton("Iniciar bot")
        self.start_button.clicked.connect(self._start_bot)

        self.health_button = QtWidgets.QPushButton("Testar conexões")
        self.health_button.clicked.connect(self._test_connections)

        self.status = QtWidgets.QTextEdit()
        self.status.setReadOnly(True)
        self.status.append("Carregado configurações persistidas.")

        layout.addLayout(form_layout)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.health_button)
        layout.addLayout(buttons)

        self.web = QWebEngineView()
        self.web.setUrl(QtCore.QUrl(self.settings.aviator_url))
        self.web.urlChanged.connect(self._handle_url_change)
        layout.addWidget(self.web, stretch=1)
        layout.addWidget(self.status)

    def closeEvent(self, event):  # type: ignore[override]
        logging.getLogger().removeHandler(self.log_handler)
        super().closeEvent(event)

    def _toggle_debug_fields(self, checked: bool) -> None:
        self.chrome_host.setEnabled(checked)
        self.chrome_port.setEnabled(checked)

    def _gather_settings(self) -> config.Settings:
        cfg = config.Settings(
            aviator_url=self.aviator_url.text().strip(),
            data_path=self.data_path.text().strip(),
            platform_user=self.platform_user.text().strip(),
            platform_password=self.platform_password.text(),
            attach_to_existing=self.attach_existing.isChecked(),
            chrome_debug_host=self.chrome_host.text().strip(),
            chrome_debug_port=int(self.chrome_port.value()) or None,
            chrome_binary=self.chrome_binary.text().strip() or None,
            auto_bet=self.auto_bet.isChecked(),
            base_bet=float(self.base_bet.value()),
            max_bet=float(self.max_bet.value()),
            confidence_floor=float(self.confidence_floor.value()),
            streak_window=int(self.streak_window.value()),
            bet_input_selector=self.bet_selector.text().strip(),
            bet_button_selector=self.bet_button_selector.text().strip(),
            cashout_button_selector=self.cashout_selector.text().strip(),
            warmup_seconds=int(self.warmup_seconds.value()),
            session_ready_selector=self.session_ready_selector.text().strip(),
            session_ready_timeout=int(self.session_ready_timeout.value()),
        )
        return cfg.validate()

    def _append_status(self, message: str) -> None:
        self.status.append(message)

    def _handle_url_change(self, url: QtCore.QUrl) -> None:
        final_url = url.toString()
        self.aviator_url.setText(final_url)
        self.settings = config.update_and_persist(
            aviator_url=final_url,
            data_path=self.data_path.text().strip(),
            platform_user=self.platform_user.text().strip(),
            platform_password=self.platform_password.text(),
        )
        self._append_status(f"Endpoint ajustado para {final_url}")

    def _start_bot(self) -> None:
        if self.runner_thread and self.runner_thread.isRunning():
            self._append_status("Bot já está rodando.")
            return
        try:
            cfg = self._gather_settings()
        except Exception as exc:  # pylint: disable=broad-except
            QtWidgets.QMessageBox.critical(self, "Erro", str(exc))
            return

        config.persist_settings(cfg)
        self.settings = cfg
        self.web.setUrl(QtCore.QUrl(cfg.aviator_url))
        self._append_status("Configurações salvas e aplicadas. Iniciando loop...")
        self.runner_thread = RunnerThread(cfg, time_steps=12, warmup_seconds=cfg.warmup_seconds)
        self.runner_thread.finished_signal.connect(lambda msg: self._append_status(msg))
        self.runner_thread.error_signal.connect(lambda err: self._append_status(f"Erro: {err}"))
        self.runner_thread.start()

    def _test_connections(self) -> None:
        try:
            cfg = self._gather_settings()
        except Exception as exc:  # pylint: disable=broad-except
            QtWidgets.QMessageBox.critical(self, "Erro", str(exc))
            return

        self.settings = cfg
        self._append_status("Validando arquivo de dados e sessão do navegador...")
        self.health_thread = HealthCheckThread(cfg)
        self.health_thread.finished_signal.connect(lambda msg: self._append_status(msg))
        self.health_thread.error_signal.connect(lambda err: self._append_status(f"Erro: {err}"))
        self.health_thread.start()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Aviator Bot GUI (Opera embutido)")
        self.resize(1200, 900)
        self.form = ConfigForm()
        self.setCentralWidget(self.form)


def launch_gui() -> None:
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    launch_gui()
