from __future__ import annotations

from pathlib import Path
import threading
from urllib.parse import quote
from html import escape

from gi.repository import Gtk, Gdk, GObject, GLib, Pango, GdkPixbuf

from ..core.io import run
from ..core.autocolor import (
    apply as apply_auto_color,
    apply_follow_if_enabled,
    configure as configure_auto_color,
    status as auto_color_status,
)
from ..core.nautilus import (
    apply as apply_nautilus_opacity,
    open_nautilus,
    status as nautilus_status,
)
from ..core.fastfetch import (
    COMMON_MODULES as FASTFETCH_COMMON_MODULES,
    apply_modules as apply_fastfetch_modules,
    load as fastfetch_load,
    preview as preview_fastfetch,
    save_config_text as save_fastfetch_config,
    save_logo as save_fastfetch_logo,
    reset_config as reset_fastfetch_config,
    set_autorun as set_fastfetch_autorun,
    set_logo_padding as set_fastfetch_logo_padding,
    sync_terminal_colors as sync_fastfetch_terminal_colors,
)
from ..core.frame import (
    FrameSettings,
    apply as apply_window_frame,
    status as window_frame_status,
)
from ..core.power import apply_mode as apply_power_mode, status as power_status
from ..core.lockscreen import (
    LockSettings,
    SddmSettings,
    apply_lock,
    disable_sddm,
    install_sddm,
    lock_now,
    lock_status,
    preview_sddm,
    sddm_status,
)

from ..core.apps import (
    KittyState,
    KittyColorState,
    RofiState,
    WaybarState,
    kitty_load,
    kitty_save,
    kitty_apply_preset,
    kitty_colors_load,
    kitty_colors_save,
    rofi_load,
    rofi_save,
    rofi_apply_theme,
    rofi_theme_presets,
    waybar_load,
    waybar_save,
    waybar_apply_preset,
)
from ..core.hypr import (
    apply_appearance,
    apply_keyboard,
    apply_monitor,
    apply_monitor_layout,
    apply_mouse,
    current_monitor_mode,
    monitors,
    normalize_monitor_mode,
    pointer_devices,
    preferred_monitor,
    set_preferred_monitor,
    state,
)
from ..core.theme import Palette, load as load_palette, save as save_palette
from ..core.typography import apply as apply_typography, status as typography_status
from ..core.windowing import ensure_control_deck_floating
from ..core.wallpapers import (
    apply as apply_wallpaper,
    current as current_wallpaper,
    folders as wallpaper_folders,
    recent as recent_wallpapers,
    scan as scan_wallpapers,
)
from .common import (
    action_button,
    card,
    open_uri,
    page_header,
    setting_row,
    slider,
    spin,
)


class Page(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.add_css_class("page")
        self.set_margin_top(24)
        self.set_margin_bottom(30)
        self.set_margin_start(28)
        self.set_margin_end(28)


class PalettePresetCard(Gtk.Button):
    def __init__(self, page, title: str, description: str, palette):
        super().__init__()
        self.page = page
        self.palette = palette
        self.add_css_class("theme-preset-card")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)

        # Mini desktop preview: a dark/light surface, a secondary panel, and a
        # workspace strip like the user's reference.  This makes tonal themes
        # visibly different before the user clicks them.
        preview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        preview_name = f"theme-preview-{id(preview)}"
        preview.set_name(preview_name)
        preview.set_margin_top(2)
        preview.set_margin_bottom(2)
        preview.set_margin_start(2)
        preview.set_margin_end(2)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        top.set_margin_top(10)
        top.set_margin_start(10)
        top.set_margin_end(10)

        glyph = Gtk.Label(label="薬")
        glyph_name = f"theme-glyph-{id(glyph)}"
        glyph.set_name(glyph_name)
        top.append(glyph)

        for label_text in ("1", "2", "3"):
            pill = Gtk.Label(label=label_text)
            pill_name = f"theme-pill-{id(pill)}"
            pill.set_name(pill_name)
            provider = Gtk.CssProvider()
            provider.load_from_data((
                f"#{pill_name} {{ background: {palette.surface_alt}; color: {palette.muted}; "
                f"border: 1px solid {palette.border}; border-radius: 999px; padding: 3px 9px; }}"
            ).encode())
            pill.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            top.append(pill)

        selected = Gtk.Label(label="4")
        selected_name = f"theme-selected-{id(selected)}"
        selected.set_name(selected_name)
        top.append(selected)
        top.set_hexpand(True)
        preview.append(top)

        surface = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        surface_name = f"theme-surface-{id(surface)}"
        surface.set_name(surface_name)
        surface.set_margin_start(10)
        surface.set_margin_end(10)
        surface.set_margin_bottom(10)
        surface.set_margin_top(1)

        heading = Gtk.Label(label="Terminal", xalign=0)
        heading_name = f"theme-heading-{id(heading)}"
        heading.set_name(heading_name)
        heading.set_hexpand(True)
        surface.append(heading)

        dot = Gtk.Label(label="●")
        dot_name = f"theme-dot-{id(dot)}"
        dot.set_name(dot_name)
        surface.append(dot)
        preview.append(surface)

        provider = Gtk.CssProvider()
        provider.load_from_data((
            f"#{preview_name} {{ background: {palette.bg}; border: 1px solid {palette.border}; border-radius: 5px; }}\n"
            f"#{glyph_name} {{ color: {palette.accent}; font-weight: 900; }}\n"
            f"#{selected_name} {{ background: {palette.accent}; color: {palette.selected_fg}; border-radius: 999px; padding: 3px 10px; font-weight: 900; }}\n"
            f"#{surface_name} {{ background: {palette.surface}; border: 1px solid {palette.border}; border-radius: 4px; padding: 9px; }}\n"
            f"#{heading_name} {{ color: {palette.fg}; font-family: serif; font-size: 17px; font-weight: 800; }}\n"
            f"#{dot_name} {{ color: {palette.accent}; }}"
        ).encode())
        for widget in (preview, glyph, selected, surface, heading, dot):
            widget.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        content.append(preview)

        name = Gtk.Label(label=title, xalign=0)
        name.add_css_class("preset-title")
        content.append(name)

        sub = Gtk.Label(label=description, xalign=0)
        sub.add_css_class("muted")
        sub.set_wrap(True)
        content.append(sub)

        self.set_child(content)
        self.connect("clicked", self._apply)

    def _apply(self, *_):
        self.page.load_palette_into_controls(self.palette)
        ok, message = save_palette(self.palette)
        self.page.status.set_text(message)
        if ok:
            self.page.palette = self.palette


class MonitorLayoutPreview(Gtk.DrawingArea):
    def __init__(self, on_changed=None):
        super().__init__()
        self.monitors = []
        self.pending = {}
        self.preferred = ""
        self.on_changed = on_changed
        self.active_name = None
        self.drag_origin = None
        self._last_geometry = {}
        self._last_scale = 1.0

        self.set_content_width(760)
        self.set_content_height(260)
        self.set_draw_func(self._draw)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end", self._drag_end)
        self.add_controller(drag)

    @staticmethod
    def _logical_size(monitor):
        scale = max(float(monitor.get("scale", 1.0)), 0.1)
        return (
            float(monitor.get("width", 0)) / scale,
            float(monitor.get("height", 0)) / scale,
        )

    def set_monitors(self, monitors_list, preferred=""):
        self.monitors = [dict(item) for item in (monitors_list or [])]
        self.pending = {
            monitor.get("name"): {
                "x": int(monitor.get("x", 0)),
                "y": int(monitor.get("y", 0)),
            }
            for monitor in self.monitors
        }
        self.preferred = preferred or ""
        self.queue_draw()

    def positions(self):
        return {name: dict(value) for name, value in self.pending.items()}

    def _bounds(self):
        if not self.monitors:
            return (0, 0, 1, 1)

        x1, y1, x2, y2 = [], [], [], []
        for monitor in self.monitors:
            name = monitor.get("name")
            pos = self.pending.get(name, {"x": 0, "y": 0})
            w, h = self._logical_size(monitor)
            x1.append(pos["x"])
            y1.append(pos["y"])
            x2.append(pos["x"] + w)
            y2.append(pos["y"] + h)
        return min(x1), min(y1), max(x2), max(y2)

    def _geometry(self, width, height):
        margin = 22
        min_x, min_y, max_x, max_y = self._bounds()
        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)
        scale = min(
            max(width - margin * 2, 10) / span_x,
            max(height - margin * 2, 10) / span_y,
        )
        scale = max(scale, 0.02)

        result = {}
        for monitor in self.monitors:
            name = monitor.get("name")
            pos = self.pending.get(name, {"x": 0, "y": 0})
            logical_w, logical_h = self._logical_size(monitor)
            result[name] = (
                margin + (pos["x"] - min_x) * scale,
                margin + (pos["y"] - min_y) * scale,
                max(logical_w * scale, 84),
                max(logical_h * scale, 54),
            )
        return result, scale

    def _draw(self, _area, cr, width, height):
        cr.set_source_rgb(0.03, 0.04, 0.05)
        cr.paint()

        cr.set_source_rgba(0.15, 0.14, 0.15, 1.0)
        cr.rectangle(1, 1, width - 2, height - 2)
        cr.set_line_width(1)
        cr.stroke()

        if not self.monitors:
            cr.set_source_rgb(0.42, 0.39, 0.39)
            cr.move_to(22, height / 2)
            cr.show_text("No display data available.")
            return

        geometry, scale = self._geometry(width, height)
        self._last_geometry = geometry
        self._last_scale = scale

        for index, monitor in enumerate(self.monitors, start=1):
            name = monitor.get("name", f"Display {index}")
            x, y, w, h = geometry[name]
            preferred = name == self.preferred
            focused = bool(monitor.get("focused", False))

            cr.set_source_rgba(0.06, 0.07, 0.08, 1.0)
            cr.rectangle(x, y, w, h)
            cr.fill_preserve()

            if preferred:
                cr.set_source_rgb(0.92, 0.35, 0.42)
                line = 2.6
            elif focused:
                cr.set_source_rgb(0.68, 0.43, 0.48)
                line = 2.0
            else:
                cr.set_source_rgb(0.33, 0.30, 0.32)
                line = 1.2
            cr.set_line_width(line)
            cr.stroke()

            cr.set_source_rgb(0.88, 0.84, 0.81)
            cr.move_to(x + 10, y + 18)
            cr.show_text(name + ("  ★" if preferred else ""))

            cr.set_source_rgb(0.56, 0.52, 0.50)
            cr.move_to(x + 10, y + 34)
            cr.show_text(
                f'{monitor.get("width", 0)}x{monitor.get("height", 0)}  '
                f'@{float(monitor.get("refreshRate", 0)):.0f}Hz'
            )

            pos = self.pending.get(name, {"x": 0, "y": 0})
            cr.move_to(x + 10, y + 50)
            cr.show_text(
                f'Pos {pos["x"]}x{pos["y"]}  Scale {float(monitor.get("scale", 1)):.2f}'
            )

            if name == self.active_name:
                cr.set_source_rgba(0.92, 0.35, 0.42, 0.12)
                cr.rectangle(x, y, w, h)
                cr.fill()

    def _hit(self, x, y):
        for name, (rx, ry, rw, rh) in self._last_geometry.items():
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return name
        return None

    def _drag_begin(self, _gesture, x, y):
        self.active_name = self._hit(x, y)
        if not self.active_name:
            return
        pos = self.pending.get(self.active_name, {"x": 0, "y": 0})
        self.drag_origin = (pos["x"], pos["y"])
        self.queue_draw()

    def _drag_update(self, _gesture, offset_x, offset_y):
        if not self.active_name or self.drag_origin is None:
            return

        logical_x = self.drag_origin[0] + offset_x / max(self._last_scale, 0.02)
        logical_y = self.drag_origin[1] + offset_y / max(self._last_scale, 0.02)

        # 10-pixel snapping keeps Hyprland positions readable.
        self.pending[self.active_name] = {
            "x": int(round(logical_x / 10.0) * 10),
            "y": int(round(logical_y / 10.0) * 10),
        }
        self.queue_draw()
        if self.on_changed:
            self.on_changed(self.positions())

    def _drag_end(self, *_args):
        if self.active_name:
            self._resolve_overlap(self.active_name)
            if self.on_changed:
                self.on_changed(self.positions())
        self.active_name = None
        self.drag_origin = None
        self.queue_draw()

    def _logical_rect_for(self, name):
        monitor = next((m for m in self.monitors if m.get("name") == name), None)
        if monitor is None:
            return None
        pos = self.pending.get(name, {"x": 0, "y": 0})
        w, h = self._logical_size(monitor)
        return (pos["x"], pos["y"], pos["x"] + w, pos["y"] + h)

    @staticmethod
    def _rect_overlap(a, b):
        return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]

    def _resolve_overlap(self, name):
        current = self._logical_rect_for(name)
        if current is None:
            return

        for other in self.monitors:
            other_name = other.get("name")
            if other_name == name:
                continue
            other_rect = self._logical_rect_for(other_name)
            if other_rect is None or not self._rect_overlap(current, other_rect):
                continue

            monitor = next((m for m in self.monitors if m.get("name") == name), None)
            w, h = self._logical_size(monitor)
            old = self.pending[name]
            candidates = [
                {"x": int(round(other_rect[0] - w)), "y": old["y"]},
                {"x": int(round(other_rect[2])), "y": old["y"]},
                {"x": old["x"], "y": int(round(other_rect[1] - h))},
                {"x": old["x"], "y": int(round(other_rect[3]))},
            ]
            best = min(
                candidates,
                key=lambda p: (p["x"] - old["x"]) ** 2 + (p["y"] - old["y"]) ** 2,
            )
            self.pending[name] = {
                "x": int(round(best["x"] / 10.0) * 10),
                "y": int(round(best["y"] / 10.0) * 10),
            }
            current = self._logical_rect_for(name)


class WaybarMiniPreview(Gtk.Box):
    SAMPLE = {
        "custom/launcher": "薬",
        "hyprland/workspaces": "1  2  3",
        "hyprland/window": "Firefox",
        "mpris": "▶ chase — batta",
        "pulseaudio": " 35%",
        "memory": "MEM 7.2G",
        "cpu": "CPU 18%",
        "custom/cpu_temp": "CPU 41°C",
        "custom/gpu_temp": "GPU 44°C",
        "custom/governor": "󱐋",
        "tray": "TRAY",
        "clock": "MON 31 AUG",
        "clock#simpleclock": "06:39",
        "custom/power": "⏻",
    }

    def __init__(self, owner):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.owner = owner
        self.add_css_class("waybar-preview")

        self.left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.left.add_css_class("waybar-preview-lane")
        self.left.set_hexpand(True)

        self.center = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.center.add_css_class("waybar-preview-lane")
        self.center.set_halign(Gtk.Align.CENTER)
        self.center.set_hexpand(True)

        self.right = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.right.add_css_class("waybar-preview-lane")
        self.right.set_halign(Gtk.Align.END)
        self.right.set_hexpand(True)

        self.append(self.left)
        self.append(self.center)
        self.append(self.right)

    def _fill(self, box, items):
        child = box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt

        if not items:
            empty = Gtk.Label(label="—")
            empty.add_css_class("waybar-preview-empty")
            box.append(empty)
            return

        for module in items:
            chip = Gtk.Box()
            chip.add_css_class("waybar-preview-chip")
            label = Gtk.Label(label=self.SAMPLE.get(module, self.owner.short_label(module)))
            chip.append(label)
            box.append(chip)

    def rebuild(self):
        self._fill(self.left, self.owner.module_state["Left"])
        self._fill(self.center, self.owner.module_state["Center"])
        self._fill(self.right, self.owner.module_state["Right"])


class AppearancePage(Page):
    def __init__(self):
        super().__init__()

        self.append(page_header(
            "02",
            "Desktop",
            "Appearance",
            "Choose the overall feel first. Technical controls stay available underneath."
        ))

        values = state()["appearance"]

        presets = card(
            "// STYLE PRESETS",
            "One click changes blur, transparency, gaps, and rounding together."
        )
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_column_homogeneous(True)

        definitions = [
            (
                "LIQUID GLASS",
                "Transparent surfaces, strong blur, and soft spacing.",
                {
                    "gaps_in": 6,
                    "gaps_out": 12,
                    "border_size": 2,
                    "rounding": 20,
                    "blur_enabled": True,
                    "blur_size": 11,
                    "blur_passes": 4,
                    "active_opacity": 0.93,
                    "inactive_opacity": 0.86,
                },
            ),
            (
                "BALANCED",
                "Subtle depth with comfortable readability.",
                {
                    "gaps_in": 4,
                    "gaps_out": 8,
                    "border_size": 2,
                    "rounding": 14,
                    "blur_enabled": True,
                    "blur_size": 7,
                    "blur_passes": 3,
                    "active_opacity": 0.98,
                    "inactive_opacity": 0.94,
                },
            ),
            (
                "SOLID",
                "Opaque, compact, and distraction-free.",
                {
                    "gaps_in": 3,
                    "gaps_out": 6,
                    "border_size": 2,
                    "rounding": 9,
                    "blur_enabled": False,
                    "blur_size": 4,
                    "blur_passes": 1,
                    "active_opacity": 1.0,
                    "inactive_opacity": 1.0,
                },
            ),
        ]

        for index, (name, description, preset) in enumerate(definitions):
            button = Gtk.Button()
            button.add_css_class("preset-card")

            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)

            kicker = Gtk.Label(label=f"0{index + 1}  {name}", xalign=0)
            kicker.add_css_class("preset-title")
            content.append(kicker)

            text = Gtk.Label(label=description, xalign=0)
            text.set_wrap(True)
            text.add_css_class("muted")
            content.append(text)

            button.set_child(content)
            button.connect("clicked", self._apply_preset, preset)
            grid.attach(button, index, 0, 1, 1)

        presets.append(grid)
        self.append(presets)

        glass = card(
            "// GLASS ENGINE",
            "Application transparency reveals the desktop; Hyprland blur softens what sits behind it."
        )

        self.blur_enabled = Gtk.Switch(active=values["blur_enabled"])
        self.blur_size = spin(values["blur_size"], 1, 20)
        self.blur_passes = spin(values["blur_passes"], 1, 8)

        self.active_opacity = slider(values["active_opacity"], 0.45, 1.0, 0.01)
        self.inactive_opacity = slider(values["inactive_opacity"], 0.40, 1.0, 0.01)

        glass.append(setting_row("Blur", self.blur_enabled))
        glass.append(setting_row("Blur amount", self.blur_size))
        glass.append(setting_row("Blur quality", self.blur_passes))
        glass.append(setting_row(
            "Active window opacity",
            self.active_opacity,
            "Lower values increase transparency."
        ))
        glass.append(setting_row("Inactive window opacity", self.inactive_opacity))
        self.append(glass)

        geometry = card("// WINDOWS")
        self.gaps_in = spin(values["gaps_in"], 0, 30)
        self.gaps_out = spin(values["gaps_out"], 0, 50)
        self.border_size = spin(values["border_size"], 0, 8)
        self.rounding = spin(values["rounding"], 0, 40)

        geometry.append(setting_row("Window spacing", self.gaps_in))
        geometry.append(setting_row("Screen edge spacing", self.gaps_out))
        geometry.append(setting_row("Border thickness", self.border_size))
        geometry.append(setting_row("Corner roundness", self.rounding))
        self.append(geometry)

        frame_state = window_frame_status()
        frame_panel = card(
            "// WINDOW FRAME & SHADOW",
            "FOLLOW keeps active/inactive borders synchronized with Theme Studio and Auto Color. CUSTOM lets you pick your own frame colors. Shadow controls are independent in both modes."
        )
        self.frame_modes = ["FOLLOW YAKUSHI THEME", "CUSTOM"]
        self.frame_mode = Gtk.DropDown.new_from_strings(self.frame_modes)
        self.frame_mode.set_selected(0 if frame_state.mode == "follow" else 1)
        self.frame_mode.connect("notify::selected", self._frame_mode_changed)
        frame_panel.append(setting_row("Color source", self.frame_mode))

        self.frame_colors = {}
        color_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        color_grid.set_column_homogeneous(True)
        for index, (key, label, value) in enumerate((
            ("active", "Active border", frame_state.active_border),
            ("inactive", "Inactive border", frame_state.inactive_border),
            ("shadow", "Shadow color", frame_state.shadow_color),
        )):
            button = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())
            rgba = Gdk.RGBA()
            rgba.parse(value)
            button.set_rgba(rgba)
            self.frame_colors[key] = button
            chip = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            chip.add_css_class("color-chip")
            title = Gtk.Label(label=label, xalign=0)
            title.add_css_class("setting-name")
            chip.append(title)
            chip.append(button)
            color_grid.attach(chip, index, 0, 1, 1)
        frame_panel.append(color_grid)

        self.shadow_enabled = Gtk.Switch(active=frame_state.shadow_enabled)
        self.shadow_opacity = slider(frame_state.shadow_opacity, 0.0, 1.0, 0.01)
        self.shadow_range = spin(frame_state.shadow_range, 0, 100)
        self.shadow_power = spin(frame_state.shadow_render_power, 1, 4)
        self.shadow_offset_x = spin(frame_state.shadow_offset_x, -50, 50)
        self.shadow_offset_y = spin(frame_state.shadow_offset_y, -50, 50)
        self.shadow_scale = slider(frame_state.shadow_scale, 0.0, 1.0, 0.01)
        frame_panel.append(setting_row("Drop shadow", self.shadow_enabled))
        frame_panel.append(setting_row("Shadow opacity", self.shadow_opacity, "Alpha is encoded into Hyprland's shadow color."))
        frame_panel.append(setting_row("Shadow size", self.shadow_range))
        frame_panel.append(setting_row("Shadow falloff", self.shadow_power, "1 is softest; 4 falls off fastest."))
        offsets = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        offsets.append(Gtk.Label(label="X", xalign=0))
        offsets.append(self.shadow_offset_x)
        offsets.append(Gtk.Label(label="Y", xalign=0))
        offsets.append(self.shadow_offset_y)
        frame_panel.append(setting_row("Shadow offset", offsets, "Positive Y moves the shadow downward."))
        frame_panel.append(setting_row("Shadow scale", self.shadow_scale))
        self.append(frame_panel)

        frame_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        frame_actions.append(action_button("APPLY WINDOW FRAME", self.apply_frame, primary=True))
        frame_actions.append(action_button("LOAD CURRENT THEME COLORS", self.load_frame_theme))
        self.append(frame_actions)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")

        self.append(action_button("APPLY APPEARANCE", self.apply, primary=True))
        self.append(self.status)
        self._frame_mode_changed()

    def _read_values(self):
        return {
            "gaps_in": int(self.gaps_in.get_value()),
            "gaps_out": int(self.gaps_out.get_value()),
            "border_size": int(self.border_size.get_value()),
            "rounding": int(self.rounding.get_value()),
            "blur_enabled": self.blur_enabled.get_active(),
            "blur_size": int(self.blur_size.get_value()),
            "blur_passes": int(self.blur_passes.get_value()),
            "active_opacity": round(self.active_opacity.scale.get_value(), 2),
            "inactive_opacity": round(self.inactive_opacity.scale.get_value(), 2),
        }

    def _set_values(self, values):
        self.gaps_in.set_value(values["gaps_in"])
        self.gaps_out.set_value(values["gaps_out"])
        self.border_size.set_value(values["border_size"])
        self.rounding.set_value(values["rounding"])
        self.blur_enabled.set_active(values["blur_enabled"])
        self.blur_size.set_value(values["blur_size"])
        self.blur_passes.set_value(values["blur_passes"])
        self.active_opacity.scale.set_value(values["active_opacity"])
        self.inactive_opacity.scale.set_value(values["inactive_opacity"])

    def _apply_preset(self, _button, values):
        self._set_values(values)
        _, message = apply_appearance(values)
        self.status.set_text(message)

    def apply(self, *_):
        _, message = apply_appearance(self._read_values())
        self.status.set_text(message)

    @staticmethod
    def _frame_button_hex(button) -> str:
        rgba = button.get_rgba()
        return "#{:02x}{:02x}{:02x}".format(
            round(rgba.red * 255), round(rgba.green * 255), round(rgba.blue * 255)
        )

    def _set_frame_colors(self, active: str, inactive: str, shadow: str):
        for key, value in (("active", active), ("inactive", inactive), ("shadow", shadow)):
            rgba = Gdk.RGBA()
            rgba.parse(value)
            self.frame_colors[key].set_rgba(rgba)

    def _frame_mode_changed(self, *_):
        follow = self.frame_mode.get_selected() == 0
        if follow:
            palette = load_palette()
            self._set_frame_colors(palette.accent, palette.border, palette.bg)
        for button in self.frame_colors.values():
            button.set_sensitive(not follow)

    def load_frame_theme(self, *_):
        palette = load_palette()
        self.frame_mode.set_selected(0)
        self._set_frame_colors(palette.accent, palette.border, palette.bg)
        self._frame_mode_changed()
        self.status.set_text("Current Yakushi palette loaded for borders and shadow. Apply Window Frame to persist it.")

    def apply_frame(self, *_):
        follow = self.frame_mode.get_selected() == 0
        if follow:
            palette = load_palette()
            active, inactive, shadow = palette.accent, palette.border, palette.bg
            self._set_frame_colors(active, inactive, shadow)
        else:
            active = self._frame_button_hex(self.frame_colors["active"])
            inactive = self._frame_button_hex(self.frame_colors["inactive"])
            shadow = self._frame_button_hex(self.frame_colors["shadow"])
        value = FrameSettings(
            mode="follow" if follow else "custom",
            active_border=active,
            inactive_border=inactive,
            shadow_enabled=self.shadow_enabled.get_active(),
            shadow_color=shadow,
            shadow_opacity=round(self.shadow_opacity.scale.get_value(), 2),
            shadow_range=int(self.shadow_range.get_value()),
            shadow_render_power=int(self.shadow_power.get_value()),
            shadow_offset_x=int(self.shadow_offset_x.get_value()),
            shadow_offset_y=int(self.shadow_offset_y.get_value()),
            shadow_scale=round(self.shadow_scale.scale.get_value(), 2),
        )
        ok, message = apply_window_frame(value)
        self.status.set_text(message if ok else "ERROR: " + message)


class WallpaperPage(Page):
    FEATURED_WIDTH = 800
    FEATURED_HEIGHT = 450
    TILE_WIDTH = 210
    TILE_HEIGHT = 145

    def __init__(self):
        super().__init__()

        self.append(page_header(
            "02",
            "Desktop",
            "Wallpapers",
            "Images under ~/Documents and ~/Pictures are indexed automatically. Documents opens by default; use the folder filter to switch libraries."
        ))

        # Keep the wallpaper toolbar geometrically stable.  The image counter
        # used to expand with its text and push Search / folder / RESCAN farther
        # right as the indexed count gained digits.  Give the counter a bounded
        # lane and keep all actions in one fixed right-side group instead.
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        toolbar.set_hexpand(True)

        self.count = Gtk.Label(xalign=0)
        self.count.add_css_class("meta")
        self.count.set_size_request(210, -1)
        self.count.set_hexpand(False)
        self.count.set_halign(Gtk.Align.START)
        self.count.set_max_width_chars(26)
        self.count.set_ellipsize(Pango.EllipsizeMode.END)
        toolbar.append(self.count)

        toolbar_spacer = Gtk.Box()
        toolbar_spacer.set_hexpand(True)
        toolbar.append(toolbar_spacer)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.set_hexpand(False)
        controls.set_halign(Gtk.Align.END)

        self.search = Gtk.SearchEntry(placeholder_text="Filter images...")
        self.search.set_size_request(210, -1)
        self.search.set_hexpand(False)
        self.search.connect("search-changed", lambda *_: self.render())
        controls.append(self.search)

        self.filter_options = ["All folders", "Recent"]
        self.folder_filter = Gtk.DropDown.new_from_strings(self.filter_options)
        self.folder_filter.set_size_request(150, -1)
        self.folder_filter.set_hexpand(False)
        self.folder_filter.connect("notify::selected", lambda *_: self.render())
        controls.append(self.folder_filter)

        refresh = action_button("RESCAN", lambda *_: self.refresh())
        refresh.set_size_request(88, -1)
        refresh.set_hexpand(False)
        controls.append(refresh)

        toolbar.append(controls)
        self.append(toolbar)

        self.recent_card = card(
            "// RECENT",
            "The latest applied wallpaper stays at one fixed preview size, so changing wallpapers never resizes the page."
        )
        self.recent_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.recent_box.set_halign(Gtk.Align.START)
        self.recent_box.set_valign(Gtk.Align.START)
        self.recent_box.set_hexpand(False)
        self.recent_box.set_vexpand(False)
        self.recent_card.append(self.recent_box)
        self.append(self.recent_card)

        library = card(
            "// WALLPAPER LIBRARY",
            "Folder filtering never moves or copies your files; it only changes what is shown here."
        )
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_min_children_per_line(1)
        # Three 210px cards stay comfortably inside the fixed 1190px deck
        # after sidebar, page margins and card padding are accounted for.
        self.flow.set_max_children_per_line(3)
        self.flow.set_column_spacing(10)
        self.flow.set_row_spacing(10)
        self.flow.set_homogeneous(False)
        self.flow.set_halign(Gtk.Align.START)
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_vexpand(False)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(390)
        if hasattr(scroll, "set_max_content_height"):
            scroll.set_max_content_height(470)
        if hasattr(scroll, "set_propagate_natural_height"):
            scroll.set_propagate_natural_height(False)
        scroll.set_vexpand(False)
        scroll.set_child(self.flow)
        library.append(scroll)
        self.append(library)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")
        self.append(self.status)

        self.all_images = []
        self.recent_images = []
        self.current_path = None
        self.refresh()

    @staticmethod
    def _clear_box(box):
        child = box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt

    @staticmethod
    def _clear_flow(flow):
        child = flow.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            flow.remove(child)
            child = nxt

    @staticmethod
    def _scaled_picture(path: Path, width: int, height: int):
        """Return a bounded wallpaper preview that can never negotiate source size.

        The source image is decoded into a pixbuf no larger than the requested
        preview box.  If decoding fails, use a fixed-size placeholder instead of
        falling back to Gtk.Picture.new_for_filename(), because that fallback can
        re-introduce the original image dimensions into GTK layout negotiation.
        """
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(path), max(1, int(width)), max(1, int(height)), True
            )
            picture = Gtk.Picture.new_for_pixbuf(pixbuf)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_can_shrink(True)
        except Exception:
            picture = Gtk.Box()
            picture.add_css_class("wallpaper-preview-missing")
        picture.set_hexpand(False)
        picture.set_vexpand(False)
        picture.set_halign(Gtk.Align.START)
        picture.set_valign(Gtk.Align.START)
        picture.set_size_request(width, height)
        if hasattr(picture, "set_overflow"):
            picture.set_overflow(Gtk.Overflow.HIDDEN)
        return picture

    @staticmethod
    def _folder_caption(path: Path) -> str:
        """Short, stable folder text for preview overlays.

        Long backup/project paths were another hidden source of natural-width
        growth: an ellipsized Gtk.Label can still request the full unbounded text
        width. Keep the visible caption intentionally short and put the full path
        in the tooltip instead.
        """
        home = Path.home()
        for root_name in ("Documents", "Pictures"):
            root = home / root_name
            try:
                relative = path.parent.relative_to(root)
            except ValueError:
                continue
            if str(relative) == ".":
                return root_name
            leaf = relative.name or root_name
            return f"{root_name} / {leaf}"
        return path.parent.name or str(path.parent)

    @staticmethod
    def _reclamp_window():
        # GTK may update natural-size requests after a new thumbnail is inserted.
        # Re-apply the deck's known floating geometry once layout has settled so a
        # pathological image/path can never leave the window permanently enlarged.
        ensure_control_deck_floating(center=False)
        return False

    def refresh(self):
        self.all_images = scan_wallpapers()
        self.recent_images = recent_wallpapers()
        self.current_path = current_wallpaper()

        # Keep the folder selector deliberately bounded.  Earlier builds added
        # every nested directory below Documents/Pictures to Gtk.DropDown.  GTK
        # measures the widest model item even when that item is not selected, so
        # a long backup/project path could silently increase the window's natural
        # width each time the library was rescanned.  Root filters still include
        # every nested image; search handles finer-grained discovery.
        self.filter_options = []
        if Path.home().joinpath("Documents").exists():
            self.filter_options.append("Documents")
        if Path.home().joinpath("Pictures").exists():
            self.filter_options.append("Pictures")
        self.filter_options.extend(["All folders", "Recent"])
        model = Gtk.StringList.new(self.filter_options)
        self.folder_filter.set_model(model)
        default_filter = "Documents" if "Documents" in self.filter_options else "All folders"
        self.folder_filter.set_selected(self.filter_options.index(default_filter))

        self._render_recent()
        self.render()

    def _render_recent(self):
        self._clear_box(self.recent_box)
        path = None
        if self.current_path and self.current_path.exists():
            path = self.current_path
        elif self.recent_images:
            path = self.recent_images[0]
        if path:
            self.recent_box.append(self._tile(path, featured=True))
            self.recent_card.set_visible(True)
        else:
            self.recent_card.set_visible(False)

    def render(self):
        self._clear_flow(self.flow)

        selected_index = self.folder_filter.get_selected()
        selected = (
            self.filter_options[selected_index]
            if 0 <= selected_index < len(self.filter_options)
            else "All folders"
        )

        if selected == "Recent":
            images = list(self.recent_images)
        elif selected == "All folders":
            images = list(self.all_images)
        else:
            images = scan_wallpapers(folder=selected)

        query = self.search.get_text().strip().lower()
        if query:
            images = [
                path for path in images
                if query in path.name.lower() or query in str(path.parent).lower()
            ]

        self.count.set_text(f"{len(images)} SHOWN // {len(self.all_images)} INDEXED")

        for path in images:
            self.flow.insert(self._tile(path), -1)

        if not images:
            self.status.set_text("No wallpapers match the current filter.")
        else:
            self.status.set_text("")

    def _tile(self, path: Path, featured=False):
        button = Gtk.Button()
        button.add_css_class("wallpaper-tile")
        if featured:
            button.add_css_class("wallpaper-featured")
        if self.current_path and path == self.current_path:
            button.add_css_class("wallpaper-current")

        tile_width = self.FEATURED_WIDTH if featured else self.TILE_WIDTH
        tile_height = self.FEATURED_HEIGHT if featured else self.TILE_HEIGHT
        button.set_size_request(tile_width, tile_height)
        button.set_hexpand(False)
        button.set_vexpand(False)
        button.set_halign(Gtk.Align.START)
        button.set_valign(Gtk.Align.START)
        if hasattr(button, "set_overflow"):
            button.set_overflow(Gtk.Overflow.HIDDEN)

        overlay = Gtk.Overlay()
        overlay.set_size_request(tile_width, tile_height)
        overlay.set_hexpand(False)
        overlay.set_vexpand(False)
        overlay.set_halign(Gtk.Align.START)
        overlay.set_valign(Gtk.Align.START)
        if hasattr(overlay, "set_overflow"):
            overlay.set_overflow(Gtk.Overflow.HIDDEN)

        picture = self._scaled_picture(path, tile_width, tile_height)
        overlay.set_child(picture)

        label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        label_box.add_css_class("wallpaper-label")
        label_box.set_halign(Gtk.Align.START)
        label_box.set_valign(Gtk.Align.END)
        label_box.set_hexpand(False)
        label_box.set_vexpand(False)
        label_box.set_margin_start(7)
        label_box.set_margin_end(7)
        label_box.set_margin_bottom(7)
        label_width = max(96, tile_width - 28)
        label_box.set_size_request(label_width, -1)

        name = Gtk.Label(label=path.stem, xalign=0)
        name.set_ellipsize(Pango.EllipsizeMode.END)
        name.set_single_line_mode(True)
        name.set_max_width_chars(48 if featured else 24)
        name.set_size_request(label_width, -1)
        name.set_tooltip_text(path.name)
        name.add_css_class("wallpaper-name")
        label_box.append(name)

        folder_text = self._folder_caption(path)
        folder = Gtk.Label(label=folder_text, xalign=0)
        folder.set_ellipsize(Pango.EllipsizeMode.END)
        folder.set_single_line_mode(True)
        folder.set_max_width_chars(48 if featured else 24)
        folder.set_size_request(label_width, -1)
        folder.set_tooltip_text(str(path.parent))
        folder.add_css_class("wallpaper-folder")
        label_box.append(folder)

        overlay.add_overlay(label_box)
        button.set_child(overlay)
        button.connect("clicked", self._apply, path)
        return button

    def _apply(self, _button, path):
        ok, message = apply_wallpaper(path)
        self.status.set_text(f"{path.name} — {message}")
        if ok:
            self.current_path = path
            self.recent_images = recent_wallpapers()
            self.render()
            self._render_recent()

            auto_ok, auto_message = apply_follow_if_enabled(path)
            if auto_message:
                self.status.set_text(
                    f"{path.name} — {message}  //  {auto_message}"
                    if auto_ok else
                    f"{path.name} — {message}  //  Auto Color error: {auto_message}"
                )

            # Two idle passes cover both thumbnail replacement and optional
            # Follow Wallpaper palette/CSS updates before forcing final geometry.
            GLib.timeout_add(90, self._reclamp_window)
            GLib.timeout_add(260, self._reclamp_window)


class ThemePage(Page):
    # Each preset has nine roles.  The point is not "same black theme, new
    # accent"; the background, raised surfaces, borders, muted text and hover
    # depth all move together inside one color family.
    PRESET_GROUPS = [
        (
            "DUSTED / MUTED",
            "Low-strain tonal palettes inspired by the dusty salmon reference you sent.",
            [
                (
                    "SALMON DUST",
                    "The reference family: charcoal-brown surfaces with dusty salmon highlights.",
                    Palette("#e8a29a", "#0e0c0d", "#1a1414", "#231919", "#e8a29a", "#a77772", "#3f292a", "#362324", "#1a1414"),
                ),
                (
                    "ROSEWOOD",
                    "Muted rose, walnut-black surfaces and warmer cream text.",
                    Palette("#cf8d91", "#100d0e", "#1e1718", "#2a1d1f", "#d7a1a4", "#986f73", "#4b3034", "#3a2529", "#1a1214"),
                ),
                (
                    "BLUSH CHARCOAL",
                    "Cool charcoal with a powder-blush accent and grey-rose secondary text.",
                    Palette("#d9a4ab", "#0d0d0f", "#18171a", "#222025", "#dcb7bd", "#907d82", "#3b3439", "#302a30", "#171417"),
                ),
                (
                    "PEACH SMOKE",
                    "Smoked brown-black with quiet peach and warm parchment foregrounds.",
                    Palette("#dca58c", "#100e0d", "#1d1815", "#29201b", "#e0ad96", "#9b7a6b", "#49372e", "#382b25", "#191411"),
                ),
            ],
        ),
        (
            "RED / BLACK",
            "For when red should dominate the desktop without turning into a generic neon preset.",
            [
                (
                    "VERMILION INK",
                    "Ink-black layers with hot vermilion and warm off-white text.",
                    Palette("#f04b45", "#070607", "#120d0e", "#1d1113", "#f06b64", "#a65e5b", "#502127", "#34151a", "#120a0b"),
                ),
                (
                    "CRIMSON VELVET",
                    "Deep velvet red surfaces; less neon, more saturated fabric-like crimson.",
                    Palette("#d93a4a", "#090607", "#170b0e", "#241014", "#e36775", "#9d626c", "#5c222e", "#39151c", "#16090c"),
                ),
                (
                    "OXBLOOD",
                    "Near-black burgundy with dense oxblood borders and a muted red signal.",
                    Palette("#b84a55", "#090708", "#150d0f", "#201215", "#c8767e", "#8e656b", "#4b252c", "#321a1f", "#140b0d"),
                ),
                (
                    "CHERRY BLACK",
                    "Black cherry layers with brighter selected workspaces but restrained body text.",
                    Palette("#e05268", "#080607", "#150a0e", "#231019", "#e77a8b", "#9d6571", "#572334", "#371522", "#14090c"),
                ),
            ],
        ),
        (
            "SOFT / MILK",
            "Pastel families with genuinely light surfaces, not dark themes wearing pastel accents.",
            [
                (
                    "SAKURA MILK",
                    "Milky pink background, rose surfaces, muted berry text and soft cherry selection.",
                    Palette("#cb7f91", "#f2e7e9", "#ead8dc", "#dfc8ce", "#34262a", "#80686e", "#c8aeb5", "#e2cbd1", "#2b2023"),
                ),
                (
                    "LILAC MILK",
                    "Pale lavender, dusty violet panels and plum-grey typography.",
                    Palette("#9985c7", "#eeeaf5", "#e3dced", "#d7cee4", "#312b38", "#766d80", "#beb3cf", "#dbd2e8", "#28232e"),
                ),
                (
                    "MINT MILK",
                    "Sage-mint paper surfaces with botanical green accent and charcoal text.",
                    Palette("#6f9d82", "#e9f0ea", "#dce8df", "#cfddd3", "#263129", "#68786d", "#b4c6b9", "#d3e1d6", "#202922"),
                ),
                (
                    "POWDER BLUE",
                    "Powder-blue paper, misty raised layers and calm slate-blue text.",
                    Palette("#7798bd", "#e9eef3", "#dce5ed", "#cfdae5", "#25313d", "#657486", "#b2c1d0", "#d1dce7", "#202a34"),
                ),
                (
                    "BUTTER CREAM",
                    "Warm ivory and butter surfaces with a muted honey accent.",
                    Palette("#b78c50", "#f3eee2", "#e9dfcd", "#ddd0b9", "#352e23", "#7f7463", "#c8b99f", "#e4d8c2", "#2b251d"),
                ),
            ],
        ),
        (
            "DEEP COLOR",
            "The same tonal philosophy in purple, green, teal, blue and amber families.",
            [
                (
                    "PLUM VELVET",
                    "Black-plum surfaces with dusty orchid accents and pale mauve text.",
                    Palette("#b483a9", "#0b090d", "#17121a", "#211826", "#c69abb", "#8e748c", "#433047", "#312337", "#160f18"),
                ),
                (
                    "SAGE NOIR",
                    "Charcoal-green surfaces, dry sage accent and warm botanical foreground.",
                    Palette("#8da58d", "#090b09", "#131814", "#1b221d", "#a8bba8", "#748176", "#344139", "#27302a", "#111612"),
                ),
                (
                    "PETROL SMOKE",
                    "Smoky petrol blue/green with desaturated cyan and stone-grey text.",
                    Palette("#77a9ad", "#080b0c", "#10181a", "#172326", "#8fc0c3", "#6d8588", "#304449", "#233438", "#101719"),
                ),
                (
                    "INDIGO INK",
                    "Ink-blue layers with dusty periwinkle and cool silver foregrounds.",
                    Palette("#8595c9", "#08090d", "#11141d", "#191e2b", "#9cabe0", "#747d9a", "#31394f", "#242a3d", "#10131b"),
                ),
                (
                    "AMBER TOBACCO",
                    "Dark tobacco brown, restrained amber and parchment-like foregrounds.",
                    Palette("#c49355", "#0c0a07", "#18130d", "#241b11", "#d2a66d", "#90785b", "#493822", "#362818", "#171109"),
                ),
            ],
        ),
    ]

    def __init__(self):
        super().__init__()

        self.append(page_header(
            "02",
            "Desktop",
            "Theme Studio",
            "What you see in each preset is what gets written: background, surfaces, borders, hover depth and text all move together."
        ))

        self.palette = load_palette()
        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")

        self._build_auto_color()

        reference = card(
            "// YOUR REFERENCE",
            "SALMON DUST now uses the dusty salmon itself as normal foreground text — no near-white fallback. The preview and applied foreground share the same role."
        )
        ref_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        for label, color in (("ACCENT", "#e8a29a"), ("SURFACE", "#1a1414"), ("DEPTH", "#231919"), ("BORDER", "#3f292a")):
            item = Gtk.Label(label=label)
            name = f"reference-{id(item)}"
            item.set_name(name)
            provider = Gtk.CssProvider()
            provider.load_from_data(
                f"#{name} {{ background: {color}; color: {'#171313' if color == '#e8a29a' else '#e8d9d5'}; border: 1px solid #4b3030; border-radius: 999px; padding: 5px 10px; font-size: 9px; font-weight: 800; }}".encode()
            )
            item.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            ref_line.append(item)
        reference.append(ref_line)
        self.append(reference)

        for group_name, group_description, presets in self.PRESET_GROUPS:
            group = card(f"// {group_name}", group_description)
            grid = Gtk.Grid(column_spacing=10, row_spacing=10)
            grid.set_column_homogeneous(True)
            for index, (title, description, palette) in enumerate(presets):
                grid.attach(PalettePresetCard(self, title, description, palette), index % 2, index // 2, 1, 1)
            group.append(grid)
            self.append(group)

        palette_card = card(
            "// CUSTOM TONAL PALETTE",
            "Fine tune the roles yourself. Surface is the main module/input panel; Depth is the raised secondary layer."
        )

        self.buttons = {}
        values = [
            ("accent", "Accent"),
            ("bg", "Background"),
            ("surface", "Surface"),
            ("surface_alt", "Depth"),
            ("fg", "Foreground"),
            ("muted", "Muted text"),
            ("border", "Border"),
            ("hover_bg", "Hover"),
            ("selected_fg", "Selected text"),
        ]

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_column_homogeneous(True)
        for index, (key, label) in enumerate(values):
            button = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())
            self.buttons[key] = button
            chip = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            chip.add_css_class("color-chip")
            title = Gtk.Label(label=label, xalign=0)
            title.add_css_class("setting-name")
            chip.append(title)
            chip.append(button)
            grid.attach(chip, index % 3, index // 3, 1, 1)

        palette_card.append(grid)
        self.append(palette_card)
        self.append(action_button("APPLY CUSTOM TONAL PALETTE", self.apply, primary=True))

        self._build_typography()
        self.append(self.status)
        self.load_palette_into_controls(self.palette)

    def _build_auto_color(self):
        auto = auto_color_status()
        self.auto_enabled = bool(auto.get("enabled", False))
        self.auto_modes = ["DARK", "LIGHT"]

        panel = card(
            "// AUTO COLOR THEME",
            "Build a complete tonal palette from the current wallpaper. DARK keeps deep surfaces; LIGHT creates a paper-like palette. Follow mode recolors automatically whenever you change wallpaper inside Yakushi."
        )

        self.auto_mode = Gtk.DropDown.new_from_strings(self.auto_modes)
        self.auto_mode.set_selected(1 if auto.get("mode") == "light" else 0)
        self.auto_mode.connect("notify::selected", self._auto_mode_changed)
        panel.append(setting_row(
            "Palette mode",
            self.auto_mode,
            "The same wallpaper can produce a dark or light desktop without changing the source image."
        ))

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.auto_follow_button = Gtk.Button()
        self.auto_follow_button.connect("clicked", self._toggle_auto_follow)
        actions.append(self.auto_follow_button)

        apply_now = Gtk.Button(label="GENERATE + APPLY NOW")
        apply_now.add_css_class("primary")
        apply_now.connect("clicked", self._apply_auto_now)
        actions.append(apply_now)
        panel.append(actions)

        self.auto_source = Gtk.Label(xalign=0)
        self.auto_source.add_css_class("muted")
        self.auto_source.set_wrap(True)
        panel.append(self.auto_source)

        self.append(panel)
        self._refresh_auto_controls()

    def _selected_auto_mode(self):
        return "light" if self.auto_mode.get_selected() == 1 else "dark"

    def _refresh_auto_controls(self):
        self.auto_follow_button.set_label(
            "FOLLOW WALLPAPER: ON" if self.auto_enabled else "FOLLOW WALLPAPER: OFF"
        )
        if self.auto_enabled:
            self.auto_follow_button.add_css_class("active")
        else:
            self.auto_follow_button.remove_css_class("active")

        wallpaper = current_wallpaper()
        if wallpaper:
            self.auto_source.set_text(f"SOURCE // {wallpaper}")
        else:
            self.auto_source.set_text("SOURCE // No wallpaper has been applied through Yakushi yet.")

    def _auto_mode_changed(self, *_):
        mode = self._selected_auto_mode()
        configure_auto_color(mode=mode)
        if self.auto_enabled:
            ok, message, palette = apply_auto_color(mode=mode)
            if ok and palette is not None:
                self.load_palette_into_controls(palette)
            self.status.set_text(message)
        self._refresh_auto_controls()

    def _toggle_auto_follow(self, *_):
        new_value = not self.auto_enabled
        mode = self._selected_auto_mode()
        if new_value:
            ok, message, palette = apply_auto_color(mode=mode, enable_follow=True)
            if ok:
                self.auto_enabled = True
                if palette is not None:
                    self.load_palette_into_controls(palette)
            self.status.set_text(message)
        else:
            configure_auto_color(enabled=False, mode=mode)
            self.auto_enabled = False
            self.status.set_text("Auto Color follow mode disabled. Your current palette stays unchanged.")
        self._refresh_auto_controls()

    def _apply_auto_now(self, *_):
        mode = self._selected_auto_mode()
        ok, message, palette = apply_auto_color(mode=mode)
        if ok and palette is not None:
            self.load_palette_into_controls(palette)
        self.status.set_text(message)
        self._refresh_auto_controls()

    def _build_typography(self):
        typography = typography_status()
        self.typography_enabled = bool(typography.get("enabled"))
        self.typography_terminal = bool(typography.get("terminal_too"))
        self.fonts = typography.get("available_fonts") or ["serif"]

        panel = card(
            "// DESKTOP TYPOGRAPHY",
            "A bold editorial serif like the Terminal heading in your reference. It can be enabled desktop-wide and restored with one click."
        )

        preview = Gtk.Label(xalign=0)
        preview.add_css_class("typography-preview")
        panel.append(preview)
        self.font_preview = preview

        self.font_dropdown = Gtk.DropDown.new_from_strings(self.fonts)
        current_family = typography.get("family") or self.fonts[0]
        try:
            self.font_dropdown.set_selected(self.fonts.index(current_family))
        except ValueError:
            self.font_dropdown.set_selected(0)
        self.font_dropdown.connect("notify::selected", self._font_preview_changed)
        panel.append(setting_row(
            "Editorial serif",
            self.font_dropdown,
            "Uses an already installed serif font discovered through fontconfig; Yakushi installs no extra font package."
        ))

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.typography_button = Gtk.Button()
        self.typography_button.add_css_class("typography-toggle")
        self.typography_button.connect("clicked", self._toggle_typography)
        actions.append(self.typography_button)

        self.terminal_font_button = Gtk.Button()
        self.terminal_font_button.add_css_class("typography-option")
        self.terminal_font_button.connect("clicked", self._toggle_terminal_font)
        actions.append(self.terminal_font_button)

        apply_font = Gtk.Button(label="APPLY SELECTED FONT")
        apply_font.add_css_class("typography-option")
        apply_font.connect("clicked", self._reapply_typography)
        actions.append(apply_font)

        panel.append(actions)

        note = Gtk.Label(
            label="Desktop mode targets GTK 3/4 apps, Waybar and Rofi. Terminal text stays monospace by default so Nerd Font icons, prompts and columns remain safe.",
            xalign=0,
        )
        note.set_wrap(True)
        note.add_css_class("muted")
        panel.append(note)

        self.append(panel)
        self._refresh_typography_controls()
        self._font_preview_changed()

    def _selected_font(self):
        if not self.fonts:
            return "serif"
        index = min(self.font_dropdown.get_selected(), len(self.fonts) - 1)
        return self.fonts[index]

    def _font_preview_changed(self, *_):
        family = self._selected_font()
        self.font_preview.set_markup(
            f'<span font_family="{escape(family)}" size="30000" weight="bold">Terminal</span>'
        )

    def _refresh_typography_controls(self):
        self.typography_button.set_label(
            "DESKTOP SERIF: ON" if self.typography_enabled else "DESKTOP SERIF: OFF"
        )
        if self.typography_enabled:
            self.typography_button.add_css_class("active")
        else:
            self.typography_button.remove_css_class("active")

        self.terminal_font_button.set_label(
            "TERMINAL TEXT: SERIF" if self.typography_terminal else "TERMINAL TEXT: KEEP MONOSPACE"
        )
        if self.typography_terminal:
            self.terminal_font_button.add_css_class("active")
        else:
            self.terminal_font_button.remove_css_class("active")

    def _set_live_gtk_font(self, family: str | None):
        try:
            settings = Gtk.Settings.get_default()
            if settings and family:
                settings.set_property("gtk-font-name", f"{family} 11")
        except Exception:
            pass

    def _toggle_typography(self, *_):
        new_value = not self.typography_enabled
        family = self._selected_font()
        ok, message = apply_typography(new_value, family, self.typography_terminal)
        if ok:
            self.typography_enabled = new_value
            if new_value:
                self._set_live_gtk_font(family)
            else:
                refreshed = typography_status()
                # GTK settings.ini will be authoritative on next app launch;
                # live restoration is best effort and avoids inventing a font.
                self.typography_terminal = False
        self._refresh_typography_controls()
        self.status.set_text(message)

    def _toggle_terminal_font(self, *_):
        self.typography_terminal = not self.typography_terminal
        self._refresh_typography_controls()
        if self.typography_enabled:
            ok, message = apply_typography(True, self._selected_font(), self.typography_terminal)
            self.status.set_text(message)

    def _reapply_typography(self, *_):
        if not self.typography_enabled:
            self.status.set_text("Enable DESKTOP SERIF first, then this button updates the selected family.")
            return
        family = self._selected_font()
        ok, message = apply_typography(True, family, self.typography_terminal)
        if ok:
            self._set_live_gtk_font(family)
        self.status.set_text(message)

    @staticmethod
    def _hex(button):
        rgba = button.get_rgba()
        return "#{:02x}{:02x}{:02x}".format(
            round(rgba.red * 255),
            round(rgba.green * 255),
            round(rgba.blue * 255),
        )

    def load_palette_into_controls(self, palette: Palette):
        self.palette = palette
        for key in self.buttons:
            rgba = Gdk.RGBA()
            rgba.parse(getattr(palette, key))
            self.buttons[key].set_rgba(rgba)

    def apply(self, *_):
        value = Palette(**{key: self._hex(button) for key, button in self.buttons.items()})
        self.palette = value
        _, message = save_palette(value)
        self.status.set_text(message)


class DisplaysPage(Page):
    def __init__(self):
        super().__init__()

        self.append(page_header(
            "01",
            "Devices",
            "Displays",
            "Drag monitor blocks to arrange them, then apply the layout. Resolution and DPI stay available below."
        ))

        preview_card = card(
            "// LAYOUT EDITOR",
            "Drag a monitor block. Positions snap to 10 logical pixels. ★ marks Yakushi's preferred/focused display."
        )
        preview_card.add_css_class("monitor-map-card")

        self.map = MonitorLayoutPreview(on_changed=self._layout_changed)
        preview_card.append(self.map)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.layout_status = Gtk.Label(xalign=0)
        self.layout_status.add_css_class("monitor-map-summary")
        self.layout_status.set_hexpand(True)
        controls.append(self.layout_status)

        self.preferred_names = []
        self.preferred_box = Gtk.DropDown.new_from_strings(["No displays"])
        controls.append(self.preferred_box)

        preferred_button = action_button("SET PREFERRED", self.set_preferred)
        controls.append(preferred_button)

        apply_layout = action_button("APPLY LAYOUT", self.apply_layout, primary=True)
        controls.append(apply_layout)

        preview_card.append(controls)
        self.append(preview_card)

        note = card(
            "// PRIMARY DISPLAY NOTE",
            "Hyprland has no Windows-style global primary-monitor flag. Yakushi's Preferred display is focused immediately and remembered as the deck's default target."
        )
        self.append(note)

        self.container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.append(self.container)

        self.refresh_button = action_button("RESCAN DISPLAYS", lambda *_: self.refresh())
        self.append(self.refresh_button)

        self.monitor_list = []
        self.refresh()

    def _layout_changed(self, _positions):
        self.layout_status.set_text("Layout changed — press APPLY LAYOUT to send positions to Hyprland.")

    def refresh(self):
        child = self.container.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.container.remove(child)
            child = nxt

        self.monitor_list = monitors()
        preferred = preferred_monitor()
        if not preferred and self.monitor_list:
            focused = next((m for m in self.monitor_list if m.get("focused")), None)
            preferred = focused.get("name", "") if focused else self.monitor_list[0].get("name", "")

        self.map.set_monitors(self.monitor_list, preferred=preferred)

        self.preferred_names = [m.get("name", "") for m in self.monitor_list]
        if self.preferred_names:
            self.preferred_box.set_model(Gtk.StringList.new(self.preferred_names))
            try:
                self.preferred_box.set_selected(self.preferred_names.index(preferred))
            except ValueError:
                self.preferred_box.set_selected(0)
        else:
            self.preferred_box.set_model(Gtk.StringList.new(["No displays"]))
            self.preferred_box.set_selected(0)

        self.layout_status.set_text(f"{len(self.monitor_list)} display(s) detected.")

        for monitor in self.monitor_list:
            self.container.append(self._monitor_card(monitor))

    def set_preferred(self, *_):
        if not self.preferred_names:
            self.layout_status.set_text("No display is available.")
            return
        name = self.preferred_names[self.preferred_box.get_selected()]
        ok, message = set_preferred_monitor(name)
        self.layout_status.set_text(message)
        if ok:
            self.map.preferred = name
            self.map.queue_draw()

    def apply_layout(self, *_):
        if not self.monitor_list:
            self.layout_status.set_text("No displays are available.")
            return

        positions = self.map.positions()
        layout = []
        for monitor in self.monitor_list:
            name = monitor.get("name")
            pos = positions.get(name, {"x": monitor.get("x", 0), "y": monitor.get("y", 0)})
            mode = (
                f'{monitor.get("width")}x{monitor.get("height")}@'
                f'{float(monitor.get("refreshRate", 60)):.2f}'
            )
            layout.append({
                "name": name,
                "mode": mode,
                "position": f'{pos["x"]}x{pos["y"]}',
                "scale": float(monitor.get("scale", 1.0)),
            })

        _ok, message = apply_monitor_layout(layout)
        self.layout_status.set_text(message)
        GLib.timeout_add(350, self._delayed_refresh)

    def _delayed_refresh(self):
        self.refresh()
        return False

    def _monitor_card(self, monitor):
        name = monitor.get("name", "Display")
        description = monitor.get("description", "")

        panel = card(f"// {name}", description)

        summary = Gtk.Label(
            label=(
                f'{monitor.get("width")}×{monitor.get("height")}  '
                f'@ {float(monitor.get("refreshRate", 0)):.0f} HZ    '
                f'SCALE {float(monitor.get("scale", 1)):.2f}'
            ),
            xalign=0,
        )
        summary.add_css_class("monitor-summary")
        panel.append(summary)

        modes = monitor.get("availableModes") or [current_monitor_mode(monitor)]
        mode = Gtk.DropDown.new_from_strings(modes)

        # Match both resolution AND refresh rate. Previous previews selected the
        # first entry with the same resolution, which is why a 200 Hz display
        # could misleadingly open on 60 Hz.
        current_mode = normalize_monitor_mode(current_monitor_mode(monitor))
        current_index = 0
        best_delta = float("inf")
        target_refresh = float(monitor.get("refreshRate", 60.0))
        for index, candidate in enumerate(modes):
            clean = normalize_monitor_mode(candidate)
            if clean == current_mode:
                current_index = index
                best_delta = 0.0
                break
            match = __import__("re").match(r'^(\d+)x(\d+)@([0-9.]+)$', clean)
            if not match:
                continue
            if int(match.group(1)) != int(monitor.get("width", 0)) or int(match.group(2)) != int(monitor.get("height", 0)):
                continue
            delta = abs(float(match.group(3)) - target_refresh)
            if delta < best_delta:
                best_delta = delta
                current_index = index
        mode.set_selected(current_index)

        scale_values = ["0.75", "1.00", "1.25", "1.50", "1.75", "2.00"]
        scale = Gtk.DropDown.new_from_strings(scale_values)

        current_scale = float(monitor.get("scale", 1))
        nearest = min(
            range(len(scale_values)),
            key=lambda i: abs(float(scale_values[i]) - current_scale),
        )
        scale.set_selected(nearest)

        panel.append(setting_row("Resolution / refresh", mode))
        panel.append(setting_row(
            "UI scale / DPI",
            scale,
            "1.00 is native scale. Increase this if the interface feels too small."
        ))

        advanced = Gtk.Expander(label="ADVANCED POSITION")
        position = Gtk.Entry(text=f'{monitor.get("x", 0)}x{monitor.get("y", 0)}')
        advanced.set_child(setting_row(
            "Position",
            position,
            "You can type an exact value here, or use the drag editor above."
        ))
        panel.append(advanced)

        status = Gtk.Label(xalign=0)
        status.add_css_class("status")

        def apply(*_):
            model = mode.get_model()
            selected_mode = model.get_string(mode.get_selected())
            selected_scale = float(scale_values[scale.get_selected()])
            ok, message = apply_monitor(
                name,
                selected_mode,
                position.get_text().strip() or "0x0",
                selected_scale,
            )
            status.set_text(message)
            if ok:
                GLib.timeout_add(450, self._delayed_refresh)

        panel.append(action_button("APPLY DISPLAY", apply, primary=True))
        panel.append(status)
        return panel


class PowerPage(Page):
    def __init__(self):
        super().__init__()

        self.append(page_header(
            "01",
            "Devices",
            "Power Management",
            "Switch between a responsive Performance profile and an everyday Balanced profile."
        ))

        chooser = card(
            "// POWER MODE",
            "Balanced keeps boost available while reducing unnecessary power use. Performance prioritizes responsiveness."
        )

        buttons = Gtk.Grid(column_spacing=10, row_spacing=10)
        buttons.set_column_homogeneous(True)

        balanced = Gtk.Button()
        balanced.add_css_class("power-profile-card")
        balanced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        balanced_title = Gtk.Label(label="BALANCED", xalign=0)
        balanced_title.add_css_class("preset-title")
        balanced_box.append(balanced_title)
        balanced_desc = Gtk.Label(
            label="Recommended for normal desktop use. Dynamic boosting stays available, but power and heat are kept under control.",
            xalign=0,
        )
        balanced_desc.add_css_class("muted")
        balanced_desc.set_wrap(True)
        balanced_box.append(balanced_desc)
        balanced.set_child(balanced_box)
        balanced.connect("clicked", lambda *_: self.apply_mode("balanced"))
        buttons.attach(balanced, 0, 0, 1, 1)

        performance = Gtk.Button()
        performance.add_css_class("power-profile-card")
        performance_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        performance_title = Gtk.Label(label="PERFORMANCE", xalign=0)
        performance_title.add_css_class("preset-title")
        performance_box.append(performance_title)
        performance_desc = Gtk.Label(
            label="Prioritizes maximum responsiveness and sustained clocks. Expect more power use and heat.",
            xalign=0,
        )
        performance_desc.add_css_class("muted")
        performance_desc.set_wrap(True)
        performance_box.append(performance_desc)
        performance.set_child(performance_box)
        performance.connect("clicked", lambda *_: self.apply_mode("performance"))
        buttons.attach(performance, 1, 0, 1, 1)

        chooser.append(buttons)
        self.append(chooser)

        self.status_card = card("// CURRENT STATE")
        self.backend = Gtk.Label(xalign=0)
        self.driver = Gtk.Label(xalign=0)
        self.governor = Gtk.Label(xalign=0)
        self.epp = Gtk.Label(xalign=0)
        self.mode = Gtk.Label(xalign=0)

        self.status_card.append(setting_row("Mode", self.mode))
        self.status_card.append(setting_row("Backend", self.backend))
        self.status_card.append(setting_row("CPU driver", self.driver))
        self.status_card.append(setting_row("Governor", self.governor))
        self.status_card.append(setting_row("Energy preference", self.epp))
        self.append(self.status_card)

        note = card(
            "// NO EXTRA POWER STACK",
            "If power-profiles-daemon already exists, Yakushi uses it. Otherwise it uses the kernel CPUFreq / AMD P-State controls through the standard Polkit authorization dialog."
        )
        self.append(note)

        refresh = action_button("REFRESH POWER STATUS", lambda *_: self.refresh())
        self.append(refresh)

        self.message = Gtk.Label(xalign=0)
        self.message.add_css_class("status")
        self.message.set_wrap(True)
        self.append(self.message)

        self.refresh()

    def refresh(self):
        current = power_status()
        self.mode.set_text(current.get("mode", "unknown").upper())
        self.backend.set_text(current.get("backend", "Unknown"))
        self.driver.set_text(current.get("driver", "Unknown"))
        self.governor.set_text(current.get("governor", "Unknown"))
        self.epp.set_text(current.get("epp", "Not exposed"))

        if not current.get("supported"):
            self.message.set_text("No supported CPU power-management interface was detected.")

    def apply_mode(self, mode: str):
        ok, message = apply_power_mode(mode)
        self.message.set_text(message)
        if ok:
            GLib.timeout_add(250, self._delayed_refresh)

    def _delayed_refresh(self):
        self.refresh()
        return False


class InputPage(Page):
    def __init__(self):
        super().__init__()

        self.append(page_header(
            "01",
            "Devices",
            "Input",
            "Keyboard and pointer settings are applied independently, so one device cannot block the other."
        ))

        current = state()

        keyboard = card("// KEYBOARD")

        self.layouts = [
            ("Turkish", "tr"),
            ("English (US)", "us"),
            ("English (UK)", "gb"),
            ("German", "de"),
            ("French", "fr"),
            ("Spanish", "es"),
            ("Italian", "it"),
            ("Japanese", "jp"),
        ]

        self.layout = Gtk.DropDown.new_from_strings([label for label, _ in self.layouts])
        current_layout = current["keyboard"]["layout"]
        index = next(
            (i for i, (_, code) in enumerate(self.layouts) if code == current_layout),
            0,
        )
        self.layout.set_selected(index)

        self.repeat_rate = spin(current["keyboard"]["repeat_rate"], 1, 100)
        self.repeat_delay = spin(current["keyboard"]["repeat_delay"], 100, 2000, 10)

        keyboard.append(setting_row("Language", self.layout))
        keyboard.append(setting_row("Repeat speed", self.repeat_rate))
        keyboard.append(setting_row("Repeat delay", self.repeat_delay))

        self.keyboard_status = Gtk.Label(xalign=0)
        self.keyboard_status.add_css_class("status")
        keyboard.append(action_button("APPLY KEYBOARD", self.apply_keyboard_settings, primary=True))
        keyboard.append(self.keyboard_status)
        self.append(keyboard)

        mouse = card(
            "// MOUSE",
            "Pointer speed uses Hyprland’s live device API. Applying a speed profile temporarily disables force_no_accel because that option bypasses sensitivity."
        )

        devices = pointer_devices()
        device_text = Gtk.Label(
            label=(
                f"{len(devices)} pointer device(s) detected: "
                + ", ".join(str(item.get("name", "Pointer")) for item in devices[:3])
                + (" …" if len(devices) > 3 else "")
            ) if devices else "No pointer device was reported; global input settings will still be applied.",
            xalign=0,
        )
        device_text.add_css_class("input-device-note")
        device_text.set_wrap(True)
        mouse.append(device_text)

        self.sensitivity = slider(
            current["mouse"]["sensitivity"],
            -1.0,
            1.0,
            0.05,
        )

        self.accel_options = ["Adaptive", "Flat"]
        self.accel = Gtk.DropDown.new_from_strings(self.accel_options)
        self.accel.set_selected(
            1 if current["mouse"]["accel_profile"] == "flat" else 0
        )

        self.left_handed = Gtk.ToggleButton(label="ON" if current["mouse"]["left_handed"] else "OFF")
        self.left_handed.add_css_class("input-toggle")
        self.left_handed.set_active(current["mouse"]["left_handed"])
        self.left_handed.connect("toggled", self._toggle_label)

        self.natural_scroll = Gtk.ToggleButton(label="ON" if current["mouse"]["natural_scroll"] else "OFF")
        self.natural_scroll.add_css_class("input-toggle")
        self.natural_scroll.set_active(current["mouse"]["natural_scroll"])
        self.natural_scroll.connect("toggled", self._toggle_label)

        mouse.append(setting_row("Pointer speed", self.sensitivity, "-1.00 is slowest, +1.00 is fastest. Changes are verified against the live device state."))
        mouse.append(setting_row("Acceleration", self.accel))
        mouse.append(setting_row("Left-handed buttons", self.left_handed))
        mouse.append(setting_row("Natural scrolling", self.natural_scroll))

        self.mouse_status = Gtk.Label(xalign=0)
        self.mouse_status.add_css_class("status")
        mouse.append(action_button("APPLY MOUSE", self.apply_mouse_settings, primary=True))
        mouse.append(self.mouse_status)
        self.append(mouse)

    @staticmethod
    def _toggle_label(button):
        button.set_label("ON" if button.get_active() else "OFF")

    def apply_keyboard_settings(self, *_):
        _, layout_code = self.layouts[self.layout.get_selected()]
        keyboard_values = {
            "layout": layout_code,
            "repeat_rate": int(self.repeat_rate.get_value()),
            "repeat_delay": int(self.repeat_delay.get_value()),
        }
        _ok, message = apply_keyboard(keyboard_values)
        self.keyboard_status.set_text(message)

    def apply_mouse_settings(self, *_):
        mouse_values = {
            "sensitivity": round(self.sensitivity.scale.get_value(), 2),
            "accel_profile": "flat" if self.accel.get_selected() == 1 else "adaptive",
            "left_handed": self.left_handed.get_active(),
            "natural_scroll": self.natural_scroll.get_active(),
        }
        _ok, message = apply_mouse(mouse_values)
        self.mouse_status.set_text(message)


class WallpaperSelector(Gtk.Box):
    def __init__(self, initial: str = "", on_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        self.path = Path(initial).expanduser() if initial else current_wallpaper()
        self.on_change = on_change

        self.preview = Gtk.Picture()
        self.preview.set_content_fit(Gtk.ContentFit.COVER)
        self.preview.set_can_shrink(True)
        self.preview.set_size_request(-1, 180)
        self.preview.add_css_class("session-wallpaper-preview")
        self.append(self.preview)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.label = Gtk.Label(xalign=0)
        self.label.set_hexpand(True)
        self.label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.label.add_css_class("muted")
        row.append(self.label)
        row.append(action_button("USE DESKTOP", self._desktop))
        row.append(action_button("BROWSE", self._browse))
        self.append(row)
        self._refresh()

    def value(self) -> str:
        return str(self.path) if self.path and self.path.exists() else ""

    def _set(self, path: Path | None):
        if path and path.exists():
            self.path = path
            self._refresh()
            if self.on_change:
                self.on_change(path)

    def _refresh(self):
        if self.path and self.path.exists():
            self.preview.set_filename(str(self.path))
            self.label.set_text(str(self.path))
        else:
            self.preview.set_paintable(None)
            self.label.set_text("No wallpaper selected — theme background color will be used.")

    def _desktop(self, *_):
        self._set(current_wallpaper())

    def _browse(self, *_):
        chooser = Gtk.FileChooserNative(
            title="Choose wallpaper",
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Use wallpaper",
            cancel_label="Cancel",
        )
        filt = Gtk.FileFilter()
        filt.set_name("Images")
        for mime in ("image/png", "image/jpeg", "image/webp"):
            filt.add_mime_type(mime)
        chooser.add_filter(filt)

        def response(dialog, result):
            if result == Gtk.ResponseType.ACCEPT:
                file = dialog.get_file()
                if file:
                    path = file.get_path()
                    if path:
                        self._set(Path(path))
            dialog.destroy()

        chooser.connect("response", response)
        chooser.show()


class LockPage(Page):
    def __init__(self):
        super().__init__()
        info = lock_status()
        self.append(page_header(
            "04", "Session", "Lock Screen",
            "Build a Hyprlock screen that follows your Yakushi palette, wallpaper, and typography."
        ))

        state_card = card("// HYPRLOCK", "Yakushi writes the standard ~/.config/hypr/hyprlock.conf file and keeps it in REVERT history.")
        availability = Gtk.Label(
            label="HYPRLOCK DETECTED" if info.get("available") else "HYPRLOCK NOT AVAILABLE",
            xalign=0,
        )
        availability.add_css_class("status")
        state_card.append(availability)
        self.append(state_card)

        wall = card("// LOCK WALLPAPER", "Use the current desktop wallpaper or choose a separate image for the lock screen.")
        self.wallpaper = WallpaperSelector(info.get("wallpaper", ""))
        wall.append(self.wallpaper)
        self.append(wall)

        look = card("// BACKDROP")
        self.blur_passes = spin(int(info.get("blur_passes", 3)), 0, 8)
        self.blur_size = spin(int(info.get("blur_size", 8)), 1, 20)
        self.brightness = slider(float(info.get("brightness", 0.72)), 0.25, 1.0, 0.01)
        look.append(setting_row("Blur passes", self.blur_passes, "0 disables blur; 2–4 is usually enough."))
        look.append(setting_row("Blur size", self.blur_size))
        look.append(setting_row("Background brightness", self.brightness, "Lower values create a darker, calmer lock screen."))
        self.append(look)

        clock = card("// CLOCK & DATE")
        self.clock_24h = Gtk.CheckButton(label="24-hour clock")
        self.clock_24h.set_active(bool(info.get("clock_24h", True)))
        self.show_date = Gtk.CheckButton(label="Show date")
        self.show_date.set_active(bool(info.get("show_date", True)))
        clock.append(self.clock_24h)
        clock.append(self.show_date)
        self.append(clock)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")
        actions = Gtk.Box(spacing=8)
        actions.append(action_button("APPLY LOCK SCREEN", self.apply, primary=True))
        actions.append(action_button("LOCK NOW", self.test))
        self.append(actions)
        self.append(self.status)

    def settings(self):
        return LockSettings(
            wallpaper=self.wallpaper.value(),
            blur_passes=int(self.blur_passes.get_value()),
            blur_size=int(self.blur_size.get_value()),
            brightness=round(self.brightness.scale.get_value(), 2),
            clock_24h=self.clock_24h.get_active(),
            show_date=self.show_date.get_active(),
        )

    def apply(self, *_):
        _ok, message = apply_lock(self.settings())
        self.status.set_text(message)

    def test(self, *_):
        ok, message = apply_lock(self.settings())
        if not ok:
            self.status.set_text(message)
            return
        _ok, message = lock_now()
        self.status.set_text(message)


class LoginPage(Page):
    def __init__(self):
        super().__init__()
        info = sddm_status()
        self.append(page_header(
            "04", "Session", "Login Screen",
            "Make SDDM visually match the Yakushi Hyprlock screen while keeping SDDM as the real boot login manager."
        ))

        status_card = card("// SDDM STATUS", "Installing the theme needs administrator authorization because SDDM themes live under /usr/share/sddm. Yakushi opens a dedicated Kitty sudo terminal so the password prompt is always visible and does not depend on a graphical Polkit agent.")
        text = "SDDM detected" if info.get("available") else "SDDM is not installed"
        active = info.get("active_theme") or "embedded/default"
        state = "ACTIVE" if info.get("active") else ("INSTALLED" if info.get("installed") else "NOT INSTALLED")
        label = Gtk.Label(label=f"{text}  //  YAKUSHI: {state}  //  ACTIVE: {active}", xalign=0)
        label.add_css_class("monitor-summary")
        status_card.append(label)
        self.append(status_card)

        preview_card = card("// YAKUSHI GREETER", "The login theme mirrors Lock Screen Studio: wallpaper, clock/date preference, darkness, blur intent, Theme Studio palette, and desktop serif typography.")
        mock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        mock.add_css_class("sddm-preview-card")
        mark = Gtk.Label(label="薬")
        mark.add_css_class("sddm-preview-symbol")
        mock.append(mark)
        title = Gtk.Label(label="YAKUSHI // LOGIN")
        title.add_css_class("meta")
        mock.append(title)
        time = Gtk.Label(label="21:45")
        time.add_css_class("sddm-preview-time")
        mock.append(time)
        field = Gtk.Label(label="••••••••")
        field.add_css_class("sddm-preview-field")
        mock.append(field)
        preview_card.append(mock)
        self.append(preview_card)

        wall = card("// LOGIN WALLPAPER", "Defaults to the Lock Screen wallpaper. Choose a different image only if you want boot login and Hyprlock to diverge. Yakushi copies it into the system theme so SDDM can always read it.")
        self.wallpaper = WallpaperSelector(info.get("wallpaper", ""))
        wall.append(self.wallpaper)
        self.append(wall)

        safety = card(
            "// SAFE APPLY",
            "Yakushi installs its own theme directory and a dedicated SDDM config override. If /etc/sddm.conf already controls the theme, its original copy is preserved for Disable/Restore."
        )
        self.append(safety)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")
        self._sddm_busy = False
        actions = Gtk.Box(spacing=8)
        self.preview_button = action_button("PREVIEW SDDM", self.preview)
        self.install_button = action_button("INSTALL / UPDATE SDDM", self.install, primary=True)
        self.disable_button = action_button("DISABLE YAKUSHI SDDM", self.disable)
        actions.append(self.preview_button)
        actions.append(self.install_button)
        actions.append(self.disable_button)
        self.append(actions)
        self.append(self.status)

    def settings(self):
        return SddmSettings(wallpaper=self.wallpaper.value(), sync_palette=True)

    def preview(self, *_):
        _ok, message = preview_sddm(self.settings())
        self.status.set_text(message)

    def _set_sddm_busy(self, busy: bool, message: str = ""):
        self._sddm_busy = busy
        self.preview_button.set_sensitive(not busy)
        self.install_button.set_sensitive(not busy)
        self.disable_button.set_sensitive(not busy)
        if message:
            self.status.set_text(message)

    def _finish_sddm_action(self, _ok: bool, message: str):
        self._set_sddm_busy(False, message)
        return GLib.SOURCE_REMOVE

    def _run_sddm_action(self, operation: str):
        if self._sddm_busy:
            return

        # Read GTK widget state on the main thread before starting background
        # work. pkexec/sudo may wait for user interaction, so never block the
        # GTK main loop while privileged SDDM work is in progress.
        settings = self.settings() if operation == "install" else None
        waiting = (
            "Opening administrator terminal…"
            if operation == "install"
            else "Opening administrator terminal to restore SDDM…"
        )
        self._set_sddm_busy(True, waiting)

        def worker():
            try:
                if operation == "install":
                    ok, message = install_sddm(settings)
                else:
                    ok, message = disable_sddm()
            except Exception as exc:
                ok, message = False, f"SDDM operation failed: {exc}"
            GLib.idle_add(self._finish_sddm_action, ok, message)

        threading.Thread(
            target=worker,
            name=f"yakushi-sddm-{operation}",
            daemon=True,
        ).start()

    def install(self, *_):
        self._run_sddm_action("install")

    def disable(self, *_):
        self._run_sddm_action("disable")


class TerminalPage(Page):
    COLOR_MODES = ["FOLLOW YAKUSHI THEME", "CUSTOM"]

    def __init__(self):
        super().__init__()

        self.append(page_header(
            "03",
            "Apps & Keys",
            "Terminal",
            "Kitty appearance, transparency, a complete theme-aware palette and one-click Liquid Glass styling."
        ))

        current = kitty_load()
        colors = kitty_colors_load()

        preview = card("// LIVE PREVIEW")
        self.preview_mock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.preview_mock.add_css_class("terminal-preview")
        self.preview_name = f"yakushi-terminal-preview-{id(self)}"
        self.preview_mock.set_name(self.preview_name)
        line1 = Gtk.Label(label="user@hyprland  ~", xalign=0)
        line1.add_css_class("terminal-preview-accent")
        self.preview_mock.append(line1)
        self.preview_mock.append(Gtk.Label(label="❯ yakushi-deck", xalign=0))
        self.preview_mock.append(Gtk.Label(label="Desktop control, without replacing the shell.", xalign=0))
        preview.append(self.preview_mock)
        self.append(preview)

        presets = card(
            "// TERMINAL PRESETS",
            "One click carries the Raycast-style glass language into Kitty without replacing your font size or shell setup."
        )
        liquid_button = Gtk.Button()
        liquid_button.add_css_class("preset-card")
        liquid_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        liquid_title = Gtk.Label(label="01  LIQUID GLASS", xalign=0)
        liquid_title.add_css_class("preset-title")
        liquid_content.append(liquid_title)
        liquid_description = Gtk.Label(
            label="78% tonal glass, native Kitty blur, balanced padding and a soft fade tab bar.",
            xalign=0,
        )
        liquid_description.set_wrap(True)
        liquid_description.add_css_class("muted")
        liquid_content.append(liquid_description)
        liquid_button.set_child(liquid_content)
        liquid_button.connect("clicked", self.apply_liquid_glass)
        presets.append(liquid_button)
        self.append(presets)

        settings = card("// KITTY")
        self.font_size = spin(current.font_size, 7, 28, 0.5, 1)
        self.padding = spin(current.padding, 0, 32)
        self.opacity = slider(current.opacity, 0.25, 1.0, 0.01)

        settings.append(setting_row("Font size", self.font_size))
        settings.append(setting_row("Window padding", self.padding))
        settings.append(setting_row(
            "Background opacity",
            self.opacity,
            "Lower values reveal more of the Hyprland blur."
        ))
        self.append(settings)

        color_panel = card(
            "// TERMINAL COLORS",
            "FOLLOW keeps Kitty synchronized with Theme Studio and Auto Color. CUSTOM lets you choose your own background, foreground and accent. Accent also tints Kitty's 16-color ANSI palette, so Fastfetch and CLI colors stop being locked to an older red theme."
        )
        self.color_mode = Gtk.DropDown.new_from_strings(self.COLOR_MODES)
        self.color_mode.set_selected(0 if colors.mode == "follow" else 1)
        self.color_mode.connect("notify::selected", self._color_mode_changed)
        color_panel.append(setting_row(
            "Color source",
            self.color_mode,
            "FOLLOW updates automatically whenever the Yakushi desktop palette changes."
        ))

        self.color_buttons = {}
        color_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        color_grid.set_column_homogeneous(True)
        for index, (key, label, value) in enumerate((
            ("background", "Background", colors.background),
            ("foreground", "Foreground", colors.foreground),
            ("accent", "Accent / ANSI", colors.accent),
        )):
            button = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())
            rgba = Gdk.RGBA()
            rgba.parse(value)
            button.set_rgba(rgba)
            button.connect("notify::rgba", self._color_changed)
            self.color_buttons[key] = button
            chip = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            chip.add_css_class("color-chip")
            title = Gtk.Label(label=label, xalign=0)
            title.add_css_class("setting-name")
            chip.append(title)
            chip.append(button)
            color_grid.attach(chip, index, 0, 1, 1)
        color_panel.append(color_grid)
        self.append(color_panel)

        color_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        color_actions.append(action_button("APPLY TERMINAL COLORS", self.apply_colors, primary=True))
        color_actions.append(action_button("LOAD CURRENT DESKTOP THEME", self.load_desktop_theme))
        self.append(color_actions)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")

        self.append(action_button("APPLY KITTY SETTINGS", self.apply, primary=True))
        self.append(self.status)

        self._preview_provider = Gtk.CssProvider()
        self.preview_mock.get_style_context().add_provider(
            self._preview_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2,
        )
        self._color_mode_changed()
        self._refresh_preview()

    @staticmethod
    def _button_hex(button) -> str:
        rgba = button.get_rgba()
        return "#{:02x}{:02x}{:02x}".format(
            round(rgba.red * 255),
            round(rgba.green * 255),
            round(rgba.blue * 255),
        )

    def _set_color_buttons(self, background: str, foreground: str, accent: str):
        for key, value in (
            ("background", background),
            ("foreground", foreground),
            ("accent", accent),
        ):
            rgba = Gdk.RGBA()
            rgba.parse(value)
            self.color_buttons[key].set_rgba(rgba)

    def _color_mode_changed(self, *_):
        follow = self.color_mode.get_selected() == 0
        if follow:
            palette = load_palette()
            self._set_color_buttons(palette.bg, palette.fg, palette.accent)
        for button in self.color_buttons.values():
            button.set_sensitive(not follow)
        self._refresh_preview()

    def _color_changed(self, *_):
        self._refresh_preview()

    def _refresh_preview(self):
        if not hasattr(self, "_preview_provider"):
            return
        background = self._button_hex(self.color_buttons["background"])
        foreground = self._button_hex(self.color_buttons["foreground"])
        accent = self._button_hex(self.color_buttons["accent"])
        bg_rgb = tuple(int(background[index:index + 2], 16) for index in (1, 3, 5))
        fg_rgb = tuple(int(foreground[index:index + 2], 16) for index in (1, 3, 5))
        self._preview_provider.load_from_data((
            f"#{self.preview_name} {{ background-color: rgba({bg_rgb[0]}, {bg_rgb[1]}, {bg_rgb[2]}, 0.78); "
            f"border-color: rgba({fg_rgb[0]}, {fg_rgb[1]}, {fg_rgb[2]}, 0.14); }}\n"
            f"#{self.preview_name} label {{ color: {foreground}; }}\n"
            f"#{self.preview_name} .terminal-preview-accent {{ color: {accent}; font-weight: 800; }}"
        ).encode())

    def load_desktop_theme(self, *_):
        palette = load_palette()
        self.color_mode.set_selected(0)
        self._set_color_buttons(palette.bg, palette.fg, palette.accent)
        for button in self.color_buttons.values():
            button.set_sensitive(False)
        self._refresh_preview()
        self.status.set_text("Current Yakushi desktop palette loaded. Apply terminal colors to enable automatic FOLLOW mode.")

    def apply_colors(self, *_):
        follow = self.color_mode.get_selected() == 0
        if follow:
            palette = load_palette()
            value = KittyColorState(
                mode="follow",
                background=palette.bg,
                foreground=palette.fg,
                accent=palette.accent,
            )
            self._set_color_buttons(value.background, value.foreground, value.accent)
        else:
            value = KittyColorState(
                mode="custom",
                background=self._button_hex(self.color_buttons["background"]),
                foreground=self._button_hex(self.color_buttons["foreground"]),
                accent=self._button_hex(self.color_buttons["accent"]),
            )
        ok, message = kitty_colors_save(value)
        self._refresh_preview()
        if ok:
            self.status.set_text(message + " Running Kitty instances were asked to reload; new Kitty windows use this palette too.")
        else:
            self.status.set_text("ERROR: " + message)

    def apply_liquid_glass(self, *_):
        palette = load_palette()
        colors = KittyColorState(
            mode="follow",
            background=palette.bg,
            foreground=palette.fg,
            accent=palette.accent,
        )
        ok, message = kitty_apply_preset("liquid_glass", colors)
        if not ok:
            self.status.set_text("ERROR: " + message)
            return

        self.opacity.scale.set_value(0.78)
        self.padding.set_value(12)
        self.color_mode.set_selected(0)
        self._set_color_buttons(colors.background, colors.foreground, colors.accent)
        for button in self.color_buttons.values():
            button.set_sensitive(False)
        self._refresh_preview()
        self.status.set_text(message)

    def apply(self, *_):
        value = KittyState(
            font_size=self.font_size.get_value(),
            opacity=round(self.opacity.scale.get_value(), 2),
            padding=int(self.padding.get_value()),
        )
        _, message = kitty_save(value)
        self.status.set_text(message)


class FastfetchPage(Page):
    def __init__(self):
        super().__init__()

        current = fastfetch_load()
        self.append(page_header(
            "03",
            "Apps & Keys",
            "Fastfetch",
            "Control startup behavior, paste your own ASCII art, toggle individual information modules, or edit the complete Fastfetch JSONC configuration."
        ))

        startup = card(
            "// STARTUP",
            "Turn Fastfetch on or off when a new terminal shell starts. On Fish, Yakushi normalizes legacy startup calls and owns one managed greeting: OFF means zero Fastfetch runs, ON means exactly one. Manual Fastfetch use is never disabled."
        )
        self.autorun = Gtk.Switch(active=current.auto_run)
        startup.append(setting_row(
            "Run Fastfetch in new terminals",
            self.autorun,
            f"Detected shell: {current.shell}."
        ))
        startup_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        startup_actions.append(action_button("APPLY AUTO-RUN", self.apply_autorun, primary=True))
        startup_actions.append(action_button("PREVIEW IN KITTY", self.preview))
        startup.append(startup_actions)
        if current.external_autorun:
            note = Gtk.Label(
                label="Existing Fastfetch startup call detected in Fish. APPLY AUTO-RUN will normalize it into Yakushi's single managed startup source so duplicate Fastfetch output cannot stack.",
                xalign=0,
            )
            note.set_wrap(True)
            note.add_css_class("muted")
            startup.append(note)
        self.append(startup)

        ascii_panel = card(
            "// ASCII ART",
            "Paste any text/ASCII art here. SAVE ASCII + PREVIEW keeps your source clean in ~/.config/fastfetch/logo.txt, generates a color-aware render copy, and opens it in Kitty immediately. The logo follows Terminal Studio accent color."
        )
        self.logo_view = Gtk.TextView()
        self.logo_view.set_monospace(True)
        self.logo_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.logo_view.add_css_class("code-editor")
        self.logo_view.get_buffer().set_text(current.logo)
        logo_scroll = Gtk.ScrolledWindow()
        logo_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        logo_scroll.set_min_content_height(230)
        logo_scroll.set_child(self.logo_view)
        ascii_panel.append(logo_scroll)

        self.logo_left = spin(current.logo_padding_left, 0, 40)
        self.logo_top = spin(current.logo_padding_top, 0, 20)
        position_grid = Gtk.Grid(column_spacing=18, row_spacing=8)
        position_grid.set_column_homogeneous(True)
        position_grid.attach(setting_row("Horizontal offset", self.logo_left, "Moves the ASCII logo to the right."), 0, 0, 1, 1)
        position_grid.attach(setting_row("Vertical offset", self.logo_top, "Adds empty rows above the ASCII logo."), 1, 0, 1, 1)
        ascii_panel.append(position_grid)

        ascii_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ascii_actions.append(action_button("SAVE ASCII + PREVIEW", self.save_logo, primary=True))
        ascii_actions.append(action_button("APPLY POSITION + PREVIEW", self.apply_logo_position))
        ascii_actions.append(action_button("RELOAD ASCII", self.reload_logo))
        ascii_panel.append(ascii_actions)
        self.append(ascii_panel)

        modules_panel = card(
            "// MODULES",
            "Hide information you do not care about without deleting the rest of your config. Disabled modules remember their position, so turning them back on does not dump them at the bottom. For example, disable Window manager / Hyprland to remove the Hyprland version line. Existing custom module objects are preserved and restored when possible."
        )
        self.module_switches = {}
        module_grid = Gtk.Grid(column_spacing=18, row_spacing=8)
        module_grid.set_column_homogeneous(True)
        for index, (module_type, label) in enumerate(FASTFETCH_COMMON_MODULES):
            switch = Gtk.Switch(active=bool(current.modules.get(module_type, False)))
            switch.set_halign(Gtk.Align.END)
            self.module_switches[module_type] = switch
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.add_css_class("fastfetch-module")
            title = Gtk.Label(label=label, xalign=0)
            title.set_hexpand(True)
            row.append(title)
            row.append(switch)
            module_grid.attach(row, index % 2, index // 2, 1, 1)
        modules_panel.append(module_grid)
        modules_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        modules_actions.append(action_button("APPLY MODULES + PREVIEW", self.apply_modules, primary=True))
        modules_actions.append(action_button("RELOAD MODULES", self.reload_modules))
        modules_actions.append(action_button("FOLLOW TERMINAL ACCENT", self.follow_terminal_accent))
        modules_panel.append(modules_actions)
        self.append(modules_panel)

        advanced = card(
            "// ADVANCED JSONC",
            "Full Fastfetch control. Edit any supported Fastfetch option here. Yakushi checks JSONC syntax and asks Fastfetch to load the candidate config before replacing your current file."
        )
        self.config_view = Gtk.TextView()
        self.config_view.set_monospace(True)
        self.config_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.config_view.add_css_class("code-editor")
        self.config_view.get_buffer().set_text(current.config_text)
        config_scroll = Gtk.ScrolledWindow()
        config_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        config_scroll.set_min_content_height(330)
        config_scroll.set_child(self.config_view)
        advanced.append(config_scroll)
        advanced_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        advanced_actions.append(action_button("VALIDATE + APPLY CONFIG", self.apply_config, primary=True))
        advanced_actions.append(action_button("RELOAD CONFIG", self.reload_config))
        advanced_actions.append(action_button("RESET SAFE DEFAULT", self.reset_config))
        advanced_actions.append(action_button("PREVIEW IN KITTY", self.preview))
        advanced.append(advanced_actions)
        self.append(advanced)

        self.status = Gtk.Label(xalign=0)
        self.status.set_wrap(True)
        self.status.add_css_class("status")
        if not current.available:
            self.status.set_text("Fastfetch is not installed yet. Fresh Yakushi installs include the official Arch fastfetch package.")
        self.append(self.status)

    @staticmethod
    def _view_text(view: Gtk.TextView) -> str:
        buffer = view.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

    def _set_view_text(self, view: Gtk.TextView, text: str):
        view.get_buffer().set_text(text)

    def apply_autorun(self, *_):
        ok, message = set_fastfetch_autorun(self.autorun.get_active())
        self.status.set_text(message)
        if not ok:
            self.autorun.set_active(fastfetch_load().auto_run)

    def preview(self, *_):
        _ok, message = preview_fastfetch()
        self.status.set_text(message)

    def save_logo(self, *_):
        ok, message = save_fastfetch_logo(self._view_text(self.logo_view))
        if ok:
            state = fastfetch_load()
            self._set_view_text(self.config_view, state.config_text)
            _preview_ok, preview_message = preview_fastfetch()
            message += " " + preview_message
        self.status.set_text(message)

    def apply_logo_position(self, *_):
        ok, message = set_fastfetch_logo_padding(
            int(self.logo_left.get_value()),
            int(self.logo_top.get_value()),
        )
        if ok:
            state = fastfetch_load()
            self._set_view_text(self.config_view, state.config_text)
            preview_ok, preview_message = preview_fastfetch()
            if preview_ok:
                message += " " + preview_message
            else:
                message += " Preview could not open: " + preview_message
        self.status.set_text(message)

    def reload_logo(self, *_):
        state = fastfetch_load()
        self._set_view_text(self.logo_view, state.logo)
        self.logo_left.set_value(state.logo_padding_left)
        self.logo_top.set_value(state.logo_padding_top)
        self.status.set_text("ASCII art and logo position reloaded from Fastfetch config.")

    def apply_modules(self, *_):
        states = {name: switch.get_active() for name, switch in self.module_switches.items()}
        ok, message = apply_fastfetch_modules(states)
        if ok:
            state = fastfetch_load()
            self._set_view_text(self.config_view, state.config_text)
            for name, switch in self.module_switches.items():
                switch.set_active(bool(state.modules.get(name, False)))
            preview_ok, preview_message = preview_fastfetch()
            if preview_ok:
                message += " " + preview_message
            else:
                message += " Preview could not open: " + preview_message
        self.status.set_text(message)


    def follow_terminal_accent(self, *_):
        ok, message = sync_fastfetch_terminal_colors()
        if ok:
            state = fastfetch_load()
            self._set_view_text(self.config_view, state.config_text)
            preview_ok, preview_message = preview_fastfetch()
            if preview_ok:
                message += " " + preview_message
        self.status.set_text(message)

    def reload_modules(self, *_):
        state = fastfetch_load()
        for name, switch in self.module_switches.items():
            switch.set_active(bool(state.modules.get(name, False)))
        self.status.set_text("Module states reloaded from Fastfetch config.")

    def apply_config(self, *_):
        ok, message = save_fastfetch_config(self._view_text(self.config_view))
        if ok:
            self.reload_modules()
            self.status.set_text(message)
        else:
            self.status.set_text(message)

    def reset_config(self, *_):
        ok, message = reset_fastfetch_config()
        if ok:
            state = fastfetch_load()
            self._set_view_text(self.config_view, state.config_text)
            self._set_view_text(self.logo_view, state.logo)
            self.logo_left.set_value(state.logo_padding_left)
            self.logo_top.set_value(state.logo_padding_top)
            for name, switch in self.module_switches.items():
                switch.set_active(bool(state.modules.get(name, False)))
        self.status.set_text(message if ok else "ERROR: " + message)

    def reload_config(self, *_):
        state = fastfetch_load()
        self._set_view_text(self.config_view, state.config_text)
        for name, switch in self.module_switches.items():
            switch.set_active(bool(state.modules.get(name, False)))
        self.status.set_text("Fastfetch JSONC reloaded from disk.")


class NautilusPage(Page):
    def __init__(self):
        super().__init__()

        self.append(page_header(
            "03",
            "Apps & Keys",
            "Nautilus",
            "Make GNOME Files blend into the desktop without patching libadwaita. Yakushi applies opacity at the Hyprland compositor layer."
        ))

        current = nautilus_status()
        panel = card(
            "// WINDOW OPACITY",
            "This affects the complete Nautilus window. 100% removes Yakushi's override. Lower values reveal your wallpaper behind the file manager while keeping Nautilus itself untouched."
        )
        self.opacity = slider(float(current.get("opacity", 1.0)), 0.30, 1.0, 0.01)
        panel.append(setting_row(
            "Nautilus opacity",
            self.opacity,
            "Recommended range: 0.78–0.94. Very low opacity can reduce filename readability."
        ))
        self.append(panel)

        info = card(
            "// HYPRLAND RULE",
            "Yakushi writes one clearly marked, reversible rule to your main Hyprland config and reloads it only after creating a backup. A new config error triggers an automatic rollback."
        )
        self.detected = Gtk.Label(xalign=0)
        self.detected.set_wrap(True)
        self.detected.add_css_class("muted")
        available = "DETECTED" if current.get("available") else "NOT INSTALLED (OPTIONAL)"
        target = current.get("config") or "Hyprland config not found"
        self.detected.set_text(f"NAUTILUS // {available}    CONFIG // {target}")
        info.append(self.detected)
        self.append(info)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        apply_button = Gtk.Button(label="APPLY NAUTILUS OPACITY")
        apply_button.add_css_class("primary")
        apply_button.connect("clicked", self.apply)
        actions.append(apply_button)

        reset = Gtk.Button(label="RESET TO 100%")
        reset.connect("clicked", self.reset)
        actions.append(reset)

        launch = Gtk.Button(label="OPEN NAUTILUS")
        launch.connect("clicked", self.launch)
        actions.append(launch)
        self.append(actions)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")
        self.append(self.status)

    def apply(self, *_):
        ok, message = apply_nautilus_opacity(round(self.opacity.scale.get_value(), 2))
        self.status.set_text(message)

    def reset(self, *_):
        self.opacity.scale.set_value(1.0)
        ok, message = apply_nautilus_opacity(1.0)
        self.status.set_text(message)

    def launch(self, *_):
        _ok, message = open_nautilus()
        self.status.set_text(message)


class RofiPage(Page):
    def __init__(self):
        super().__init__()
        self.append(page_header(
            "03",
            "Apps & Keys",
            "Rofi",
            "Choose a Yakushi launcher preset, including the Raycast-inspired liquid-glass command bar."
        ))

        current = rofi_load()

        themes = card(
            "// ROFI THEMES",
            "Presets change launcher geometry and surface treatment. Colors follow Theme Studio; opacity stays independent. Raycast Glass safely adds its own Hyprland layer-blur rule; blur strength stays in Appearance."
        )
        theme_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        theme_grid.set_column_homogeneous(True)
        for index, (key, title, description) in enumerate(rofi_theme_presets()):
            button = Gtk.Button()
            button.add_css_class("preset-card")
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            name = Gtk.Label(label=f"0{index + 1}  {title}", xalign=0)
            name.add_css_class("preset-title")
            content.append(name)
            note = Gtk.Label(label=description, xalign=0)
            note.set_wrap(True)
            note.add_css_class("muted")
            content.append(note)
            button.set_child(content)
            button.connect("clicked", self.apply_theme, key)
            theme_grid.attach(button, index % 2, index // 2, 1, 1)
        themes.append(theme_grid)
        self.append(themes)

        preview = card(
            "// RAYCAST GLASS PREVIEW",
            "Layered glass, neutral typography, an accent selection rail and quiet clickable actions."
        )
        mock = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        mock.add_css_class("rofi-preview")
        search = Gtk.Label(label="   Search applications...", xalign=0)
        search.add_css_class("rofi-preview-search")
        mock.append(search)

        section = Gtk.Label(label="APPLICATIONS", xalign=0)
        section.add_css_class("rofi-preview-section")
        mock.append(section)

        for index, text in enumerate(["󰈹   Firefox", "   Kitty", "󰉋   Files"]):
            item = Gtk.Label(label=text, xalign=0)
            item.add_css_class("rofi-preview-item")
            if index == 0:
                item.add_css_class("rofi-preview-selected")
            mock.append(item)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.add_css_class("rofi-preview-footer")
        brand = Gtk.Label(label="薬  YAKUSHI", xalign=0)
        brand.set_hexpand(True)
        brand.add_css_class("rofi-preview-brand")
        footer.append(brand)
        close_key = Gtk.Label(label="Esc", xalign=1)
        close_key.add_css_class("rofi-preview-close")
        footer.append(close_key)
        open_key = Gtk.Label(label="↵  Open", xalign=1)
        open_key.add_css_class("rofi-preview-open")
        footer.append(open_key)
        mock.append(footer)

        preview.append(mock)
        self.append(preview)

        settings = card("// FINE TUNING")
        self.font = Gtk.Entry(text=current.font)
        self.width = spin(current.width, 400, 1100, 10)
        self.radius = spin(current.radius, 0, 30)
        self.padding = spin(current.padding, 8, 50)
        self.lines = spin(current.lines, 3, 15)
        self.opacity = slider(current.opacity, 0.20, 1.0, 0.01)
        settings.append(setting_row("Font", self.font))
        settings.append(setting_row("Window width", self.width))
        settings.append(setting_row("Corner roundness", self.radius))
        settings.append(setting_row("Outer padding", self.padding))
        settings.append(setting_row("Visible results", self.lines))
        settings.append(setting_row("Background opacity", self.opacity, "Uses real compositor transparency and survives Theme Studio palette changes."))
        self.append(settings)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")

        actions = Gtk.Box(spacing=8)
        actions.append(action_button("APPLY FINE TUNING", self.apply, primary=True))
        actions.append(action_button("OPEN ROFI", self.open_rofi))
        self.append(actions)
        self.append(self.status)

    def _reload_controls(self):
        current = rofi_load()
        self.font.set_text(current.font)
        self.width.set_value(current.width)
        self.radius.set_value(current.radius)
        self.padding.set_value(current.padding)
        self.lines.set_value(current.lines)
        self.opacity.scale.set_value(current.opacity)

    def apply_theme(self, _button, theme_key):
        ok, message = rofi_apply_theme(theme_key)
        self.status.set_text(message)
        if ok:
            self._reload_controls()

    def apply(self, *_):
        value = RofiState(
            font=self.font.get_text().strip() or "JetBrainsMono Nerd Font 12",
            width=int(self.width.get_value()),
            radius=int(self.radius.get_value()),
            padding=int(self.padding.get_value()),
            lines=int(self.lines.get_value()),
            opacity=round(self.opacity.scale.get_value(), 2),
        )
        _, message = rofi_save(value)
        self.status.set_text(message)

    def open_rofi(self, *_):
        run(["sh", "-lc", "rofi -show drun >/tmp/yakushi-rofi.log 2>&1 &"], timeout=2)
        self.status.set_text("Rofi launched.")

class ModuleSwitch(Gtk.Switch):
    """Tiny fixed-size module toggle: neutral grey OFF, Yakushi red ON."""
    def __init__(self, active=False):
        super().__init__()
        self.add_css_class("module-switch")
        self.set_active(bool(active))
        self.set_hexpand(False)
        self.set_vexpand(False)
        self.set_halign(Gtk.Align.END)
        self.set_valign(Gtk.Align.CENTER)
        self.set_size_request(30, 16)


class ModuleChip(Gtk.Box):
    def __init__(self, owner, module: str, lane: str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        self.owner = owner
        self.module = module
        self.lane = lane
        self.add_css_class("module-chip")
        self.set_tooltip_text(owner.DESCRIPTIONS.get(module, "Waybar module"))
        self.set_hexpand(True)
        self.set_vexpand(False)
        self.set_size_request(-1, 32)

        handle = Gtk.Label(label="⠿")
        handle.add_css_class("module-handle")
        handle.set_tooltip_text("Drag to reorder this module.")
        self.append(handle)

        drag = Gtk.DragSource()
        drag.set_actions(Gdk.DragAction.MOVE)
        drag.connect("prepare", self._prepare_drag)
        handle.add_controller(drag)

        name = Gtk.Label(label=owner.FRIENDLY.get(module, module), xalign=0)
        name.add_css_class("module-name")
        name.set_ellipsize(Pango.EllipsizeMode.END)
        name.set_hexpand(True)
        self.append(name)

        # Keep the state control visually independent from the module text.
        # The module name expands, pushing one consistently tiny switch to the
        # absolute right edge of every row. Preview text remains available in
        # the tooltip instead of competing for horizontal space.
        name.set_tooltip_text(owner.preview_text(module))

        self.enabled = ModuleSwitch(lane != "Disabled")
        self.enabled.set_tooltip_text("Enable or disable this Waybar module.")
        self.enabled.connect("notify::active", self._set_enabled)
        self.append(self.enabled)

        drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop.connect("drop", self._drop_before)
        self.add_controller(drop)

    def _prepare_drag(self, *_args):
        return Gdk.ContentProvider.new_for_value(self.module)

    def _drop_before(self, _target, value, _x, _y):
        source = str(value)
        if not source or source == self.module:
            return False
        self.owner.move_module(source, self.lane, before=self.module)
        return True

    def _set_enabled(self, button, _pspec=None):
        enabled = button.get_active()
        if enabled and self.lane == "Disabled":
            destination = self.owner.last_active_lane.get(self.module, "Right")
            GLib.idle_add(self.owner.move_module, self.module, destination)
        elif not enabled and self.lane != "Disabled":
            self.owner.last_active_lane[self.module] = self.lane
            GLib.idle_add(self.owner.move_module, self.module, "Disabled")


class ModuleLane(Gtk.Box):
    def __init__(self, owner, lane_name: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        self.owner = owner
        self.lane_name = lane_name
        self.add_css_class("module-lane")
        self.add_css_class(f"module-lane-{lane_name.lower()}")
        self.set_hexpand(True)
        self.set_vexpand(False)

        title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title.add_css_class("module-lane-header")

        label = Gtk.Label(label=lane_name.upper(), xalign=0)
        label.add_css_class("module-lane-title")
        label.set_hexpand(True)
        title.append(label)

        self.count = Gtk.Label(label="0")
        self.count.add_css_class("module-lane-count")
        title.append(self.count)
        self.append(title)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.body.set_hexpand(True)
        self.body.set_vexpand(False)
        self.append(self.body)

        drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop.connect("drop", self._drop_append)
        self.add_controller(drop)

    def _drop_append(self, _target, value, _x, _y):
        source = str(value)
        if not source:
            return False
        self.owner.move_module(source, self.lane_name)
        return True

    def rebuild(self, modules):
        child = self.body.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.body.remove(child)
            child = next_child

        for module in modules:
            self.body.append(ModuleChip(self.owner, module, self.lane_name))

        self.count.set_text(str(len(modules)))

        if not modules:
            empty = Gtk.Label(label="Drop modules here")
            empty.add_css_class("module-empty")
            empty.set_halign(Gtk.Align.START)
            empty.set_valign(Gtk.Align.CENTER)
            self.body.append(empty)


class WaybarPage(Page):
    FRIENDLY = {
        "custom/launcher": "Launcher",
        "hyprland/workspaces": "Workspaces",
        "hyprland/window": "Active Window",
        "mpris": "Media",
        "pulseaudio": "Audio",
        "memory": "Memory",
        "cpu": "CPU",
        "custom/cpu_temp": "CPU Temperature",
        "custom/gpu_temp": "GPU Temperature",
        "custom/governor": "CPU Governor",
        "tray": "System Tray",
        "clock": "Date",
        "clock#simpleclock": "Time",
        "custom/power": "Power",
    }

    SHORT = {
        "custom/launcher": "薬",
        "hyprland/workspaces": "WS",
        "hyprland/window": "WIN",
        "mpris": "MUSIC",
        "pulseaudio": "VOL",
        "memory": "MEM",
        "cpu": "CPU",
        "custom/cpu_temp": "CPU°C",
        "custom/gpu_temp": "GPU°C",
        "custom/governor": "GOV",
        "tray": "TRAY",
        "clock": "DATE",
        "clock#simpleclock": "TIME",
        "custom/power": "⏻",
    }

    DESCRIPTIONS = {
        "custom/launcher": "Left click opens Yakushi Control Deck. Right click keeps the application launcher.",
        "hyprland/workspaces": "Shows and switches workspaces.",
        "hyprland/window": "Displays the active window title.",
        "mpris": "Shows media playback information.",
        "pulseaudio": "Volume indicator and click target for audio settings.",
        "memory": "Current RAM usage.",
        "cpu": "Current CPU load.",
        "custom/cpu_temp": "CPU temperature sensor output.",
        "custom/gpu_temp": "GPU temperature sensor output.",
        "custom/governor": "CPU governor indicator and switch action.",
        "tray": "System tray area for background applications.",
        "clock": "Date and calendar popover.",
        "clock#simpleclock": "Simple time display.",
        "custom/power": "Launches your power menu.",
    }

    def __init__(self):
        super().__init__()

        self.append(page_header(
            "02",
            "Desktop",
            "Bar Studio",
            "Apply Liquid Glass, then drag modules where you want them or drop them into Disabled to hide them."
        ))

        current = waybar_load()
        self.current = current

        preview_card = card(
            "// LIVE PREVIEW",
            "A miniature waybar layout so you can see what LEFT, CENTER, and RIGHT currently mean."
        )
        self.preview = WaybarMiniPreview(self)
        preview_card.append(self.preview)
        self.append(preview_card)

        presets = card(
            "// BAR PRESETS",
            "Apply the same Raycast-like material language to Waybar while keeping your module order and click actions intact."
        )
        liquid_button = Gtk.Button()
        liquid_button.add_css_class("preset-card")
        liquid_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        liquid_title = Gtk.Label(label="01  LIQUID GLASS", xalign=0)
        liquid_title.add_css_class("preset-title")
        liquid_content.append(liquid_title)
        liquid_description = Gtk.Label(
            label="Translucent gradient pills, fine highlights, restrained shadows and compositor blur.",
            xalign=0,
        )
        liquid_description.set_wrap(True)
        liquid_description.add_css_class("muted")
        liquid_content.append(liquid_description)
        liquid_button.set_child(liquid_content)
        liquid_button.connect("clicked", self.apply_liquid_glass)
        presets.append(liquid_button)
        self.append(presets)

        look = card(
            "// BAR SETTINGS",
            "Compact geometry controls. Changes are applied together with the module layout."
        )

        self.height = spin(current.height, 24, 60)
        self.margin_top = spin(current.margin_top, 0, 30)
        self.margin_side = spin(current.margin_left, 0, 40)
        self.spacing = spin(current.spacing, 0, 14)
        self.font_size = spin(current.font_size, 9, 20)
        self.radius = spin(current.radius, 0, 24)
        self.padding = spin(current.padding, 2, 24)
        self.opacity = slider(current.opacity, 0.15, 1.0, 0.01)

        settings_grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        settings_grid.set_column_homogeneous(True)
        geometry_rows = [
            ("Bar height", self.height),
            ("Top margin", self.margin_top),
            ("Side margins", self.margin_side),
            ("Module spacing", self.spacing),
            ("Font size", self.font_size),
            ("Module roundness", self.radius),
            ("Module padding", self.padding),
            ("Module opacity", self.opacity),
        ]
        for index, (label, widget) in enumerate(geometry_rows):
            row = setting_row(label, widget)
            row.add_css_class("bar-setting-compact")
            settings_grid.attach(row, index % 2, index // 2, 1, 1)
        look.append(settings_grid)
        self.append(look)

        modules_card = card(
            "// MODULES",
            "LEFT, CENTER, and RIGHT are kept as three obvious lanes. Grey means disabled; Yakushi red means enabled. Drag the handle to reorder or move modules between lanes."
        )

        self.module_state = {
            "Left": list(current.left),
            "Center": list(current.center),
            "Right": list(current.right),
            "Disabled": [],
        }
        self.last_active_lane = {}

        lanes_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        lanes_grid.set_column_homogeneous(True)
        lanes_grid.set_hexpand(True)
        self.lanes = {}

        for column, lane_name in enumerate(("Left", "Center", "Right")):
            lane = ModuleLane(self, lane_name)
            lanes_grid.attach(lane, column, 0, 1, 1)
            self.lanes[lane_name] = lane

        disabled = ModuleLane(self, "Disabled")
        disabled.add_css_class("module-lane-disabled-wide")
        lanes_grid.attach(disabled, 0, 1, 3, 1)
        self.lanes["Disabled"] = disabled

        modules_card.append(lanes_grid)
        self.append(modules_card)

        self.status = Gtk.Label(xalign=0)
        self.status.add_css_class("status")

        self.append(
            action_button(
                "APPLY WAYBAR SETTINGS",
                self.apply,
                primary=True,
            )
        )
        self.append(self.status)

        self.rebuild_lanes()

    def short_label(self, module: str) -> str:
        return self.SHORT.get(module, self.FRIENDLY.get(module, module))

    def preview_text(self, module: str) -> str:
        return WaybarMiniPreview.SAMPLE.get(module, self.short_label(module))

    def rebuild_lanes(self):
        for lane_name, lane in self.lanes.items():
            lane.rebuild(self.module_state[lane_name])
        self.preview.rebuild()

    def move_module(self, module: str, destination: str, before: str | None = None):
        for lane_name, modules in self.module_state.items():
            if module in modules:
                modules.remove(module)
                break

        if destination not in self.module_state:
            return

        if destination != "Disabled":
            self.last_active_lane[module] = destination

        target = self.module_state[destination]

        if before and before in target:
            target.insert(target.index(before), module)
        else:
            target.append(module)

        self.rebuild_lanes()

    def apply(self, *_):
        value = WaybarState(
            height=int(self.height.get_value()),
            margin_top=int(self.margin_top.get_value()),
            margin_left=int(self.margin_side.get_value()),
            margin_right=int(self.margin_side.get_value()),
            spacing=int(self.spacing.get_value()),
            font_size=int(self.font_size.get_value()),
            radius=int(self.radius.get_value()),
            padding=int(self.padding.get_value()),
            opacity=round(self.opacity.scale.get_value(), 2),
            left=list(self.module_state["Left"]),
            center=list(self.module_state["Center"]),
            right=list(self.module_state["Right"]),
        )

        _, message = waybar_save(value)
        self.status.set_text(message)

    def apply_liquid_glass(self, *_):
        ok, message = waybar_apply_preset("liquid_glass")
        if not ok:
            self.status.set_text("ERROR: " + message)
            return

        current = waybar_load()
        self.current = current
        self.height.set_value(current.height)
        self.margin_top.set_value(current.margin_top)
        self.margin_side.set_value(current.margin_left)
        self.spacing.set_value(current.spacing)
        self.font_size.set_value(current.font_size)
        self.radius.set_value(current.radius)
        self.padding.set_value(current.padding)
        self.opacity.scale.set_value(current.opacity)
        self.status.set_text(message)
