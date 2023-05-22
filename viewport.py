import imgui
import math
from vector import *
from util import *
from project import *


class Viewport:
    MIN_ZOOM = 4
    MAX_ZOOM = 10
    ZOOM_STEP = 0.2
    IMGUI_WHITE: int = 0xffffffff

    def __init__(self) -> None:
        self.show_grid: bool = True
        self.show_axes: bool = True

        # Viewport width and height in pixels
        self.width: int = 100
        self.height: int = 100
        self.ui_scale: float = 1.0

        # Viewport zoom level and pan
        self.zoom: float = 7.0
        self.meters_per_pixel: float = 0.0
        self.pixels_per_meter: float = 0.0

        # Offset of the center of the viewport (in meters)
        self.offset: Vec2 = Vec2()

        # Viewport visible area rect (in meters)
        self.rect: Rect = Rect()

        self.to_screen_matrix: Matrix3x3 = Matrix3x3()
        self.from_screen_matrix: Matrix3x3 = Matrix3x3()

        # EditableShapes to be drawn
        self.shapes_to_draw: list = []

    def _meters_per_pixel(self, zoom: float) -> float:
        m_per_pix = math.pow(10, -zoom)
        m_per_pix /= self.ui_scale
        return m_per_pix

    def _recompute_matrices(self) -> None:
        m_per_pix: float = self._meters_per_pixel(self.zoom)
        pix_per_m: float = 1.0 / m_per_pix

        trans: Vec2 = Vec2(-self.offset) * pix_per_m
        trans += Vec2(self.width, self.height) * 0.5

        mat = Matrix3x3()
        mat.set_scale(pix_per_m, pix_per_m)
        mat.set_translation(trans.x, trans.y)
        self.to_screen_matrix = mat

    def _change_zoom(self, new_zoom: float, anchor: Vec2 = None):
        prev_zoom = self.zoom

        if new_zoom > self.MAX_ZOOM:
            new_zoom = self.MAX_ZOOM
        if new_zoom < self.MIN_ZOOM:
            new_zoom = self.MIN_ZOOM

        if anchor is not None:
            anchor = self.from_screen(anchor)
            adiff = anchor - self.offset

            prev = self._meters_per_pixel(prev_zoom)
            curr = self._meters_per_pixel(new_zoom)

            adiff = adiff * (curr / prev)
            self.offset = anchor - adiff

        self.zoom = new_zoom

    def zoom_in(self, steps: int = 1, anchor: Vec2 = None):
        new_zoom = self.zoom + steps * self.ZOOM_STEP
        self._change_zoom(new_zoom, anchor)

    def zoom_out(self, steps: int = 1, anchor: Vec2 = None):
        new_zoom = self.zoom - steps * self.ZOOM_STEP
        self._change_zoom(new_zoom, anchor)

    def translate_pixels(self, offset: Vec2) -> None:
        offset.y = -offset.y
        self.offset -= offset * self.meters_per_pixel

    # Transforms a global coordinate (in meters) to screen space (in pixels)
    def to_screen(self, coord: Vec2) -> Vec2:
        c = Vec2(coord)
        c -= Vec2(self.rect.left, self.rect.bottom)
        c *= self.pixels_per_meter
        c.y = self.height - c.y  # Viewport renders with flipped Y
        return c.round()

    # Transforms a screen coordinate (in pixels) to global space (in meters)
    def from_screen(self, coord: Vec2) -> Vec2:
        c = Vec2(coord)
        c.y = self.height - c.y  # Undo viewport flipped Y
        c *= self.meters_per_pixel
        c += Vec2(self.rect.left, self.rect.bottom)
        return c

    def update(self) -> None:
        main_viewport = imgui.get_main_viewport()
        io = imgui.get_io()

        self.width = main_viewport.size[0]
        self.height = main_viewport.size[1]

        self.meters_per_pixel = self._meters_per_pixel(self.zoom)
        self.pixels_per_meter = 1.0 / self.meters_per_pixel

        viewport_dims: Vec2 = Vec2(self.width, self.height)
        viewport_dims *= self.meters_per_pixel

        self.rect.center = self.offset
        self.rect.width = viewport_dims.x
        self.rect.height = viewport_dims.y

        self._recompute_matrices()

    def draw(self) -> None:
        dl = imgui.get_background_draw_list()

        if self.show_grid:
            self._draw_grid()
        if self.show_axes:
            self._draw_axes()

        for s in self.shapes_to_draw:
            s.draw(self)

        self._draw_scale()

    # Draw a line defined in global coordinate space (in meters)
    def draw_line(self, start: Vec2, end: Vec2, color: int = IMGUI_WHITE,
                  thickness: float = 1.0):
        dl = imgui.get_background_draw_list()

        # TODO: are there clipping issues for big shapes?
        start = self.to_screen(start)
        end = self.to_screen(end)

        dl.add_line(start.x, start.y, end.x, end.y, color, thickness)

    # Draw a circle defined in global coordinate space (in meters)
    def draw_circle(self, center: Vec2, radius: float, color: int = IMGUI_WHITE,
                    filled: bool = False, thickness: float = 1.0):
        dl = imgui.get_background_draw_list()

        # TODO: are there clipping issues for big shapes?
        center = self.to_screen(center)
        radius *= self.pixels_per_meter

        # TODO: derive segments in some smarter way, maybe?
        segments: int = clamp(round(radius * 2), 8, 512)

        if filled:
            dl.add_circle_filled(center.x, center.y, radius, color, segments)
        else:
            dl.add_circle(center.x, center.y, radius, color, segments, thickness)

    # Draw a quad defined in global coordinate space (in meters)
    def draw_quad(self, points: list[Vec2], color: int = IMGUI_WHITE,
                  filled: bool = False, thickness: float = 1.0):
        dl = imgui.get_background_draw_list()

        # TODO: are there clipping issues for big shapes?
        p = [self.to_screen(points[i]) for i in range(4)]

        if filled:
            dl.add_quad_filled(p[0].x, p[0].y, p[1].x, p[1].y,
                               p[2].x, p[2].y, p[3].x, p[3].y, color)
        else:
            dl.add_quad(p[0].x, p[0].y, p[1].x, p[1].y,
                        p[2].x, p[2].y, p[3].x, p[3].y, color, thickness)

    def _draw_grid(self) -> None:
        color_minor = imgui.get_color_u32_rgba(0.1, 0.1, 0.1, 1)
        color_major = imgui.get_color_u32_rgba(0.2, 0.2, 0.2, 1)

        min_grid_pixels = 6
        minor_scale = min_grid_pixels * self.meters_per_pixel
        minor_scale = larger_pow(minor_scale, 10)
        major_scale = minor_scale * 10

        # Vertical minor gridlines
        x = round_to_next(self.rect.left, minor_scale)
        while x < self.rect.right:
            self.draw_line(Vec2(x, self.rect.top), Vec2(x, self.rect.bottom),
                            color_minor)
            x += minor_scale

        # Horizontal minor gridlines
        y = round_to_next(self.rect.bottom, minor_scale)
        while y < self.rect.top:
            self.draw_line(Vec2(self.rect.left, y), Vec2(self.rect.right, y),
                            color_minor)
            y += minor_scale

        # Vertical major gridlines
        x = round_to_next(self.rect.left, major_scale)
        while x < self.rect.right:
            self.draw_line(Vec2(x, self.rect.top), Vec2(x, self.rect.bottom),
                            color_major)
            x += major_scale

        # Horizontal major gridlines
        y = round_to_next(self.rect.bottom, major_scale)
        while y < self.rect.top:
            self.draw_line(Vec2(self.rect.left, y), Vec2(self.rect.right, y),
                            color_major)
            y += major_scale

    def _draw_axes(self) -> None:
        color_axes = imgui.get_color_u32_rgba(0.25, 0.25, 0.25, 1)
        thickness = 3.0

        # X-axis of the coordinate system
        if self.rect.bottom <= 0 and self.rect.top >= 0:
            self.draw_line(Vec2(self.rect.left, 0), Vec2(self.rect.right, 0),
                            color_axes, thickness)

        # Y-axis of the coordinate system
        if self.rect.left <= 0 and self.rect.right >= 0:
            self.draw_line(Vec2(0, self.rect.top), Vec2(0, self.rect.bottom),
                            color_axes, thickness)

    def _draw_scale(self) -> None:
        dl = imgui.get_background_draw_list()
        color = imgui.get_color_u32_rgba(1,1,1,1)

        width = 130 * self.ui_scale
        s = smaller_pow(width * self.meters_per_pixel, 10)
        for i in range(1, 6):
            w = (s * i * self.pixels_per_meter)
            if w < width:
                scale = s * i
            else:
                break
        width = scale * self.pixels_per_meter

        bottom = self.height - 20 * self.ui_scale
        left = 20 * self.ui_scale
        top = bottom - 5 * self.ui_scale
        right = left + width

        thickness = 2.0 * self.ui_scale
        dl.add_line(left, bottom, left, top, color, thickness)
        dl.add_line(left, bottom, right, bottom, color, thickness)
        dl.add_line(right, bottom, right, top, color, thickness)

        text = meters_pretty(scale)
        text_left = right + 10 * self.ui_scale
        text_size = imgui.calc_text_size(text)
        text_top = bottom - text_size[1] + 4 * self.ui_scale
        dl.add_text(text_left, text_top, color, text)