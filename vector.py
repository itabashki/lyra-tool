from typing import Any
import numpy as np
from numpy import matrix
from numpy._typing import ArrayLike, DTypeLike
from math import sin, cos, radians
import numpy.linalg as linalg


class Vec2(np.ndarray):
    def __new__(self, x: float = 0.0, y: float = None):
        if y is None:
            y = x  # Duplicate values if only a single value is provided
        if type(x) is Vec2:
            y = x.y
            x = x.x
        arr = np.array([x, y, 1], dtype=np.float64)
        return super().__new__(self, shape=(3,), dtype=np.float64, buffer=arr)

    @property
    def x(self) -> float:
             return self[0]

    @x.setter
    def x(self, value: float):
        self[0] = value

    @property
    def y(self) -> float:
        return self[1]

    @y.setter
    def y(self, value: float):
        self[1] = value

    @property
    def length(self) -> float:
        return linalg.norm(self)

    @property
    def abs(self):
        return Vec2(abs(self[0]), abs(self[1]))

    def normalized(self):
        l: float = self.length
        if l == 0.0:
            return Vec2()
        else:
            return Vec2(self) / l

    def atan2(self) -> float:
        return np.arctan2(self[0], self[1])


class Matrix3x3(np.ndarray):
    def __new__(self):
        arr = np.zeros((3,3), dtype=np.float64)
        return super().__new__(self, shape=(3,3), dtype=np.float64, buffer=arr)

    def set_scale(self, x: float, y: float) -> None:
        self[0][0] = x
        self[1][1] = y
        self[2][2] = 1

    def set_rotation(self, angle: float) -> None:
        sin_angle: float = sin(radians(angle))
        cos_angle: float = cos(radians(angle))
        self[0][0] = cos_angle
        self[0][1] = -sin_angle
        self[1][0] = sin_angle
        self[1][1] = cos_angle

    def set_translation(self, x: float, y: float) -> None:
        self[0][2] = x
        self[1][2] = y
        self[2][2] = 1

    def dot_vec2(self, v: Vec2) -> Vec2:
        result = self.dot(v.transpose())
        return Vec2(result[0], result[1])


class Rect:
    def __init__(self) -> None:
        self._center: Vec2 = Vec2()
        self._half_dims: Vec2 = Vec2()

    @property
    def center(self) -> Vec2:
        return self._center

    @center.setter
    def center(self, value: Vec2):
        self._center = value

    @property
    def width(self) -> float:
        return self._half_dims.x * 2.0

    @width.setter
    def width(self, value: float):
        self._half_dims.x = max(value, 0) * 0.5

    @property
    def height(self) -> float:
        return self._half_dims.y * 2.0

    @height.setter
    def height(self, value: float):
        self._half_dims.y = max(value, 0) * 0.5

    @property
    def half_dims(self) -> Vec2:
        return self._half_dims

    @half_dims.setter
    def half_dims(self, value: Vec2):
        self._half_dims = np.maximum(value, Vec2())

    @property
    def dimensions(self) -> Vec2:
        return self._half_dims * 2.0

    @dimensions.setter
    def dimensions(self, value: Vec2):
        self._half_dims = np.maximum(value * 0.5, Vec2())

    @property
    def min_point(self) -> Vec2:
        return self._center - self._half_dims

    @property
    def max_point(self) -> Vec2:
        return self._center + self._half_dims

    @property
    def left(self) -> float:
        return self._center.x - self._half_dims.x

    @property
    def right(self) -> float:
        return self._center.x + self._half_dims.x

    @property
    def bottom(self) -> float:
        return self._center.y - self._half_dims.y

    @property
    def top(self) -> float:
        return self._center.y + self._half_dims.y

    def overlaps_rect(self, other) -> bool:
        if abs(self._center.x - other._center.x) \
            > (self._half_dims.x + other._half_dims.x):
            return False
        if abs(self._center.y - other._center.y) \
            > (self._half_dims.y + other._half_dims.y):
            return False
        return True

    def overlaps_point(self, p: Vec2) -> bool:
        aabb_min: Vec2 = self.min_point
        aabb_max: Vec2 = self.max_point
        if (p.x < aabb_min.x) or (p.x > aabb_max.x):
            return False
        if (p.y < aabb_min.y) or (p.y > aabb_max.y):
            return False
        return True
