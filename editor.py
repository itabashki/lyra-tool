import imgui
import math
from vector import Vec2, Rect
from viewport import Viewport
from copy import deepcopy
from enum import IntEnum, auto
from util import *
from project import *


METER_SCALE_NAME = 'um'
METER_SCALE = 1e-6
METER_INV_SCALE = 1e6

SHAPE_NAMES = {
    'PointShape': 'Point',
    'CrossShape': 'Cross',
    'LineShape': 'Line',
    'RectangleShape': 'Rectangle',
    'FilledRectangleShape': 'Filled Rectangle',
    'CircleShape': 'Circle',
    'FilledCircleShape': 'Filled Circle',
    'AnnulusShape': 'Annulus',
}
SHAPE_TYPES = [k for k in SHAPE_NAMES]


class EditableShape:
    # Make clicking the shape easier by expanding the targeting area by a bit
    CLICK_BUMP: float = 4.0

    def __init__(self, name: str, shape: ShapeObject) -> None:
        self.name: str = name
        self.shape: ShapeObject = shape
        self.selected: bool = False

    def _bg_color(self) -> int:
        alpha = 0.33
        if self.selected:
            return imgui.get_color_u32_rgba(1, 1, 0, alpha)
        else:
            return imgui.get_color_u32_rgba(1, 0, 0, alpha)

    def _fg_color(self) -> int:
        alpha = 1.0
        if self.selected:
            return imgui.get_color_u32_rgba(1, 1, 0, alpha)
        else:
            return imgui.get_color_u32_rgba(1, 0, 0, alpha)

    def _rotate_vec2(self, v: Vec2, angle: float) -> Vec2:
        sin_theta: float = math.sin(math.radians(angle))
        cos_theta: float = math.cos(math.radians(angle))
        x: float = v.x * cos_theta - v.y * sin_theta
        y: float = v.x * sin_theta + v.y * cos_theta
        return Vec2(x, y)

    def _annulus_intersect(self, p: Vec2, center: Vec2,
                           radius: float, inner_radius: float):
        dist: float = math.floor((p - center).length)
        if dist > radius:
            return False
        if dist < inner_radius:
            return False
        return True

    def _box_intersect(self, p: Vec2, center: Vec2, half_dims: Vec2,
                       angle: float, inner_half_dims: Vec2 = Vec2()) -> bool:
        v: Vec2 = self._rotate_vec2(p - center, angle) + center
        rect: Rect = Rect()
        rect.center = center
        rect.half_dims = half_dims

        if not rect.overlaps_point(v):
            return False
        if (inner_half_dims > 0.0).all():
            rect.half_dims = inner_half_dims
            if rect.overlaps_point(v):
                return False
        return True

    # Checks whether the given screen point intersects with shape
    def intersect_screen(self, view: Viewport, point: Vec2) -> bool:
        if isinstance(self.shape, (PointShape, CircleShape)):
            center: Vec2 = view.to_screen(self.shape.center)
            radius: float = 2.0  # Default for point shape
            inner_radius: float = 0.0

            if isinstance(self.shape, CrossShape):
                x: CrossShape = self.shape
                hw: float = x.width * view.pixels_per_meter * 0.5
                half_dims: Vec2 = Vec2(hw, self.CLICK_BUMP)
                if self._box_intersect(point, center, half_dims, 0):
                    return True
                half_dims = Vec2(self.CLICK_BUMP, hw)
                if self._box_intersect(point, center, half_dims, 0):
                    return True
            if isinstance(self.shape, CircleShape):
                c: CircleShape = self.shape
                radius = c.radius * view.pixels_per_meter
                inner_radius = radius
            if isinstance(self.shape, FilledCircleShape):
                inner_radius = 0.0
            if isinstance(self.shape, AnnulusShape):
                a: AnnulusShape = self.shape
                inner_radius = a.inner_radius * view.pixels_per_meter

            radius += self.CLICK_BUMP
            inner_radius -= self.CLICK_BUMP
            return self._annulus_intersect(point, center, radius, inner_radius)

        if isinstance(self.shape, LineShape):
            l: LineShape = self.shape
            d: Vec2 = (l.end - l.begin)

            center: Vec2 = view.to_screen(l.begin + d * 0.5)
            angle: float = -math.degrees(d.atan2())
            half_dims: Vec2 = Vec2(0, l.length) * view.pixels_per_meter
            half_dims += self.CLICK_BUMP * 2.0
            return self._box_intersect(point, center, half_dims, angle)

        if isinstance(self.shape, RectangleShape):
            r: RectangleShape = self.shape
            center: Vec2 = view.to_screen(r.center)
            half_dims: Vec2 = r.dimensions * 0.5 * view.pixels_per_meter
            inner_half_dims: Vec2 = Vec2(half_dims)
            angle: float = r.angle

            if isinstance(self.shape, FilledRectangleShape):
                inner_half_dims = Vec2()

            half_dims += self.CLICK_BUMP
            inner_half_dims -= self.CLICK_BUMP
            return self._box_intersect(point, center, half_dims,
                                       angle, inner_half_dims)
        return False

    def translate_screen(self, view: Viewport, diff: Vec2):
        diff = Vec2(diff.x, -diff.y) * view.meters_per_pixel

        if isinstance(self.shape, (PointShape, CircleShape, RectangleShape)):
            self.shape.center += diff

        if isinstance(self.shape, LineShape):
            l: LineShape = self.shape
            l.begin += diff
            l.end += diff

    def _inspect_vec2(self, shape: ShapeObject, prop: str, meters: bool = True):
        value: Vec2 = getattr(shape, prop)
        if not isinstance(value, Vec2):
            raise TypeError(f'Inspected attribute {prop} was not a Vec2, was: {type(value)}')
        x, y = value.x, value.y
        id: str = prop
        if meters:
            x *= METER_INV_SCALE
            y *= METER_INV_SCALE
            id = METER_SCALE_NAME + '##' + id
        changed, (x, y) = imgui.input_float2(id, x, y, format='%.5f')
        if changed:
            # TODO: undo stack
            if meters:
                x *= METER_SCALE
                y *= METER_SCALE
            setattr(shape, prop, Vec2(x, y))

    def _inspect_float(self, shape: ShapeObject, prop: str, meters: bool = True):
        value: float = getattr(shape, prop)
        if not isinstance(value, float):
            raise TypeError(f'Inspected attribute {prop} was not a float, was: {type(value)}')
        id: str = prop
        if meters:
            value *= METER_INV_SCALE
            id = METER_SCALE_NAME + '##' + id
        changed, value = imgui.input_float(id, value, format='%.5f')
        if changed:
            # TODO: undo stack
            if meters:
                value *= METER_SCALE
            setattr(shape, prop, value)

    def ui_inspect(self) -> None:
        if isinstance(self.shape, (PointShape, CircleShape, RectangleShape)):
            imgui.text('Center:')
            imgui.same_line()
            self._inspect_vec2(self.shape, 'center')

        if isinstance(self.shape, CrossShape):
            x: CrossShape = self.shape
            imgui.text('Width:')
            imgui.same_line()
            self._inspect_float(x, 'width')

        if isinstance(self.shape, LineShape):
            l: LineShape = self.shape

            imgui.text('Begin:')
            imgui.same_line()
            self._inspect_vec2(l, 'begin')

            imgui.text('End:')
            imgui.same_line()
            self._inspect_vec2(l, 'end')

        if isinstance(self.shape, CircleShape):
            c: CircleShape = self.shape
            imgui.text('Radius:')
            imgui.same_line()
            self._inspect_float(c, 'radius')

        if isinstance(self.shape, AnnulusShape):
            a: AnnulusShape = self.shape
            imgui.text('Inner Radius:')
            imgui.same_line()
            self._inspect_float(a, 'inner_radius')

        if isinstance(self.shape, RectangleShape):
            r: RectangleShape = self.shape

            imgui.text('Dims:')
            imgui.same_line()
            self._inspect_vec2(r, 'dimensions')

            imgui.text('Angle:')
            imgui.same_line()
            angle: float = r.angle
            changed, angle = imgui.slider_float('degrees ##angle', angle, -360, 360,
                                                format='%.01f')
            if changed:
                # TODO: undo stack
                r.angle = angle

        if isinstance(self.shape, ShapeObject):
            imgui.text('Depth:')
            imgui.same_line()
            depth: int = self.shape.depth
            changed, depth = imgui.slider_int('scans ##depth', depth, 1, 20)
            if changed:
                # TODO: undo stack
                self.shape.depth = depth

    def draw(self, view: Viewport) -> None:
        typ = type(self.shape)
        bg_color: int = self._bg_color()
        fg_color: int = self._fg_color()
        thickness = 2.0

        if isinstance(self.shape, PointShape):
            p: PointShape = self.shape
            radius = 4.0 * view.meters_per_pixel
            view.draw_circle(p.center, radius, fg_color, True)
        if isinstance(self.shape, CrossShape):
            x: CrossShape = self.shape
            half_width = x.width * 0.5
            view.draw_line(x.center - Vec2(half_width, 0),
                            x.center + Vec2(half_width, 0),
                            fg_color, thickness)
            view.draw_line(x.center - Vec2(0, half_width),
                            x.center + Vec2(0, half_width),
                            fg_color, thickness)
        if isinstance(self.shape, LineShape):
            l: LineShape = self.shape
            view.draw_line(l.begin, l.end, fg_color, thickness + 2.0)
        if isinstance(self.shape, CircleShape):
            c: CircleShape = self.shape
            is_filled: bool = isinstance(self.shape, FilledCircleShape)
            is_donut: bool = isinstance(self.shape, AnnulusShape)

            if is_filled and not is_donut:
                view.draw_circle(c.center, c.radius, bg_color, True)
            if is_donut:
                a: AnnulusShape = self.shape

                # TODO: avoid kinda weird hack to draw background
                r_diff = a.radius - a.inner_radius
                mid_r = a.inner_radius + r_diff * 0.5
                t = r_diff * view.pixels_per_meter
                view.draw_circle(c.center, mid_r, bg_color, False, t)

                view.draw_circle(c.center, a.inner_radius, fg_color, False,
                                     thickness)
            view.draw_circle(c.center, c.radius, fg_color, False,
                                 thickness)
        if isinstance(self.shape, RectangleShape):
            r: RectangleShape = self.shape
            is_filled: bool = isinstance(self.shape, FilledRectangleShape)

            half_dims: Vec2 = r.dimensions * 0.5
            angle: float = r.angle

            right: Vec2 = self._rotate_vec2(Vec2(half_dims.x, 0), angle)
            up: Vec2 = self._rotate_vec2(Vec2(0, half_dims.y), angle)

            points = [
                r.center - up - right,
                r.center + up - right,
                r.center + up + right,
                r.center - up + right,
            ]
            if is_filled:
                view.draw_quad(points, bg_color, True)
            view.draw_quad(points, fg_color, False, thickness)


class Interface:
    def __init__(self) -> None:
        self.frame_number: int = 0
        self.show_settings: bool = True
        self.show_inspector: bool = True
        self.show_grid: bool = True
        self.viewport: Viewport = Viewport()
        self.project: Project = None
        self.shapes: list[EditableShape] = []
        self.selected: set[EditableShape] = set()
        self.is_dragging: bool = False
        self.is_dragging_selection: bool = False
        self.was_dragging: bool = False
        self.add_shape_type: int = 0

    def _unselect_shape(self, shape: EditableShape) -> None:
        shape.selected = False
        if shape in self.selected:
            self.selected.remove(shape)

    def _unselect_all(self) -> None:
        for shape in self.selected:
            shape.selected = False
        self.selected.clear()

    def _select_shape(self, shape: EditableShape, add: bool = False):
        if not add:
            self._unselect_all()
        if shape is not None:
            self.selected.add(shape)
            shape.selected = True

    def _add_shape(self, shape: ShapeObject) -> EditableShape:
        # TODO: undo stack
        name = self.project.add_new_shape(shape)
        editable = EditableShape(name, shape)
        self.shapes.append(editable)
        return editable

    def _move_shape(self, from_index: int, to_index: int) -> None:
        # TODO: undo stack
        shape = self.shapes.pop(from_index)
        self.shapes.insert(to_index, shape)

    def _remove_shape(self, index: int) -> None:
        # TODO: undo stack
        shape = self.shapes.pop(index)
        if shape in self.selected:
            self.selected.remove(shape)
        self.project.remove_shape(shape.name)

    def _duplicate_shape(self, index: int) -> EditableShape:
        shape: ShapeObject = self.shapes[index].shape
        dupe: ShapeObject = deepcopy(shape)

        editable: EditableShape = self._add_shape(dupe)
        self._select_shape(editable, True)

    def _ui_inspector(self) -> None:
        flags = imgui.TREE_NODE_DEFAULT_OPEN
        for s in self.selected:
            s: EditableShape = s
            name: str = s.name
            if imgui.tree_node(name, flags):
                s.ui_inspect()
                imgui.tree_pop()
            imgui.separator()

    def _create_new_shape(self) -> None:
        shape: ShapeObject = None
        typename: str = SHAPE_TYPES[self.add_shape_type]
        typ: type = SHAPE_TYPENAME_TO_TYPE[typename]
        shape = typ()

        if isinstance(shape, CrossShape):
            x: CrossShape = shape
            x.width = 1e-5

        if isinstance(shape, CircleShape):
            c: CircleShape = shape
            c.radius = 1e-5

        if isinstance(shape, AnnulusShape):
            a: AnnulusShape = shape
            a.inner_radius = 5e-6

        if isinstance(shape, RectangleShape):
            r: RectangleShape = shape
            r.dimensions = Vec2(1e-5)

        if isinstance(shape, LineShape):
            l: LineShape = shape
            l.begin = Vec2(-1e-5)
            l.end = Vec2(1e-5)

        for s in list(self.selected):
            self._unselect_shape(s)

        editable = self._add_shape(shape)
        self._select_shape(editable)

    def _ui_add_shape(self):
        if imgui.button('Add'):
            self._create_new_shape()
        imgui.same_line()

        typename: str = SHAPE_TYPES[self.add_shape_type]
        with imgui.begin_combo("##shape", SHAPE_NAMES[typename]) as combo:
            if combo.opened:
                for i, typ in enumerate(SHAPE_TYPES):
                    is_selected = (i == self.add_shape_type)
                    name = SHAPE_NAMES[typ]
                    if imgui.selectable(name, is_selected)[0]:
                        self.add_shape_type = i
                    # Set the initial focus when opening the combo
                    if is_selected:
                        imgui.set_item_default_focus()

    def _ui_project(self):
        ps: ProjectSettings = self.project.settings
        flags = imgui.TREE_NODE_DEFAULT_OPEN

        def _prop_locked(name: str, value: str) -> None:
            imgui.text(f'{name}:')
            imgui.same_line()
            imgui.text_disabled(value)

        if imgui.tree_node('Material', flags):
            _prop_locked('Process', f'{ps.process}')
            _prop_locked('Profile', f'{ps.material_name}')
            _prop_locked('Energy', f'{ps.energy*1e-3:.3f} kV')
            _prop_locked('Dwell', f'{ps.dwell_time*1e6:.3f} us')
            _prop_locked('Overlap', f'{ps.overlap:.1f}')

            imgui.text('Dose:')
            imgui.same_line()
            imgui.push_item_width(-100)
            dose: float = ps.dose * 1e2
            changed, dose = imgui.input_float('uC/cm^2 ##dose', dose)
            if changed:
                # TODO: undo stack
                ps.dose = dose * 1e-2
            imgui.pop_item_width()
            imgui.tree_pop()

        if imgui.tree_node('Settings', flags):
            _prop_locked('Beam Current', f'{ps.beam_current*1e12:.3f} pA')
            _prop_locked('Spot Size', f'{ps.spot_size*1e9:.3f} nm')
            imgui.text(f'Beam Order:')
            if imgui.radio_button('Parallel', ps.parallel):
                # TODO: undo stack
                ps.parallel = True
            imgui.same_line()
            if imgui.radio_button('Serial', not ps.parallel):
                # TODO: undo stack
                ps.parallel = False
            imgui.tree_pop()

        _, avail_h = imgui.get_content_region_available()
        if avail_h < 200:
            avail_h = 200
        else:
            avail_h = 0

        io = imgui.get_io()
        modifier: bool = (io.key_shift or io.key_ctrl)

        remove_indices = []
        duplicate_indices = []

        if imgui.tree_node('Object List', flags):
            imgui.same_line()
            imgui.text_disabled('(?)')
            if imgui.is_item_hovered() and imgui.begin_tooltip():
                imgui.text_unformatted((
                    'Click objects in the list to select in the viewport,\n' +
                    'Shift-click or Ctrl-click to select multiple objects.\n' +
                    'Drag and drop objects to re-order them in the list.'
                ))
                imgui.end_tooltip()

            self._ui_add_shape()

            imgui.push_style_var(imgui.STYLE_CHILD_ROUNDING, 4.0)

            with imgui.begin_child('Objects', 0, avail_h, border=True):
                for i in range(len(self.shapes)):
                    shape: EditableShape = self.shapes[i]
                    select, _ = imgui.selectable(shape.name, shape.selected)
                    if select:
                        if shape.selected and modifier:
                            self._unselect_shape(shape)
                        else:
                            self._select_shape(shape, modifier)
                    with imgui.begin_popup_context_item() as popup:
                        if popup.opened:
                            selected = set(self.selected)
                            if shape not in selected:
                                imgui.text_disabled(shape.name)
                                imgui.separator()
                            for s in selected:
                                imgui.text_disabled(s.name)
                            selected.add(shape)
                            if imgui.button('Remove Shape(s)'):
                                for j in range(len(self.shapes)):
                                    if self.shapes[j] in selected:
                                        remove_indices.append(j)
                            if imgui.button('Duplicate Shape(s)'):
                                for j in range(len(self.shapes)):
                                    if self.shapes[j] in selected:
                                        duplicate_indices.append(j)
                    with imgui.begin_drag_drop_source() as src:
                        if src.dragging:
                            imgui.set_drag_drop_payload('shape', i.to_bytes(4))
                            imgui.text(shape.name)
                    with imgui.begin_drag_drop_target() as dest:
                        if dest.hovered:
                            payload = imgui.accept_drag_drop_payload('shape')
                            if payload is not None:
                                j = int.from_bytes(payload)
                                self._move_shape(j, i)

            imgui.pop_style_var()
            imgui.tree_pop()

        if len(duplicate_indices) > 0:
            self._unselect_all()
            for i in duplicate_indices:
                self._duplicate_shape(i)

        remove_indices.sort(reverse=True)
        for i in remove_indices:
            self._remove_shape(i)


    def set_ui_scale(self, ui_scale: float):
        self.viewport.ui_scale = ui_scale

    def update_input(self) -> None:
        self.frame_number += 1
        io = imgui.get_io()
        if io.want_capture_mouse:
            return  # Let imgui do its own thing

        mouse_pos = Vec2(*io.mouse_pos)
        mouse_delta = Vec2(*io.mouse_delta)
        ctrl: bool = io.key_ctrl
        shift: bool = io.key_shift

        if imgui.is_mouse_dragging(1):
            self.viewport.translate_pixels(mouse_delta)

        if imgui.is_mouse_dragging(0):
            self._handle_dragging(mouse_pos, mouse_delta)
        elif self.is_dragging:
            self.was_dragging = True
            self.is_dragging = False
            self.is_dragging_selection = False
        else:
            self.was_dragging = False

        if imgui.is_mouse_released(0):
            if not (self.is_dragging or self.was_dragging):
                self._handle_click(mouse_pos, ctrl, shift)

        wheel = io.mouse_wheel
        if wheel > 0:
            self.viewport.zoom_in(1, mouse_pos)
        if wheel < 0:
            self.viewport.zoom_out(1, mouse_pos)

    def update_menu_bar(self) -> None:
        global METER_SCALE, METER_SCALE_NAME, METER_INV_SCALE

        with imgui.begin_menu('Editor') as menu:
            if menu.opened:
                _, self.show_settings = imgui.menu_item('Project', None,
                                                        self.show_settings)
                _, self.show_inspector = imgui.menu_item('Inspector', None,
                                                    self.show_inspector)
                imgui.separator()

                v: Viewport = self.viewport
                _, v.show_grid = imgui.menu_item('Grid', None, v.show_grid)
                _, v.show_axes = imgui.menu_item('Axes', None, v.show_axes)

        with imgui.begin_menu('Scale') as menu:
            if menu.opened:
                meters: bool = (METER_SCALE_NAME == 'm')
                millimeters: bool = (METER_SCALE_NAME == 'mm')
                micrometers: bool = (METER_SCALE_NAME == 'um')
                nanometers: bool = (METER_SCALE_NAME == 'nm')
                angstroms: bool = (METER_SCALE_NAME == 'Å')

                meters, _ = imgui.menu_item('Meters', None, meters)
                millimeters, _ = imgui.menu_item('Millimeters', None, millimeters)
                micrometers, _ = imgui.menu_item('Micrometers', None, micrometers)
                nanometers, _ = imgui.menu_item('Nanometers', None, nanometers)
                angstroms, _ = imgui.menu_item('Angstroms', None, angstroms)

                if meters:
                    METER_SCALE_NAME = 'm'
                    METER_SCALE = 1
                    METER_INV_SCALE = 1
                if millimeters:
                    METER_SCALE_NAME = 'mm'
                    METER_SCALE = 1e-3
                    METER_INV_SCALE = 1e3
                if micrometers:
                    METER_SCALE_NAME = 'um'
                    METER_SCALE = 1e-6
                    METER_INV_SCALE = 1e6
                if nanometers:
                    METER_SCALE_NAME = 'nm'
                    METER_SCALE = 1e-9
                    METER_INV_SCALE = 1e9
                if angstroms:
                    METER_SCALE_NAME = 'Å'
                    METER_SCALE = 1e-10
                    METER_INV_SCALE = 1e10

    def update_ui(self) -> None:
        cond = imgui.FIRST_USE_EVER

        if self.show_settings:
            imgui.set_next_window_position(40, 40, cond)
            imgui.set_next_window_size(300, 500, cond)
            with imgui.begin('Project'):
                if self.project is None:
                    imgui.text_disabled('No Project Loaded')
                else:
                    self._ui_project()

        if self.show_inspector:
            imgui.set_next_window_position(360, 40, cond)
            imgui.set_next_window_size(300, 500, cond)
            with imgui.begin('Object Inspector'):
                if self.project is None:
                    imgui.text_disabled('No Project Loaded')
                elif len(self.selected) < 1:
                    imgui.text_disabled('No Object(s) Selected')
                else:
                    self._ui_inspector()

        self.viewport.update()

        # TODO: some kind of shape culling or filtering here
        self.viewport.shapes_to_draw = self.shapes
        self.viewport.draw()

    def set_project(self, proj: Project) -> None:
        self.project = None
        self._unselect_all()
        self.shapes.clear()

        self.project = proj
        if self.project:
            for n, s in self.project.objects.items():
                shape = EditableShape(n, s)
                self.shapes.append(shape)

    def _handle_select(self, point: Vec2, modifier: bool):
        if modifier:
            new_selection: bool = False
            for s in self.shapes:
                if s in self.selected:
                    continue
                if s.intersect_screen(self.viewport, point):
                    self.selected.add(s)
                    s.selected = True
                    new_selection = True
                    break
            if not new_selection:
                for s in self.selected:
                    if s.intersect_screen(self.viewport, point):
                        s.selected = False
                        self.selected.remove(s)
                        break
        else:
            select: EditableShape = None
            for s in self.shapes:
                if s.intersect_screen(self.viewport, point):
                    select = s
                    break
            self._select_shape(select)

    def _handle_click(self, pos: Vec2, ctrl: bool, shift: bool):
        self._handle_select(pos, shift)

    def _handle_dragging(self, pos: Vec2, diff: Vec2):
        began_dragging: bool = not self.is_dragging
        self.is_dragging = True

        if began_dragging:
            self.is_dragging_selection = False
            for s in self.selected:
                if s.intersect_screen(self.viewport, pos - diff):
                    self.is_dragging_selection = True
                    break
        if self.is_dragging_selection:
            for s in self.selected:
                s.translate_screen(self.viewport, diff)
