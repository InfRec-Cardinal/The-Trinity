                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                                           

                                                                          
                                                                           

                                                                              
                                                   
   
from typing import Sequence, Tuple
import abc
import itertools
import math

import numpy as np

from phyre.creator import constants
from phyre.interface.scene import ttypes as scene_if

SCENE_HEIGHT = constants.SCENE_HEIGHT
SCENE_WIDTH = constants.SCENE_WIDTH


def get_builders():

    def yield_subclasses(cls):
        for subcls in cls.__subclasses__():
            yield subcls
            yield from yield_subclasses(subcls)

    return {cls.__name__.lower(): cls for cls in yield_subclasses(ShapeBuilder)}


class ShapeBuilder(object):
    SHAPE_TYPE = scene_if.ShapeType.UNDEFINED

    @classmethod
    def default_sizes(cls, scale):
        pass                                                                  
        raise RuntimeError('Using "scale" is not supported for %s' %
                           cls.__name__)

    @classmethod
    def diameter_to_default_scale(cls, diameter):
        pass                                                     
        raise RuntimeError('Using "diameter" is not supported for %s' %
                           cls.__name__)

    @classmethod
    @abc.abstractmethod
    def _build(cls, **kwargs):
        pass                                   

                      
                                
                
                                                     
           
        pass

    @classmethod
    def build(cls, scale=None, diameter=None, **kwargs):
        pass                                                      

                                                       

                                                         
           
        assert not (scale is not None and diameter is not None
                   ), 'Cannot build shape from both scale and diameter'
        if diameter is not None:
            scale = cls.diameter_to_default_scale(diameter)
        if scale is not None:
            kwargs.update(cls.default_sizes(scale))
        ret = cls._build(**kwargs)
                                               
        if not isinstance(ret, (tuple, list)):
            ret = ret, None
        elif len(ret) < 2 or isinstance(ret[1], scene_if.Shape):
            ret = ret, None
                                                 
        shapes, phantom_vertices = ret
        if isinstance(shapes, scene_if.Shape):
            shapes = [shapes]
        return shapes, phantom_vertices

    @classmethod
    def diameter(cls, scale=None, **kwargs):
        if scale is not None:
            kwargs.update(cls.default_sizes(scale))
        return cls._diameter(**kwargs)

    @classmethod
    def _diameter(cls, **kwargs):
        raise NotImplementedError()

    @classmethod
    def diameter(cls, scale=None, **kwargs):
        if scale is not None:
            kwargs.update(cls.default_sizes(scale))
        return cls._diameter(**kwargs)

    @classmethod
    def _diameter(cls, **kwargs):
        raise NotImplementedError()


def _interpolate(scale_range, scale):
    assert len(scale_range) == 2
    return (1. - scale) * scale_range[0] + scale * scale_range[1]


def _inverse_interpolate(scale_range, interpolated_value):
    assert len(scale_range) == 2
    min_scale = min(scale_range)
    scale_range = [each - min_scale for each in scale_range]
    interpolated_value -= min_scale
    return interpolated_value / max(scale_range)


def vertices_to_polygon(vertices):
    poly_vertices = []
    for v in vertices:
        poly_vertices.append(scene_if.Vector(v[0], v[1]))
    shape = scene_if.Shape(polygon=scene_if.Polygon(vertices=poly_vertices))
    assert is_valid_convex_polygon(poly_vertices)
    return shape


def compute_shape_diameter(shape: scene_if.Shape) -> float:

    def distance(pair):
        p1, p2 = pair
        return ((p1.x - p2.x)**2 + (p1.y - p2.y)**2)**0.5

    if shape.polygon:
        return max(
            map(distance, itertools.combinations(shape.polygon.vertices, 2)))
    else:
        return shape.circle.radius


def _merge_centroids(points, masses):
    mass = sum(masses)
    x = sum(p[0] * m / mass for p, m in zip(points, masses))
    y = sum(p[1] * m / mass for p, m in zip(points, masses))
    return (x, y), mass


def compute_polygon_centroid(vertices: Sequence[Tuple[float, float]]
                            ) -> Tuple[Tuple[float, float], float]:
    pass                                                      

    def _triangle_centroid(points):
        x = sum(p[0] for p in points) / 3
        y = sum(p[1] for p in points) / 3
        l = lambda p1, p2: math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        a, b, c = map(l, points, points[1:] + points)
        p = (a + b + c) / 2
        mass = math.sqrt(p * (p - a) * (p - b) * (p - c))
        return (x, y), mass

    centroid = [0., 0.]
    mass = 0.
    for i in range(2, len(vertices)):
        triangle_centroid, triangle_mass = _triangle_centroid(
            [vertices[0], vertices[i - 1], vertices[i]])
        centroid, mass = _merge_centroids([centroid, triangle_centroid],
                                          [mass, triangle_mass])

    return centroid, mass


def compute_union_of_polygons_centroid(
        polygons: Sequence[Sequence[Tuple[float, float]]]
) -> Tuple[Tuple[float, float], float]:
    pass                                                      
    points, masses = zip(*map(compute_polygon_centroid, polygons))
    return _merge_centroids(points, masses)


def is_valid_convex_polygon(points):
                                                                          
                             
    if len(points) < 3:
        return False
    looped_points = points + points[:2]
    looped_points = [np.array([p.x, p.y]) for p in looped_points]
    for p1, p2, p3 in zip(looped_points, looped_points[1:], looped_points[2:]):
        a = p3 - p2
        b = p1 - p2
                                                                        
                   
        if a[0] * b[1] - a[1] * b[0] <= 0:
            return False
    return True


class Ball(ShapeBuilder):
    SHAPE_TYPE = scene_if.ShapeType.BALL
    RASTERIZATION_BUFFER = 0.5
    SCALE_RANGE = [0., SCENE_WIDTH / 2.]

    @classmethod
    def diameter_to_default_scale(cls, diameter):
        radius = diameter / 2.0 - cls.RASTERIZATION_BUFFER
        return _inverse_interpolate(cls.SCALE_RANGE, radius)

    @classmethod
    def default_sizes(cls, scale):
                                                      
        radius = _interpolate(cls.SCALE_RANGE, scale)
        return dict(radius=radius)

    @classmethod
    def _build(cls, radius):
                                                                 
        radius = int(radius) + cls.RASTERIZATION_BUFFER
        return scene_if.Shape(circle=scene_if.Circle(radius=radius))

    @classmethod
    def _diameter(cls, radius):
        return 2. * (int(radius) + cls.RASTERIZATION_BUFFER)


class Box(ShapeBuilder):
    SHAPE_TYPE = scene_if.ShapeType.UNDEFINED
    SCALE_RANGE = [0., SCENE_WIDTH]

    @classmethod
    def default_sizes(cls, scale):
        size = _interpolate(cls.SCALE_RANGE, scale)
        return dict(height=size, width=size)

    @classmethod
    def _build(cls, width, height):
        vertices = []
        for i in range(4):
            vx = (1 - 2 * (i in (1, 2))) / 2. * width
            vy = (1 - 2 * (i in (2, 3))) / 2. * height
            vertices.append((vx, vy))
        return vertices_to_polygon(vertices)

    @classmethod
    def _diameter(cls, width, height):
        return math.sqrt(width**2 + height**2)

    @classmethod
    def diameter_to_default_scale(cls, diameter):
        size = math.sqrt((diameter**2) / 2.0)
        return _inverse_interpolate(cls.SCALE_RANGE, size)


class Bar(Box):
    SHAPE_TYPE = scene_if.ShapeType.BAR
    BAR_HEIGHT = SCENE_WIDTH / 50.

    @classmethod
    def default_sizes(cls, scale):
        return dict(
            width=_interpolate(cls.SCALE_RANGE, scale),
            height=cls.BAR_HEIGHT,
        )

    @classmethod
    def diameter_to_default_scale(cls, diameter):
        size = math.sqrt((diameter**2) - (cls.BAR_HEIGHT**2))
        return _inverse_interpolate(cls.SCALE_RANGE, size)


class StandingSticks(ShapeBuilder):
    SHAPE_TYPE = scene_if.ShapeType.STANDINGSTICKS
    BAR_HEIGHT = SCENE_WIDTH / 50.
    ANGLE = 77.5
    SCALE_RANGE = [0., SCENE_WIDTH]

    @classmethod
    def default_sizes(cls, scale):
        return dict(
            angle=cls.ANGLE,
            width=_interpolate(cls.SCALE_RANGE, scale),
            height=cls.BAR_HEIGHT,
        )

    @classmethod
    def _build(cls, angle, width, height):

                                                                           
        bar = []
        y_offset = 0.0                                              
        for i in range(4):
            vx = ((1 - 2 * (i in (1, 2))) / 3.) * width
            vy = ((1 - 2 * (i in (2, 3))) / 3. + y_offset) * height
            bar.append((vx, vy))

                                           
        shapes = []
        radians = [_angle / 180. * math.pi for _angle in [-angle, angle]]
        for radian in radians:
            rotated_bar = []
            for x, y in bar:
                vx = math.cos(radian) * x - math.sin(radian) * y
                vy = math.cos(radian) * y + math.sin(radian) * x
                rotated_bar.append((vx, vy))
            shapes.append(rotated_bar)

                                     
        phantom_vertices = (shapes[1][1], shapes[1][2], shapes[0][3],
                            shapes[0][0], shapes[1][3], shapes[1][0],
                            shapes[0][1], shapes[0][2])

                        
        return [vertices_to_polygon(shape) for shape in shapes
               ], phantom_vertices

    @classmethod
    def _diameter(cls, angle, width, height):
        return math.sqrt(width**2 + height**2)

    @classmethod
    def diameter_to_default_scale(cls, diameter):
        width = math.sqrt((diameter**2) - (cls.BAR_HEIGHT**2))
        return _inverse_interpolate(cls.SCALE_RANGE, width)


class Jar(ShapeBuilder):
    SHAPE_TYPE = scene_if.ShapeType.JAR
    BASE_RATIO = 0.8
    WIDTH_RATIO = 1. / 1.2
    SCALE_RANGE = [0., SCENE_WIDTH]

    @classmethod
    def thickness_from_height(cls, height):
        return (math.log(height) / math.log(0.3 * SCENE_WIDTH) * SCENE_WIDTH /
                50)

    @classmethod
    def default_sizes(cls, scale):
        height = _interpolate(cls.SCALE_RANGE, scale)
        width = height * cls.WIDTH_RATIO
                                                                  
                           
        thickness = cls.thickness_from_height(height)
        return dict(
            height=height,
            width=width,
            thickness=thickness,
            base_width=width * cls.BASE_RATIO,
        )

    @classmethod
    def _build(cls, height, width, thickness, base_width):
                     
        vertices = []
        for i in range(4):
            vx = (1 - 2 * (i in (1, 2))) / 2. * base_width
            vy = (1 - 2 * (i in (2, 3))) / 2. * thickness
            vertices.append((vx, vy))

                                                   
        base = (width - base_width) / 2.
        hypotenuse = math.sqrt(height**2 + base**2)
        cos, sin = base / hypotenuse, height / hypotenuse
        x_delta = thickness * sin
        x_delta_top = thickness / sin
        y_delta = thickness * cos

                                  
        vertices_left = [
            [-width / 2, height - (thickness / 2)],
            [(-base_width / 2), -(thickness / 2)],
            [(-base_width / 2) + x_delta, y_delta - (thickness / 2)],
            [(-width / 2) + x_delta_top, height - (thickness / 2)],
        ]

                            
        vertices_right = [
            [width / 2, height - (thickness / 2)],
            [(width / 2) - x_delta_top, height - (thickness / 2)],
            [(base_width / 2) - x_delta, y_delta - (thickness / 2)],
            [(base_width / 2), -(thickness / 2)],
        ]

        phantom_vertices = (vertices_left[0], vertices_left[1],
                            vertices_right[3], vertices_right[0])
        shapes = [
            vertices_to_polygon(vertices),
            vertices_to_polygon(vertices_left),
            vertices_to_polygon(vertices_right),
        ]

        return shapes, phantom_vertices

    @classmethod
    def _diameter(cls, height, width, thickness, base_width):
        base = (width - base_width) / 2.0 + base_width
        return math.sqrt(base**2 + height**2)

    @classmethod
    def diameter_to_default_scale(cls, diameter):
        base_to_width_ratio = (1.0 - cls.BASE_RATIO) / 2.0 + cls.BASE_RATIO
        width_to_height_ratio = base_to_width_ratio * cls.WIDTH_RATIO
        height = math.sqrt((diameter**2) / (1 + (width_to_height_ratio**2)))
        return _inverse_interpolate(cls.SCALE_RANGE, height)

    @classmethod
    def center_of_mass(cls, *args, **kwargs):

        def undo_polygon(shape):
            return [(v.x, v.y) for v in shape.polygon.vertices]

        shapes, _ = cls.build(*args, **kwargs)
        verticies = list(map(undo_polygon, shapes))

        def _merge(points, masses):
            mass = sum(masses)
            x = sum(p[0] * m / mass for p, m in zip(points, masses))
            y = sum(p[1] * m / mass for p, m in zip(points, masses))
            return (x, y), mass

        def _triangle_centroid(points):
            x = sum(p[0] for p in points) / 3
            y = sum(p[1] for p in points) / 3
            l = lambda p1, p2: math.sqrt((p1[0] - p2[0])**2 +
                                         (p1[1] - p2[1])**2)
            a, b, c = map(l, points, points[1:] + points)
            p = (a + b + c) / 2
            mass = math.sqrt(p * (p - a) * (p - b) * (p - c))
            return (x, y), mass

        def _4angle_centroid(points):
            p1, m1 = _triangle_centroid([points[0], points[1], points[2]])
            p2, m2 = _triangle_centroid([points[0], points[3], points[2]])
            return _merge([p1, p2], [m1, m2])

        points, masses = zip(*map(_4angle_centroid, verticies))
        (x, y), _ = _merge(points, masses)
        assert abs(x) <= 1e-5, x
        return x, y
