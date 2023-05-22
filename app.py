import sys
import logging as log
import imgui
import glfw
import OpenGL.GL as gl
from imgui.integrations.glfw import GlfwRenderer
from collections.abc import Callable
from __version__ import __version__
from typing import NamedTuple
from pathlib import Path
from io import IOBase

import dialog
import project
import editor
import xmlproject
import cProfile


# Setup logging
log.basicConfig(filename='lyra-tool.log', filemode='w',
                format='%(asctime)s |%(levelname)s| (%(name)s) %(message)s',
                level=log.INFO)


class ModalEntry(NamedTuple):
    title: str
    description: str
    ok_callback: Callable[[], None]
    cancel_callback: Callable[[], None]


class Window:
    MIN_WIDTH: int = 800
    MIN_HEIGHT: int = 600

    def __init__(self) -> None:
        if not glfw.init():
            log.critical('failed to initialize GLFW')
            sys.exit(1)

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

        self.width: int = 1024
        self.height: int = 768
        self.window = glfw.create_window(self.width, self.height,
                                         'Lyra Tool', None, None)
        if not self.window:
            log.critical('failed to open window')
            glfw.terminate()
            sys.exit(1)

        glfw.make_context_current(self.window)
        glfw.swap_interval(1) # Enable vsync
        glfw.set_window_size_limits(self.window,
                                    self.MIN_WIDTH, self.MIN_HEIGHT,
                                    glfw.DONT_CARE, glfw.DONT_CARE)

        self.clear_color = (0.0, 0.0, 0.0, 1.0)
        self.impl = GlfwRenderer(self.window)
        self.content_scale: float = 1.0

    def update(self) -> None:
        glfw.poll_events()
        self.impl.process_inputs()

        xscale, yscale = glfw.get_window_content_scale(self.window)
        self.content_scale = max(xscale, yscale)

        self.width, self.height = glfw.get_window_size(self.window)

    def draw(self) -> None:
        gl.glClearColor(*self.clear_color)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        self.impl.render(imgui.get_draw_data())
        glfw.swap_buffers(self.window)

    def should_close(self) -> bool:
        return glfw.window_should_close(self.window)

    def close(self) -> None:
        glfw.set_window_should_close(self.window, True)

    def shutdown(self) -> None:
        self.impl.shutdown()
        glfw.terminate()


class LyraToolApp:
    def __init__(self) -> None:
        imgui.create_context()
        self.window = Window()
        self.io = imgui.get_io()
        self.font_size: int = 16
        self.font_mult: float = 2.0
        # Loading x2 font size to look good on Hi-DPI screens
        self.font = self.io.fonts.add_font_from_file_ttf(
            'Roboto.ttf', int(self.font_size * self.font_mult))
        self.window.impl.refresh_font_texture()
        self.editor = editor.Interface()
        self.file_new: bool = False
        self.file_open: bool = False
        self.file_save: bool = False
        self.file_quit: bool = False
        self.modal_queue: list[ModalEntry] = []
        self.modal_entry: ModalEntry = None

    def _open_file(self, file: IOBase) -> None:
        try:
            Project = xmlproject.from_file()
        except:
            log.exception('Unhandled exception when opening file:')

    def _file_menu(self) -> None:
        has_open_proj: bool = (self.editor.project is not None)

        file_new, _ = imgui.menu_item('New', None, False, True)
        file_open, _ = imgui.menu_item('Open', None, False, True)
        file_save, _ = imgui.menu_item('Save', None, False, has_open_proj)
        imgui.separator()
        file_quit, _ = imgui.menu_item('Quit', None, False, True)

        if file_new:
            if has_open_proj:
                self._enqueue_modal('New File?',
                                    ('Open a new empty project file?\n' +
                                    'Any unsaved changes will be lost!'),
                                    lambda: self._handle_file_new())
            else:
                self._handle_file_new()

        if file_open:
            if has_open_proj:
                self._enqueue_modal('Open File?',
                                    ('Load a new project file from disk?\n' +
                                    'Any unsaved changes will be lost!'),
                                    lambda: self._handle_file_open())
            else:
                self._handle_file_open()

        if file_save:
            self._handle_file_save()

        if file_quit:
            self._enqueue_modal('Quit?',
                                ('Are you sure you want to quit?\n' +
                                 'Any unsaved changes will be lost!'),
                                 lambda: self.window.close())

    def _enqueue_modal(self, title: str, desc: str,
                       ok_cb: Callable[[], None] = None,
                       cancel_cb: Callable[[], None] = None) -> None:
        item = ModalEntry(title, desc, ok_cb, cancel_cb)
        self.modal_queue.append(item)

    def _menu_bar(self) -> None:
        self.file_new = False
        self.file_open = False
        self.file_save = False
        self.file_quit = False

        with imgui.begin_main_menu_bar() as bar:
            if bar.opened:
                with imgui.begin_menu('File', True) as menu:
                    if menu.opened:
                        self._file_menu()
                self.editor.update_menu_bar()

    def _handle_file_new(self) -> None:
        log.info('Initializing new default project')
        new_proj = project.new_project()
        self.editor.set_project(new_proj)

    def _handle_file_open(self) -> None:
        file = dialog.file_open()
        if file is None:
            log.info('None file returned from file open dialog, will ignore')
        else:
            log.info(f'Loading using xmlproject reader from file: {file.name}')
            try:
                proj = xmlproject.from_file(file)
                self.editor.set_project(proj)
                file.close()
            except:
                log.exception('Exception occurred during file parse:')
                self._enqueue_modal('Error!',
                                ('Exception occurred during file load!\n' +
                                 'Check the log file for more info.'))

    def _handle_file_save(self) -> None:
        file = dialog.file_save()
        if file is None:
            log.info('None file returned from file save dialog, will ignore')
        else:
            log.info(f'Saving using xmlproject writer to file: {file.name}')
            try:
                xmlproject.to_file(self.editor.project, file)
                file.close()
            except:
                log.exception('Exception occurred during file save:')
                self._enqueue_modal('Error!',
                                ('Exception occurred during file save!\n' +
                                 'Check the log file for more info.'))

    def _handle_modal(self) -> None:
        if self.modal_entry is None:
            if len(self.modal_queue) > 0:
                self.modal_entry = self.modal_queue.pop(0)
                imgui.open_popup(self.modal_entry.title)
            else:
                return

        flags = imgui.WINDOW_ALWAYS_AUTO_RESIZE | imgui.WINDOW_NO_SAVED_SETTINGS

        with imgui.begin_popup_modal(self.modal_entry.title, flags=flags) as modal:
            if modal.opened:
                imgui.text(self.modal_entry.description)
                ok: bool = imgui.button('Ok', 100)
                imgui.same_line()
                cancel: bool = imgui.button('Cancel', 100)

                if ok or cancel:
                    if ok and self.modal_entry.ok_callback:
                        self.modal_entry.ok_callback()
                    if cancel and self.modal_entry.cancel_callback:
                        self.modal_entry.cancel_callback()
                    imgui.close_current_popup()
                    self.modal_entry = None

    def update(self) -> None:
        self.window.update()
        ui_scale: float = self.window.content_scale
        # NOTE: Font is loaded with twice the size
        self.io.font_global_scale = ui_scale / self.font_mult

        imgui.new_frame()
        self.editor.set_ui_scale(ui_scale)
        self.editor.update_input()

        with imgui.font(self.font):
            self._menu_bar()
            self._handle_modal()
            self.editor.update_ui()

    def draw(self) -> None:
        imgui.render()
        self.window.draw()

    def should_close(self) -> bool:
        return self.window.should_close()

    def shutdown(self) -> None:
        self.window.shutdown()


def main():
    log.info('Initializing Lyra Tool, v' + __version__)
    app = LyraToolApp()

    log.info('Beginning main loop')
    while not app.should_close():
        app.update()
        app.draw()

    log.info('Shutting down')
    app.shutdown()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log.exception('Unhandled exception in main:')
