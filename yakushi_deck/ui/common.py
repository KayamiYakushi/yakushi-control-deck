from __future__ import annotations

from gi.repository import Gtk, Gdk, Gio


def install_css(css: str) -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    display = Gdk.Display.get_default()
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def spin(value, lower, upper, step=1, digits=0):
    return Gtk.SpinButton(
        adjustment=Gtk.Adjustment(
            value=value,
            lower=lower,
            upper=upper,
            step_increment=step,
            page_increment=max(step * 5, 1),
            page_size=0,
        ),
        digits=digits,
    )


def slider(value, lower, upper, step=0.01, digits=2):
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lower, upper, step)
    scale.set_value(value)
    scale.set_draw_value(False)
    scale.set_hexpand(True)

    value_label = Gtk.Label(label=f"{value:.{digits}f}")
    value_label.add_css_class("value-readout")
    value_label.set_width_chars(5)

    def changed(widget):
        value_label.set_text(f"{widget.get_value():.{digits}f}")

    scale.connect("value-changed", changed)

    box.append(scale)
    box.append(value_label)
    box.scale = scale
    return box


def page_header(index: str, section_name: str, title: str, subtitle: str) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)

    meta = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    dash = Gtk.Label(label="—")
    dash.add_css_class("meta")
    meta.append(dash)

    section = Gtk.Label(label=f"{index} // {section_name.upper()}")
    section.add_css_class("meta")
    meta.append(section)

    box.append(meta)

    heading = Gtk.Label(label=title, xalign=0)
    heading.add_css_class("page-title")
    box.append(heading)

    sub = Gtk.Label(label=subtitle, xalign=0)
    sub.set_wrap(True)
    sub.add_css_class("page-subtitle")
    box.append(sub)

    return box


def card(title: str, subtitle: str = "") -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.add_css_class("deck-card")

    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

    label = Gtk.Label(label=title, xalign=0)
    label.add_css_class("card-title")
    header.append(label)

    if subtitle:
        sub = Gtk.Label(label=subtitle, xalign=0)
        sub.set_wrap(True)
        sub.add_css_class("muted")
        header.append(sub)

    box.append(header)
    return box


def setting_row(label: str, widget: Gtk.Widget, description: str = "") -> Gtk.Box:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=22)
    row.add_css_class("setting-row")

    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    text.set_hexpand(True)

    title = Gtk.Label(label=label, xalign=0)
    title.add_css_class("setting-name")
    text.append(title)

    if description:
        sub = Gtk.Label(label=description, xalign=0)
        sub.set_wrap(True)
        sub.add_css_class("muted")
        text.append(sub)

    row.append(text)
    row.append(widget)
    return row


def action_button(label: str, callback, primary: bool = False) -> Gtk.Button:
    button = Gtk.Button(label=label)
    if primary:
        button.add_css_class("primary")
    button.connect("clicked", callback)
    return button


def open_uri(uri: str):
    try:
        Gio.AppInfo.launch_default_for_uri(uri, None)
    except Exception:
        pass


def open_folder(path):
    try:
        file = Gio.File.new_for_path(str(path))
        open_uri(file.get_uri())
    except Exception:
        pass
