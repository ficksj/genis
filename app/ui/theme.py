"""Тема Genis: чёрно-зелёный «терминал» с пиксельной обезьяной."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ..paths import assets_dir
from .fonts import load_fonts

# --- палитра ---------------------------------------------------------------
BG = "#050907"
SIDEBAR_BG = "#070D0A"
SURFACE = "#0B1410"
SURFACE_2 = "#101C15"
SURFACE_3 = "#08110C"
BORDER = "#1B2C21"
BORDER_LIGHT = "#27412F"
TEXT = "#E9F6EE"
TEXT_SOFT = "#C9E3D4"
MUTED = "#8AA894"
MUTED_DIM = "#63806F"
PREVIEW_BG = "#06100A"
ACCENT = "#35F08A"
ACCENT_BRIGHT = "#8CFFC0"
ACCENT_DIM = "#1FBF63"
ACCENT_SOFT = "#0F2A1B"
ACCENT_PRESS = "#22C46D"
DARK_INK = "#04120A"
DANGER = "#FF6B6B"
DANGER_SOFT = "#2A1114"
WARN = "#F5C451"
WARN_SOFT = "#2A2210"

_TEMPLATE = """
* {{
    font-family: "{ui}";
    font-size: 13px;
    outline: none;
}}

QMainWindow, QDialog {{
    background: {bg};
    color: {text};
}}
QWidget {{
    color: {text};
}}
QToolTip {{
    background: {surface_2};
    color: {text};
    border: 1px solid {border_light};
    border-radius: 8px;
    padding: 6px 9px;
}}

/* --- карточки ---------------------------------------------------------- */
QFrame#Card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 16px;
}}
QFrame#HeroCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {surface_2}, stop:1 #0A1510);
    border: 1px solid {border_light};
    border-radius: 18px;
}}
QFrame#SidebarFrame {{
    background: {sidebar_bg};
    border-right: 1px solid {border};
}}
QFrame#Divider {{
    background: {border};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

/* --- типографика ------------------------------------------------------- */
QLabel#H1 {{
    font-size: 26px;
    font-weight: 800;
    color: {text};
    letter-spacing: -0.4px;
}}
QLabel#H2 {{
    font-size: 14px;
    font-weight: 700;
    color: {text};
}}
QLabel#DialogTitle {{
    font-size: 21px;
    font-weight: 800;
    color: {text};
    letter-spacing: -0.3px;
}}
QLabel#H3 {{
    font-size: 11px;
    font-weight: 700;
    color: {muted};
    letter-spacing: 1.2px;
}}
QLabel#Muted {{
    color: {muted};
    font-size: 12px;
}}
QLabel#Mono {{
    font-family: "{mono}";
    color: {muted};
    font-size: 11px;
}}
QLabel#StatValue {{
    font-size: 24px;
    font-weight: 800;
    color: {text};
    letter-spacing: -0.5px;
}}
QLabel#StatLabel {{
    font-size: 10px;
    font-weight: 700;
    color: {muted_dim};
    letter-spacing: 1.4px;
}}
QLabel#HeroGesture {{
    font-size: 38px;
    font-weight: 800;
    color: {accent};
    letter-spacing: -1px;
}}
QLabel#HeroGesture[state="idle"] {{
    font-size: 30px;
    color: {muted_dim};
}}
QLabel#HeroAction {{
    font-size: 13px;
    color: {text_soft};
}}
QLabel#Brand {{
    font-size: 19px;
    font-weight: 800;
    color: {text};
    letter-spacing: 0.4px;
}}
QLabel#BrandSub {{
    font-size: 10px;
    font-weight: 600;
    color: {muted_dim};
    letter-spacing: 0.8px;
}}
QLabel#Footer {{
    font-size: 10px;
    color: {muted_dim};
}}
QLabel#FooterStrong {{
    font-size: 11px;
    font-weight: 700;
    color: {accent_dim};
}}
QLabel#SectionKicker {{
    font-size: 10px;
    font-weight: 700;
    color: {accent_dim};
    letter-spacing: 1.6px;
}}
QLabel#Chip {{
    background: {surface_3};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 3px 8px;
    color: {muted};
    font-family: "{mono}";
    font-size: 10px;
}}

QLabel#StatusPill {{
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
QLabel#StatusPill[state="on"] {{
    background: rgba(53, 240, 138, 0.12);
    color: {accent};
    border: 1px solid rgba(53, 240, 138, 0.38);
}}
QLabel#StatusPill[state="pause"] {{
    background: rgba(245, 196, 81, 0.12);
    color: {warn};
    border: 1px solid rgba(245, 196, 81, 0.36);
}}
QLabel#StatusPill[state="off"] {{
    background: rgba(255, 107, 107, 0.12);
    color: #FF9AA5;
    border: 1px solid rgba(255, 107, 107, 0.36);
}}

QLabel#Preview {{
    background: #06100A;
    border: 1px solid {border};
    border-radius: 14px;
    color: {muted_dim};
}}
QLabel#AboutLogo {{
    background: transparent;
}}

/* --- кнопки ------------------------------------------------------------ */
QPushButton {{
    background: {surface_2};
    border: 1px solid {border_light};
    border-radius: 10px;
    padding: 9px 15px;
    color: {text};
    font-weight: 600;
}}
QPushButton:hover {{
    background: #16261C;
    border-color: #35563F;
}}
QPushButton:pressed {{
    background: #0C1A12;
}}
QPushButton:disabled {{
    color: {muted_dim};
    background: {surface_3};
    border-color: {border};
}}
QPushButton#Primary {{
    background: {accent};
    border: 1px solid {accent};
    color: {dark_ink};
    font-weight: 800;
}}
QPushButton#Primary:hover {{
    background: {accent_bright};
    border-color: {accent_bright};
}}
QPushButton#Primary:pressed {{
    background: {accent_press};
    border-color: {accent_press};
}}
QPushButton#Primary:disabled {{
    background: #14321F;
    border-color: #14321F;
    color: #4E6B5A;
}}
QPushButton#Ghost {{
    background: transparent;
    border: 1px solid {border_light};
    color: {text_soft};
    font-weight: 600;
}}
QPushButton#Ghost:hover {{
    background: {surface_2};
    border-color: #3B6446;
}}
QPushButton#Danger {{
    background: {danger_soft};
    border: 1px solid #59242B;
    color: #FF9AA5;
}}
QPushButton#Danger:hover {{
    background: #3A171C;
    border-color: #7A3038;
}}
QPushButton#Link {{
    background: transparent;
    border: none;
    color: {accent_dim};
    padding: 2px 4px;
    font-weight: 600;
}}
QPushButton#Link:hover {{
    color: {accent};
}}
QPushButton#Nav {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 9px;
    padding: 11px 14px;
    color: {muted};
    font-size: 13px;
    font-weight: 700;
    text-align: left;
}}
QPushButton#Nav:hover {{
    background: #0E1A13;
    color: {text};
}}
QPushButton#Nav:checked {{
    background: {accent_soft};
    border-left: 2px solid {accent};
    color: {accent};
}}

/* --- поля ввода -------------------------------------------------------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {surface_3};
    border: 1px solid {border_light};
    border-radius: 9px;
    padding: 8px 10px;
    color: {text};
    selection-background-color: {accent_dim};
    selection-color: {dark_ink};
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: #35603F;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {accent};
}}
QLineEdit:read-only {{
    color: {text_soft};
    background: #071009;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {surface_2};
    border-left: 1px solid {border};
    width: 20px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    border-top-right-radius: 9px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    border-bottom-right-radius: 9px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: #1A2C20;
}}
{spin_arrows}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
{combo_arrow}
QComboBox QAbstractItemView {{
    background: {surface_2};
    border: 1px solid {border_light};
    border-radius: 10px;
    padding: 5px;
    selection-background-color: {accent_soft};
    selection-color: {accent};
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 7px 8px;
    border-radius: 6px;
    min-height: 20px;
}}

QCheckBox {{
    spacing: 9px;
    color: {text_soft};
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {border_light};
    background: {surface_3};
}}
QCheckBox::indicator:hover {{
    border-color: {accent_dim};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
    {check_rule}
}}

QSlider::groove:horizontal {{
    height: 5px;
    background: {border};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {accent_dim};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: {accent};
}}

/* --- прокрутка --------------------------------------------------------- */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #223A2A;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #2F5238;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    height: 10px;
    background: transparent;
}}
QScrollBar::handle:horizontal {{
    background: #223A2A;
    border-radius: 5px;
}}

/* --- журнал, меню, прочее --------------------------------------------- */
QPlainTextEdit#Log {{
    background: #060D09;
    border: 1px solid {border};
    border-radius: 12px;
    color: #A9CDB8;
    padding: 10px;
    font-family: "{mono}";
    font-size: 11px;
}}
QProgressBar {{
    background: {surface_3};
    border: 1px solid {border_light};
    border-radius: 7px;
    height: 12px;
    text-align: center;
    font-size: 10px;
    color: {text};
}}
QProgressBar::chunk {{
    background: {accent_dim};
    border-radius: 6px;
}}
QMenu {{
    background: {surface_2};
    border: 1px solid {border_light};
    border-radius: 12px;
    padding: 7px;
}}
QMenu::item {{
    padding: 8px 28px 8px 12px;
    border-radius: 8px;
    color: {text};
}}
QMenu::item:selected {{
    background: {accent_soft};
    color: {accent};
}}
QMenu::item:disabled {{
    color: {muted_dim};
}}
QMenu::separator {{
    height: 1px;
    background: {border};
    margin: 6px 8px;
}}
QStatusBar {{
    background: {sidebar_bg};
    color: {muted};
}}
QMessageBox {{
    background: {surface};
}}
QTabWidget::pane {{
    border: none;
}}
"""


def _asset_url(name: str) -> str:
    path = assets_dir() / "icons" / name
    if path.exists():
        return str(path).replace("\\", "/")
    return ""


def stylesheet(ui_family: str, mono_family: str) -> str:
    check = _asset_url("check.png")
    chevron_down = _asset_url("chevron-down.png")
    chevron_up = _asset_url("chevron-up.png")

    check_rule = f'image: url("{check}");' if check else ""
    if chevron_down:
        combo_arrow = (
            f'QComboBox::down-arrow {{ image: url("{chevron_down}");'
            " width: 14px; height: 14px; }"
        )
    else:
        combo_arrow = "QComboBox::down-arrow { image: none; width: 0; height: 0; }"

    if chevron_down and chevron_up:
        spin_arrows = (
            f'QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{chevron_up}");'
            " width: 10px; height: 10px; }"
            f'QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{chevron_down}");'
            " width: 10px; height: 10px; }"
        )
    else:
        spin_arrows = ""

    return _TEMPLATE.format(
        ui=ui_family,
        mono=mono_family,
        check_rule=check_rule,
        combo_arrow=combo_arrow,
        spin_arrows=spin_arrows,
        bg=BG,
        sidebar_bg=SIDEBAR_BG,
        surface=SURFACE,
        surface_2=SURFACE_2,
        surface_3=SURFACE_3,
        border=BORDER,
        border_light=BORDER_LIGHT,
        text=TEXT,
        text_soft=TEXT_SOFT,
        muted=MUTED,
        muted_dim=MUTED_DIM,
        accent=ACCENT,
        accent_bright=ACCENT_BRIGHT,
        accent_dim=ACCENT_DIM,
        accent_soft=ACCENT_SOFT,
        accent_press=ACCENT_PRESS,
        dark_ink=DARK_INK,
        danger=DANGER,
        danger_soft=DANGER_SOFT,
        warn=WARN,
        warn_soft=WARN_SOFT,
    )


def apply_theme(app: QApplication) -> None:
    """Шрифты + стили. Вызывать до создания окон."""
    ui, mono = load_fonts()
    font = QFont(ui)
    font.setPixelSize(13)
    app.setFont(font)
    app.setStyleSheet(stylesheet(ui, mono))


# Совместимость: раньше модуль экспортировал готовую строку.
STYLESHEET = stylesheet("Manrope", "JetBrains Mono")

__all__ = ["apply_theme", "stylesheet", "STYLESHEET"]
