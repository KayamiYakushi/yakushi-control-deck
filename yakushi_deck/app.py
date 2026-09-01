from __future__ import annotations

from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from .core.paths import BACKUPS, CONFIG
from .core.history import revert_latest
from .core.theme import repair_rasi_compatibility
from .core.windowing import ensure_control_deck_floating
from .ui.common import install_css, open_folder, open_uri
from .ui.pages import (
    AppearancePage,
    DisplaysPage,
    InputPage,
    PowerPage,
    LockPage,
    LoginPage,
    NautilusPage,
    RofiPage,
    TerminalPage,
    ThemePage,
    WallpaperPage,
    WaybarPage,
)

APP_ID = "dev.yakushi.ControlDeckLite"


class Window(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(
            application=app,
            title="薬 Yakushi Control Deck",
            default_width=1190,
            default_height=820,
        )
        self.add_css_class("yakushi-window")
        self.set_size_request(980, 700)

        overlay = Gtk.Overlay()
        self.set_child(overlay)

        frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        frame.add_css_class("outer-frame")
        overlay.set_child(frame)

        for halign, valign in [
            (Gtk.Align.START, Gtk.Align.START),
            (Gtk.Align.END, Gtk.Align.START),
            (Gtk.Align.START, Gtk.Align.END),
            (Gtk.Align.END, Gtk.Align.END),
        ]:
            mark = Gtk.Label(label="+")
            mark.add_css_class("corner-mark")
            mark.set_halign(halign)
            mark.set_valign(valign)
            mark.set_margin_start(8)
            mark.set_margin_end(8)
            mark.set_margin_top(5)
            mark.set_margin_bottom(5)
            overlay.add_overlay(mark)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.add_css_class("sidebar")
        sidebar.set_size_request(248, -1)
        frame.append(sidebar)

        brand = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        brand.add_css_class("brand-panel")

        brand_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        symbol = Gtk.Label(label="薬")
        symbol.add_css_class("brand-symbol")
        brand_top.append(symbol)

        brand_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        brand_name = Gtk.Label(label="YAKUSHI", xalign=0)
        brand_name.add_css_class("brand-name")
        brand_text.append(brand_name)

        brand_sub = Gtk.Label(label="// CONTROL_DECK_", xalign=0)
        brand_sub.add_css_class("brand-sub")
        brand_text.append(brand_sub)

        brand_top.append(brand_text)
        brand.append(brand_top)
        sidebar.append(brand)

        self.search = Gtk.SearchEntry(placeholder_text="Search settings...")
        self.search.add_css_class("search")
        self.search.connect("search-changed", self.filter_navigation)
        sidebar.append(self.search)

        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        nav_scroll.set_vexpand(True)

        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        nav.add_css_class("nav")
        nav_scroll.set_child(nav)
        sidebar.append(nav_scroll)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(130)

        self.nav_items = []

        sections = [
            (
                "01",
                "DEVICES",
                [
                    ("displays", "Displays", "表示", DisplaysPage),
                    ("input", "Input", "入力", InputPage),
                    ("power", "Power", "電力", PowerPage),
                ],
            ),
            (
                "02",
                "DESKTOP",
                [
                    ("appearance", "Appearance", "外観", AppearancePage),
                    ("wallpapers", "Wallpapers", "壁紙", WallpaperPage),
                    ("theme", "Theme Studio", "色彩", ThemePage),
                    ("waybar", "Bar Studio", "帯", WaybarPage),
                ],
            ),
            (
                "03",
                "APPS & KEYS",
                [
                    ("terminal", "Terminal", "端末", TerminalPage),
                    ("nautilus", "Nautilus", "書類", NautilusPage),
                    ("rofi", "Rofi", "起動", RofiPage),
                ],
            ),
            (
                "04",
                "SESSION",
                [
                    ("lock", "Lock Screen", "施錠", LockPage),
                    ("login", "Login Screen", "ログイン", LoginPage),
                ],
            ),
        ]

        first_button = None

        for number, section_name, entries in sections:
            section = Gtk.Label(label=f"{number}  {section_name}", xalign=0)
            section.add_css_class("section-label")
            nav.append(section)

            for page_id, label, jp, page_class in entries:
                page = page_class()
                self.stack.add_named(page, page_id)

                button = Gtk.Button()
                button.add_css_class("nav-button")
                button.set_hexpand(True)

                content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

                english = Gtk.Label(label=label, xalign=0)
                english.set_hexpand(True)
                content.append(english)

                japanese = Gtk.Label(label=jp, xalign=1)
                japanese.add_css_class("nav-jp")
                content.append(japanese)

                button.set_child(content)
                button.connect("clicked", self.navigate, page_id)
                nav.append(button)

                item = {
                    "button": button,
                    "label": label.lower(),
                    "section": section_name.lower(),
                }
                self.nav_items.append(item)

                if page_id == "appearance":
                    first_button = button

        if first_button:
            first_button.add_css_class("selected")
            self.stack.set_visible_child_name("appearance")

        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        footer.add_css_class("sidebar-footer")

        status = Gtk.Label(label="YAKUSHIS FAV SONG", xalign=0)
        status.add_css_class("footer-label")
        footer.append(status)

        barcode_button = Gtk.Button(label="▌▌ ▏▌▌▌ ▏▌ ▌▌ ▏▌▌▌▌ ▏▌")
        barcode_button.add_css_class("barcode-button")
        barcode_button.set_halign(Gtk.Align.FILL)
        barcode_button.connect(
            "clicked",
            lambda *_: open_uri("https://open.spotify.com/track/5QKiW2Oogj7T5KoI1Wcl2u"),
        )
        footer.append(barcode_button)

        barcode_note = Gtk.Label(label="SCAN // CHASE BY BATTA", xalign=0)
        barcode_note.add_css_class("barcode-note")
        footer.append(barcode_note)

        sidebar.append(footer)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main.set_hexpand(True)
        frame.append(main)

        utility = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        utility.add_css_class("utility-bar")

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        utility.append(spacer)

        self.revert_status = Gtk.Label()
        self.revert_status.add_css_class("utility-status")
        utility.append(self.revert_status)

        revert = Gtk.Button(label="REVERT LAST")
        revert.add_css_class("flat")
        revert.add_css_class("revert-button")
        revert.set_tooltip_text(
            "Undo the most recent change made by Yakushi Control Deck."
        )
        revert.connect("clicked", self.revert_last)
        utility.append(revert)

        files = Gtk.Button(label="FILES")
        files.add_css_class("flat")
        files.add_css_class("utility-button")
        files.connect("clicked", lambda *_: open_folder(CONFIG))
        utility.append(files)

        backups = Gtk.Button(label="BACKUPS")
        backups.add_css_class("flat")
        backups.add_css_class("utility-button")
        backups.connect("clicked", lambda *_: open_folder(BACKUPS))
        utility.append(backups)

        main.append(utility)

        self.content_scroll = Gtk.ScrolledWindow()
        self.content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content_scroll.set_hexpand(True)
        self.content_scroll.set_vexpand(True)
        self.content_scroll.set_child(self.stack)
        main.append(self.content_scroll)

    def revert_last(self, *_):
        _ok, message = revert_latest()
        self.revert_status.set_text(message)

    def _scroll_content_to_top(self):
        adjustment = self.content_scroll.get_vadjustment()
        adjustment.set_value(adjustment.get_lower())
        return GLib.SOURCE_REMOVE

    def navigate(self, button, page_id):
        for item in self.nav_items:
            item["button"].remove_css_class("selected")

        button.add_css_class("selected")
        self.stack.set_visible_child_name(page_id)

        # The main ScrolledWindow wraps the whole Gtk.Stack, so without an
        # explicit reset its vertical adjustment carries over to the next
        # page. Reset after the child switch has been queued so every section
        # opens from its header instead of inheriting the previous page scroll.
        GLib.idle_add(self._scroll_content_to_top)

    def filter_navigation(self, entry):
        query = entry.get_text().strip().lower()

        for item in self.nav_items:
            visible = (
                not query
                or query in item["label"]
                or query in item["section"]
            )
            item["button"].set_visible(visible)


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self._float_attempts = 0

    def _float_window(self):
        self._float_attempts += 1
        if ensure_control_deck_floating() or self._float_attempts >= 12:
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def do_activate(self):
        window = self.props.active_window
        if window is None:
            window = Window(self)
        window.present()

        # The Wayland surface appears slightly after present(). Retry briefly
        # and target this process' exact Hyprland client, never an unrelated
        # active window.
        self._float_attempts = 0
        GLib.timeout_add(120, self._float_window)


def main():
    repair_rasi_compatibility()
    install_css("""
        * {
            color: #d9d3cf;
        }

        window.yakushi-window {
            background-color: #050607;
        }

        .outer-frame {
            background-color: #060708;
            border: 1px solid #6d252b;
            border-radius: 2px;
        }

        .corner-mark {
            color: #713138;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 13px;
        }

        .sidebar {
            background-color: #07090a;
            border-right: 1px solid #242326;
            padding: 18px 16px 14px 16px;
        }

        .brand-panel {
            border: 1px solid #343036;
            padding: 13px;
            margin-bottom: 3px;
        }

        .brand-symbol {
            color: #c45b68;
            font-size: 26px;
            font-weight: 800;
        }

        .brand-name {
            color: #ded8d3;
            font-size: 14px;
            font-weight: 800;
        }

        .brand-sub {
            color: #756b69;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
        }

        .search {
            background-color: #090b0c;
            border: 1px solid #2a282b;
            border-radius: 4px;
            min-height: 34px;
            padding: 0 8px;
            color: #c8c1bd;
        }

        .nav {
            padding-top: 5px;
        }

        .section-label {
            color: #756a69;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            font-weight: 700;
            padding: 12px 8px 5px 8px;
        }

        .nav-button {
            background-color: transparent;
            border: none;
            border-radius: 5px;
            box-shadow: none;
            padding: 8px 10px;
            min-height: 30px;
            color: #a9a19e;
        }

        .nav-button:hover {
            background-color: #101214;
        }

        .nav-button:checked {
            background-color: #d8d0c8;
            color: #181517;
        }

        .nav-button:checked label {
            color: #181517;
        }

        .nav-jp {
            color: #5e5756;
            font-size: 10px;
        }

        .nav-button:checked .nav-jp {
            color: #6b5451;
        }

        .sidebar-footer {
            border-top: 1px solid #252326;
            padding: 12px 7px 3px 7px;
        }

        .footer-label {
            color: #766765;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
            font-weight: 700;
        }

        .barcode {
            color: #b6aca6;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 10px;
        }

        .utility-bar {
            min-height: 42px;
            padding: 8px 16px 3px 16px;
        }

        .utility-button {
            background-color: #0a0b0c;
            color: #8f8582;
            border: 1px solid #2a282b;
            border-radius: 3px;
            padding: 4px 11px;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
        }

        .utility-button:hover {
            color: #d4cbc7;
            border-color: #513038;
        }

        .page {
            background-color: transparent;
        }

        .meta {
            color: #716865;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            font-weight: 700;
        }

        .page-title {
            color: #e3dcd7;
            font-family: serif;
            font-size: 34px;
            font-weight: 700;
        }

        .page-subtitle {
            color: #746e6c;
            font-size: 12px;
            margin-bottom: 3px;
        }

        .deck-card {
            background-color: #08090a;
            border: 1px solid #2b292c;
            border-radius: 4px;
            padding: 16px;
        }

        .card-title {
            color: #9f9491;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 10px;
            font-weight: 700;
        }

        .muted {
            color: #6e6866;
            font-size: 11px;
        }

        .setting-row {
            padding: 8px 0;
        }

        .setting-name {
            color: #c9c1bd;
            font-size: 12px;
            font-weight: 600;
        }

        entry,
        spinbutton,
        dropdown {
            background-color: #0b0d0e;
            border: 1px solid #2a282b;
            border-radius: 4px;
            padding: 6px 8px;
            min-width: 135px;
        }

        scale trough {
            background-color: #161719;
            min-height: 4px;
            border-radius: 0;
        }

        scale highlight {
            background-color: #98404c;
            min-height: 4px;
        }

        scale slider {
            min-width: 12px;
            min-height: 12px;
            border-radius: 0;
            background-color: #d4cbc6;
        }

        switch {
            background-color: #171719;
            border-radius: 12px;
        }

        switch:checked {
            background-color: #813842;
        }

        .value-readout {
            color: #8c817f;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 10px;
            border: 1px solid #29272a;
            padding: 5px;
        }

        button {
            background-color: #0c0e0f;
            color: #b9b0ac;
            border: 1px solid #302d30;
            border-radius: 4px;
            box-shadow: none;
            padding: 8px 12px;
        }

        button:hover {
            background-color: #131517;
            border-color: #4b3035;
        }

        button.primary {
            background-color: #a74a58;
            color: #0a0809;
            border-color: #c96573;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 10px;
            font-weight: 800;
        }

        .preset-card {
            background-color: #090b0c;
            border: 1px solid #2a282b;
            min-height: 106px;
            padding: 13px;
        }

        .preset-card:hover {
            background-color: #110c0f;
            border-color: #65333b;
        }

        .preset-title {
            color: #b7aaa6;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 10px;
            font-weight: 800;
        }

        .status {
            color: #a85b66;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            padding-top: 3px;
        }

        .monitor-summary {
            color: #a85b66;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 10px;
            padding: 2px 0 8px 0;
        }

        .wallpaper-tile {
            padding: 0;
            background-color: #0a0b0c;
            border: 1px solid #29272a;
        }

        .wallpaper-tile:hover {
            border-color: #75333c;
        }

        .wallpaper-label {
            background-color: rgba(4, 5, 6, 0.82);
            padding: 6px;
        }

        .wallpaper-name {
            color: #e0d9d4;
            font-size: 10px;
            font-weight: 700;
        }

        .wallpaper-folder {
            color: #7b7270;
            font-size: 8px;
        }

        .color-chip {
            background-color: #0a0b0c;
            border: 1px solid #29272a;
            padding: 10px;
        }

        colorbutton button {
            min-height: 38px;
        }

        .terminal-preview {
            background-color: #070809;
            border: 1px solid #29272a;
            padding: 14px;
        }

        .terminal-preview label {
            color: #b44f5e;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 11px;
        }

        .rofi-preview {
            background-color: #0c0b0c;
            border: 1px solid #393035;
            padding: 14px;
        }

        .rofi-preview-search {
            background-color: #171315;
            color: #c86672;
            border: 1px solid #3b3034;
            padding: 9px 12px;
        }

        .rofi-preview-item {
            color: #c8c0bc;
            padding: 7px 10px;
        }

        /* Preview 2: navigation contrast and module studio */
        button.nav-button {
            background-image: none;
            background-color: transparent;
            color: #a79f9c;
            border: 1px solid transparent;
            box-shadow: none;
        }

        button.nav-button label {
            color: #a79f9c;
        }

        button.nav-button:hover {
            background-image: none;
            background-color: #111315;
            border-color: #242327;
        }

        button.nav-button:checked {
            background-image: none;
            background-color: #d8d0c8;
            border-color: #d8d0c8;
        }

        button.nav-button:checked label {
            color: #171416;
        }

        button.nav-button .nav-jp {
            color: #68605e;
        }

        button.nav-button:checked .nav-jp {
            color: #725d59;
        }

        .revert-button {
            background-image: none;
            background-color: #24171a;
            border: 1px solid #6d313a;
            color: #d98a96;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            font-weight: 800;
        }

        .revert-button:hover {
            background-color: #3a2026;
            border-color: #a54a58;
            color: #f0a4ae;
        }

        .utility-status {
            color: #8a6267;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
            margin-right: 4px;
        }

        .module-lane {
            background-color: #070809;
            border: 1px solid #29272a;
            padding: 9px;
        }

        .module-lane-header {
            border-bottom: 1px solid #252326;
            padding-bottom: 7px;
            margin-bottom: 1px;
        }

        .module-lane-title {
            color: #a79b98;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            font-weight: 800;
        }

        .module-lane-count {
            color: #99505a;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
        }

        .module-chip {
            background-color: #0d0f10;
            border: 1px solid #302d30;
            padding: 8px;
        }

        .module-chip:hover {
            background-color: #121416;
            border-color: #61333a;
        }

        .module-handle {
            color: #8d4b55;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 14px;
        }

        .module-name {
            color: #d2c9c5;
            font-size: 11px;
            font-weight: 650;
        }

        .module-id {
            color: #675f5d;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
        }

        button.module-action {
            background-image: none;
            background-color: #151719;
            border: 1px solid #353135;
            color: #8e8481;
            padding: 4px 7px;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
        }

        button.module-action:hover {
            background-color: #26171b;
            border-color: #6c333c;
            color: #d38490;
        }

        .module-empty {
            color: #4f4948;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            padding: 18px;
        }

        /* Preview 3: force native GTK controls onto the Yakushi dark surface. */

        button {
            background: #090b0c;
            background-image: none;
            color: #b9b0ac;
            border: 1px solid #302d30;
            box-shadow: none;
        }

        button label {
            color: #b9b0ac;
        }

        button:hover {
            background: #121416;
            background-image: none;
            color: #ded6d1;
            border-color: #503038;
        }

        button:hover label {
            color: #ded6d1;
        }

        button.primary {
            background: #090b0c;
            background-image: none;
            color: #d77784;
            border: 1px solid #9b404e;
        }

        button.primary label {
            color: #d77784;
        }

        button.primary:hover {
            background: #1a1013;
            background-image: none;
            color: #ef9da8;
            border-color: #c25565;
        }

        button.primary:hover label {
            color: #ef9da8;
        }

        button.nav-button {
            background: #07090a;
            background-image: none;
            color: #aaa29f;
            border: 1px solid transparent;
            box-shadow: none;
        }

        button.nav-button label {
            color: #aaa29f;
        }

        button.nav-button:hover {
            background: #111315;
            background-image: none;
            border-color: #262428;
        }

        button.nav-button:hover label {
            color: #d5cdca;
        }

        button.nav-button.selected {
            background: #dedbd6;
            background-image: none;
            border-color: #dedbd6;
            color: #111214;
        }

        button.nav-button.selected label {
            color: #111214;
        }

        button.nav-button .nav-jp {
            color: #655e5c;
        }

        button.nav-button.selected .nav-jp {
            color: #5e5351;
        }

        button.utility-button,
        button.revert-button,
        button.module-action,
        button.preset-card,
        button.wallpaper-tile {
            background-image: none;
        }

        button.utility-button {
            background: #090b0c;
            color: #8f8582;
        }

        button.utility-button label {
            color: #8f8582;
        }

        button.revert-button {
            background: #160f11;
            color: #d37c88;
        }

        button.revert-button label {
            color: #d37c88;
        }

        button.preset-card {
            background: #090b0c;
        }

        button.wallpaper-tile {
            background: #08090a;
        }

        button.module-action {
            background: #0d0f10;
        }

        dropdown,
        dropdown > button,
        dropdown button {
            background: #090b0c;
            background-image: none;
            color: #c7bfbb;
            border-color: #302d30;
        }

        dropdown label,
        dropdown > button label,
        dropdown button label {
            color: #c7bfbb;
        }

        dropdown:hover,
        dropdown > button:hover,
        dropdown button:hover {
            background: #121416;
            background-image: none;
        }

        popover,
        popover contents,
        popover listview,
        popover row {
            background: #090b0c;
            color: #c7bfbb;
        }

        popover row:hover,
        popover row:selected {
            background: #1a1114;
            color: #e8deda;
        }

        colorbutton button {
            background: #090b0c;
            background-image: none;
            border: 1px solid #302d30;
        }

        colorbutton button:hover {
            background: #111315;
            background-image: none;
        }

        spinbutton button {
            background: #0b0d0e;
            background-image: none;
        }

        spinbutton button label {
            color: #c7bfbb;
        }

        .session-wallpaper-preview {
            background: #070809;
            border: 1px solid #302d30;
            border-radius: 4px;
        }

        .sddm-preview-card {
            min-height: 250px;
            background: #090a0b;
            border: 1px solid #3f292a;
            padding: 28px;
        }

        .sddm-preview-symbol {
            color: #e8a29a;
            font-size: 34px;
            font-weight: 800;
        }

        .sddm-preview-time {
            color: #e8a29a;
            font-family: serif;
            font-size: 48px;
            font-weight: 700;
        }

        .sddm-preview-field {
            color: #8e7370;
            background: #1a1414;
            border: 1px solid #3f292a;
            border-radius: 4px;
            padding: 12px 18px;
        }

        checkbutton {
            color: #b9b0ac;
            padding: 5px 0;
        }

        checkbutton check {
            background: #090b0c;
            background-image: none;
            border: 1px solid #3a3437;
            border-radius: 3px;
            min-width: 16px;
            min-height: 16px;
        }

        checkbutton check:checked {
            background: #a74a58;
            background-image: none;
            border-color: #c96573;
        }

        .barcode-button {
            background: transparent;
            background-image: none;
            color: #c9bdb8;
            border: 1px solid transparent;
            border-radius: 2px;
            padding: 2px 0;
            text-align: left;
            min-height: 24px;
        }

        .barcode-button:hover {
            background: #0d1011;
            background-image: none;
            border-color: #2e2b2e;
            color: #f0e4dd;
        }

        .barcode-button label {
            color: inherit;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 10px;
        }

        .barcode-note {
            color: #6f6462;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
            font-weight: 700;
        }

        .palette-swatch {
            min-height: 16px;
            min-width: 16px;
            border-radius: 999px;
            border: 1px solid #2a2629;
        }

        .waybar-preview {
            background: #08090a;
            border: 1px solid #2b292c;
            border-radius: 4px;
            padding: 10px 12px;
        }

        .waybar-preview-lane {
            spacing: 6px;
        }

        .waybar-preview-chip {
            background: #0e1011;
            border: 1px solid #343136;
            border-radius: 999px;
            padding: 4px 8px;
        }

        .waybar-preview-chip label {
            color: #d0c6c2;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
        }

        .waybar-preview-empty {
            color: #5d5857;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
            padding: 4px 6px;
        }

        .monitor-map-card {
            min-height: 240px;
        }

        .monitor-map-summary {
            color: #8c817f;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
        }

        .module-desc {
            color: #7b7270;
            font-size: 9px;
        }


        button.theme-preset-card,
        button.power-profile-card {
            background: #090b0c;
            background-image: none;
            border: 1px solid #302d30;
            padding: 11px;
            min-height: 116px;
        }

        button.theme-preset-card:hover,
        button.power-profile-card:hover {
            background: #111315;
            background-image: none;
            border-color: #70404a;
        }

        button.power-profile-card {
            min-height: 96px;
        }

        .wallpaper-current {
            border: 2px solid #c75162;
        }

        .module-preview-text {
            color: #a86a73;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
        }

        .module-chip switch {
            margin-left: 5px;
        }

        .monitor-map-card drawingarea {
            background: #070809;
        }

        .palette-swatch {
            min-width: 18px;
            min-height: 18px;
        }

        /* Preview 6: compact deck-native module controls. */
        button.module-toggle {
            background: #0b0d0f;
            background-image: none;
            color: #766e6b;
            border: 1px solid #343034;
            border-radius: 3px;
            box-shadow: none;
            min-width: 42px;
            min-height: 25px;
            padding: 2px 7px;
            margin-left: 4px;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
            font-weight: 800;
        }

        button.module-toggle label {
            color: #766e6b;
        }

        button.module-toggle:checked {
            background: #32151b;
            background-image: none;
            border-color: #9d4350;
            color: #e18390;
        }

        button.module-toggle:checked label {
            color: #e18390;
        }

        button.module-toggle:hover {
            background: #151719;
            background-image: none;
            border-color: #60313a;
        }

        .module-chip {
            min-height: 64px;
            padding: 7px 8px;
        }

        .module-chip .module-desc {
            color: #696260;
            font-size: 8px;
        }

        .module-handle {
            min-width: 18px;
            color: #a64d59;
        }

        button.utility-button.flat,
        button.revert-button.flat {
            background-image: none;
            box-shadow: none;
            text-shadow: none;
        }

        button.utility-button.flat {
            background-color: #080a0b;
            color: #8f8582;
            border: 1px solid #29272a;
        }

        button.utility-button.flat label {
            color: #8f8582;
        }

        button.utility-button.flat:hover {
            background-color: #111315;
            border-color: #503038;
        }

        button.revert-button.flat {
            background-color: #160f11;
            color: #d37c88;
            border: 1px solid #6d313a;
        }

        button.revert-button.flat label {
            color: #d37c88;
        }


        .typography-preview {
            background: #0b0d0e;
            border: 1px solid #302d30;
            border-radius: 4px;
            padding: 14px 16px;
            color: #e9e2dd;
        }

        button.typography-toggle,
        button.typography-option {
            background: #090b0c;
            background-image: none;
            border: 1px solid #343034;
            color: #9d9390;
            box-shadow: none;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            font-weight: 800;
        }

        button.typography-toggle.active,
        button.typography-option.active {
            background: #2d171b;
            background-image: none;
            border-color: #9f4b57;
            color: #e7a0a8;
        }

        button.typography-toggle.active label,
        button.typography-option.active label {
            color: #e7a0a8;
        }

        button.theme-preset-card {
            min-height: 164px;
        }


        /* Preview 10: deck-native input toggles and pointer diagnostics. */
        button.input-toggle {
            background: #0b0d0f;
            background-image: none;
            color: #766e6b;
            border: 1px solid #343034;
            border-radius: 3px;
            box-shadow: none;
            min-width: 58px;
            min-height: 28px;
            padding: 3px 9px;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 9px;
            font-weight: 800;
        }

        button.input-toggle label {
            color: #766e6b;
        }

        button.input-toggle:checked {
            background: #32151b;
            background-image: none;
            border-color: #9d4350;
            color: #e18390;
        }

        button.input-toggle:checked label {
            color: #e18390;
        }

        .input-device-note {
            color: #756d6a;
            font-family: "JetBrainsMono Nerd Font", monospace;
            font-size: 8px;
            padding: 2px 0 5px 0;
        }
    """)

    App().run([])


if __name__ == "__main__":
    main()
