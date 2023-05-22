from collections import OrderedDict
from vector import Vec2
from enum import Enum, auto


class ProjectSettings:
    def __init__(self) -> None:
        self.process: str = ''
        self.material_name: str = ''
        self.description: str = ''
        self.energy: float = 0.0
        self.dwell_time: float = 0.0
        self.overlap: float = 1.0
        self.dose: float = 0.0
        self.beam_current: float = 0.0
        self.spot_size: float = 0.0
        self.parallel: bool = False


# Base class for all shape objects
class ShapeObject:
    def __init__(self) -> None:
        self.depth: int = 1
        self.settle_time_frame: float = 0.0


class PointShape(ShapeObject):
    def __init__(self) -> None:
        super().__init__()
        self.center: Vec2 = Vec2()


class CrossShape(PointShape):
    def __init__(self) -> None:
        super().__init__()
        self.width: float = 0.0


class ReferencePoint(CrossShape):
    def __init__(self) -> None:
        super().__init__()


class LineShape(ShapeObject):
    def __init__(self) -> None:
        super().__init__()
        self.begin: Vec2 = Vec2()
        self.end: Vec2 = Vec2()

    @property
    def length(self) -> float:
        return (self.end - self.begin).length


class RectangleShape(ShapeObject):
    def __init__(self) -> None:
        super().__init__()
        self.center: Vec2 = Vec2()
        self.dimensions: Vec2 = Vec2()
        self.angle: float = 0.0
        self.settle_time_line: float = 0.0


class FilledRectangleShape(RectangleShape):
    def __init__(self) -> None:
        super().__init__()


# TODO: figure out what this actually does
class RectanglePolishShape(FilledRectangleShape):
    def __init__(self) -> None:
        super().__init__()


# TODO: figure out what this actually does
class RectangleStairsShape(FilledRectangleShape):
    def __init__(self) -> None:
        super().__init__()


class CircleShape(ShapeObject):
    def __init__(self) -> None:
        super().__init__()
        self.center: Vec2 = Vec2()
        self.radius: float = 0.0


class FilledCircleShape(CircleShape):
    def __init__(self) -> None:
        super().__init__()


class AnnulusShape(FilledCircleShape):
    def __init__(self) -> None:
        super().__init__()
        self.inner_radius: float = 0.0


# TODO: figure out what this actually does
class CirclePolishShape(AnnulusShape):
    def __init__(self) -> None:
        super().__init__()


# TODO: figure out what this actually does
class CircleStairsShape(AnnulusShape):
    def __init__(self) -> None:
        super().__init__()


SHAPE_TYPENAME_TO_TYPE = {
    'PointShape': PointShape,
    'CrossShape': CrossShape,
    'ReferencePoint': ReferencePoint,
    'LineShape': LineShape,
    'RectangleShape': RectangleShape,
    'FilledRectangleShape': FilledRectangleShape,
    'RectanglePolishShape': RectanglePolishShape,
    'RectangleStairsShape': RectangleStairsShape,
    'CircleShape': CircleShape,
    'FilledCircleShape': FilledCircleShape,
    'AnnulusShape': AnnulusShape,
    'CirclePolishShape': CirclePolishShape,
    'CircleStairsShape': CircleStairsShape,
}


class Project:
    SHAPE_NAME_PREFIX = {
        'PointShape': 'Dot',
        'CrossShape': 'Cross',
        'LineShape': 'Line',
        'RectangleShape': 'Rectangle',
        'FilledRectangleShape': 'Filled rect',
        'CircleShape': 'Circle',
        'FilledCircleShape': 'Filled circle',
        'AnnulusShape': 'Annulus',
    }

    def __init__(self) -> None:
        self.settings = ProjectSettings()
        self.objects: OrderedDict = OrderedDict()

    def _shape_name_prefix(self, shape: ShapeObject) -> str:
        typ: type = type(shape)
        typename: str = typ.__name__

        if typename in self.SHAPE_NAME_PREFIX:
            return self.SHAPE_NAME_PREFIX[typename]
        else:
            raise TypeError(f'unknown ShapeObject subclass: {typ}')

    def _new_shape_name(self, shape: ShapeObject) -> str:
        prefix = self._shape_name_prefix(shape)

        # TODO: this is a very inefficient way of finding unused indices
        indices = set()
        for name in self.objects:
            n: str = name
            if n.startswith(prefix):
                n = n.removeprefix(prefix)
                n = n.strip()
                try:
                    i: int = int(n)
                    indices.add(i)
                except ValueError:
                    pass

        free_index: int = 1
        if len(indices) > 0:
            indices = sorted(indices)
            for i in indices:
                if i < free_index:
                    continue
                if free_index == i:
                    free_index += 1

        return f'{prefix} {free_index:d}'


    def add_new_shape(self, shape: ShapeObject) -> str:
        if not isinstance(shape, ShapeObject):
            raise TypeError('shape is not a subclass of ShapeObject')

        name = self._new_shape_name(shape)
        self.objects[name] = shape

        return name

    def remove_shape(self, name: str) -> None:
        self.objects.pop(name)

def new_project() -> Project:
    settings = ProjectSettings()
    settings.process = 'E-Lithography'
    settings.material_name = 'Default material'
    settings.energy = 30000
    settings.dwell_time = 0.0001
    settings.overlap = 1.0
    settings.dose = 2.0
    settings.beam_current = 1.0e-010
    settings.spot_size = 4.0e-008
    settings.parallel = False

    proj = Project()
    proj.settings = settings

    # circle = CircleShape()
    # circle.center = Vec2(1e-6)
    # circle.radius = 1e-6
    # proj.add_new_shape(circle)

    # circle2 = FilledCircleShape()
    # circle2.center = Vec2(1e-6)
    # circle2.radius = 0.8e-6
    # proj.add_new_shape(circle2)

    # annulus = AnnulusShape()
    # annulus.center = Vec2(4e-6, 1e-6)
    # annulus.radius = 1e-6
    # annulus.inner_radius = 5e-7
    # proj.add_new_shape(annulus)

    # rect = RectangleShape()
    # rect.dimensions = Vec2(2e-6, 1e-6)
    # rect.center = Vec2(1e-6, 3e-6)
    # proj.add_new_shape(rect)

    # rect2 = FilledRectangleShape()
    # rect2.dimensions = Vec2(2e-6, 3e-6)
    # rect2.center = Vec2(4e-6, 4e-6)
    # rect2.angle = 30.0
    # proj.add_new_shape(rect2)

    # cross = CrossShape()
    # cross.center = Vec2(2.5e-6, 2.5e-6)
    # cross.width = 5e-7
    # proj.add_new_shape(cross)

    # line = LineShape()
    # line.begin = Vec2(6e-6, 6e-6)
    # line.end = Vec2(7e-6, 8e-6)
    # proj.add_new_shape(line)

    return proj
