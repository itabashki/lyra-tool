import logging as log
from xml.dom.minidom import Node, Document, Element, parse
from collections import OrderedDict
from __version__ import __version__
from io import IOBase
from project import *


def _append_children(node: Node, children: list[Node]) -> Node:
    for c in children:
        node.appendChild(c)


def _shape_xml_tag(shape: ShapeObject) -> str:
    typ: type = type(shape)

    # Can't use type as a key in dict, so this is the alternative
    if typ is PointShape: return 'Dot'
    elif typ is CrossShape: return 'Cross'
    elif typ is ReferencePoint: return 'ReferencePoint'
    elif typ is LineShape: return 'Line'
    elif typ is RectangleShape: return 'Rectangle'
    elif typ is FilledRectangleShape: return 'RectangleFilled'
    elif typ is RectanglePolishShape: return 'RectanglePolish'
    elif typ is RectangleStairsShape: return 'RectangleStairs'
    elif typ is CircleShape: return 'Circle'
    elif typ is FilledCircleShape: return 'CircleFilled'
    elif typ is AnnulusShape: return 'CircleAnnulus'
    elif typ is CirclePolishShape: return 'CirclePolish'
    elif typ is CircleStairsShape: return 'CircleStairs'
    else:
        raise TypeError(f'unknown ShapeObject class: {typ}')


def _xml_tag_shape(tag: str) -> ShapeObject:
    if tag == 'Dot': return PointShape()
    elif tag == 'Cross': return CrossShape()
    elif tag == 'ReferencePoint': return ReferencePoint()
    elif tag == 'Line': return LineShape()
    elif tag == 'Rectangle': return RectangleShape()
    elif tag == 'RectangleFilled': return FilledRectangleShape()
    elif tag == 'RectanglePolish': return RectanglePolishShape()
    elif tag == 'RectangleStairs': return RectangleStairsShape()
    elif tag == 'Circle': return CircleShape()
    elif tag == 'CircleFilled': return FilledCircleShape()
    elif tag == 'CircleAnnulus': return AnnulusShape()
    elif tag == 'CirclePolish': return CirclePolishShape()
    elif tag == 'CircleStairs': return CircleStairsShape()
    else:
        log.warning(f'Unrecognized XML shape tag: {tag}')
    return None


def _shape_to_dom(shape: ShapeObject, name: str, doc: Document) -> Element:
    if not isinstance(shape, ShapeObject):
        raise TypeError('shape is not a subclass of ShapeObject')

    elem: Element = doc.createElement(_shape_xml_tag(shape))
    elem.attributes['Name'] = name
    elem.attributes['DepthUnit'] = 'scan'
    elem.attributes['Depth'] = f'{shape.depth:d}'

    if isinstance(shape, (PointShape, RectangleShape, CircleShape)):
        elem.attributes['Center'] = f'{shape.center.x:e} {shape.center.y:e}'

    if isinstance(shape, LineShape):
        l: LineShape = shape
        elem.attributes['Begin'] = f'{l.begin.x:e} {l.begin.y:e}'
        elem.attributes['End'] = f'{l.end.x:e} {l.end.y:e}'

    if isinstance(shape, CrossShape):
        x: CrossShape = shape
        elem.attributes['Width'] = f'{x.width:e}'

    if isinstance(shape, RectangleShape):
        r: RectangleShape = shape
        elem.attributes['Width'] = f'{r.dimensions.x:e}'
        elem.attributes['Height'] = f'{r.dimensions.y:e}'
        elem.attributes['Angle'] = f'{r.angle:f}'
        elem.attributes['SettleTimeLine'] = f'{r.settle_time_line:e}'

    if isinstance(shape, CircleShape):
        if isinstance(shape, AnnulusShape):
            a: AnnulusShape = shape
            elem.attributes['RadiusA'] = f'{a.radius:e}'
            elem.attributes['RadiusB'] = f'{a.inner_radius:e}'
        else:
            c: CircleShape = shape
            elem.attributes['Radius'] = f'{c.radius:e}'

    if not isinstance(shape, ReferencePoint):
        elem.attributes['SettleTimeFrame'] = f'{shape.settle_time_frame:e}'

    return elem


def _parse_xml_str(elem: Element, attr: str) -> str:
    a = elem.attributes[attr]
    return a.value


def _parse_xml_vec2(elem: Element, attr: str) -> Vec2:
    a: str = _parse_xml_str(elem, attr)
    x, y = a.split(' ')
    return Vec2(float(x), float(y))


def _parse_xml_float(elem: Element, attr: str) -> float:
    a: str = _parse_xml_str(elem, attr)
    return float(a)


def _parse_xml_int(elem: Element, attr: str) -> int:
    a: str = _parse_xml_str(elem, attr)
    return int(a)


def _parse_xml_bool(elem: Element, attr: str) -> bool:
    a: str = _parse_xml_str(elem, attr)
    if a.lower() == 'false':
        return False
    elif a.lower() == 'true':
        return True
    return bool(a)


def _shape_from_dom(elem: Element) -> tuple[str, ShapeObject]:
    shape: ShapeObject = _xml_tag_shape(elem.tagName)
    if shape is None:
        log.warning(f'Skipping unparseable elememnt: {elem}')
        return (None, None)

    name: str = _parse_xml_str(elem, 'Name')
    depth_unit: str = _parse_xml_str(elem, 'DepthUnit')
    if depth_unit != 'scan':
        log.warning(f'Unexpected DepthUnit ({depth_unit}) for elem: {elem}')
    shape.depth = _parse_xml_int(elem, 'Depth')

    if isinstance(shape, (PointShape, RectangleShape, CircleShape)):
        shape.center = _parse_xml_vec2(elem, 'Center')

    if isinstance(shape, LineShape):
        l: LineShape = shape
        l.begin = _parse_xml_vec2(elem, 'Begin')
        l.end = _parse_xml_vec2(elem, 'End')

    if isinstance(shape, CrossShape):
        x: CrossShape = shape
        x.width = _parse_xml_float(elem, 'Width')

    if isinstance(shape, RectangleShape):
        r: RectangleShape = shape
        r.dimensions.x = _parse_xml_float(elem, 'Width')
        r.dimensions.y = _parse_xml_float(elem, 'Height')
        r.angle = _parse_xml_float(elem, 'Angle')
        r.settle_time_line = _parse_xml_float(elem, 'SettleTimeLine')

    if isinstance(shape, CircleShape):
        if isinstance(shape, AnnulusShape):
            a: AnnulusShape = shape
            a.radius = _parse_xml_float(elem, 'RadiusA')
            a.inner_radius = _parse_xml_float(elem, 'RadiusB')
        else:
            c: CircleShape = shape
            c.radius = _parse_xml_float(elem, 'Radius')

    if not isinstance(shape, CrossShape):
        shape.settle_time_frame = _parse_xml_float(elem, 'SettleTimeFrame')

    return (name, shape)


def _settings_to_dom(s: ProjectSettings, doc: Document) -> list[Element]:
    out = []
    material = doc.createElement('Material')
    material.attributes['proc'] = s.process
    material.attributes['name'] = s.material_name
    material.attributes['energy'] = f'{s.energy:f}'
    material.attributes['dwelltime'] = f'{s.dwell_time:e}'
    material.attributes['overlapping'] = f'{s.overlap:f}'
    material.attributes['description'] = s.description
    material.attributes['dose'] = f'{s.dose:e}'
    out.append(material)

    settings = doc.createElement('Settings')
    settings.attributes['BeamCurrent'] = f'{s.beam_current:e}'
    settings.attributes['SpotSize'] = f'{s.spot_size:e}'
    settings.attributes['Parallel'] = 'true' if s.parallel else 'false'
    out.append(settings)

    return out


def _settings_from_dom(material: Element, settings: Element) -> ProjectSettings:
    ps = ProjectSettings()
    ps.process = _parse_xml_str(material, 'proc')
    ps.material_name = _parse_xml_str(material, 'name')
    ps.energy = _parse_xml_float(material, 'energy')
    ps.dwell_time = _parse_xml_float(material, 'dwelltime')
    ps.overlap = _parse_xml_float(material, 'overlapping')
    ps.description = _parse_xml_str(material, 'description')
    ps.dose = _parse_xml_float(material, 'dose')

    ps.beam_current = _parse_xml_float(settings, 'BeamCurrent')
    ps.spot_size = _parse_xml_float(settings, 'SpotSize')
    ps.parallel = _parse_xml_bool(settings, 'Parallel')
    return ps


def _project_to_dom(proj: Project, doc: Document) -> Element:
    elem = doc.createElement('Project')
    elem.attributes['ver'] = '1.0'

    settings = _settings_to_dom(proj.settings, doc)
    _append_children(elem, settings)

    objlist = doc.createElement('ObjectList')
    for name, obj in proj.objects.items():
        objlist.appendChild(_shape_to_dom(obj, name, doc))

    elem.appendChild(objlist)
    return elem


def _project_from_dom(elem: Element) -> Project:
    material: Element = None
    settings: Element = None
    obj_list: Element = None

    for child in elem.childNodes:
        if child.nodeType == Node.ELEMENT_NODE:
            if child.tagName == 'Material':
                material = child
            if child.tagName == 'Settings':
                settings = child
            if child.tagName == 'ObjectList':
                obj_list = child

    project = Project()
    project.settings = _settings_from_dom(material, settings)

    for child in obj_list.childNodes:
        if child.nodeType == Node.ELEMENT_NODE:
            name, obj = _shape_from_dom(child)
            if obj is not None:
                project.objects[name] = obj

    return project


def to_dom(project: Project) -> Document:
    doc = Document()

    meta = doc.createComment(f' Generated by LyraTool v{__version__} ')
    doc.appendChild(meta)

    pnode = _project_to_dom(project, doc)
    doc.appendChild(pnode)

    return doc


def from_dom(doc: Document) -> Project:
    pelem: Element = None
    for child in doc.childNodes:
        if child.nodeType == Node.ELEMENT_NODE:
            if child.tagName == 'Project':
                pelem = child
                break
    if pelem is None:
        raise RuntimeError('Failed to find Project XML element')
    return _project_from_dom(pelem)


def to_file(project: Project, file: IOBase):
    doc = to_dom(project)
    doc.writexml(file, indent='', addindent=' ', newl='\n', standalone=True)


def from_file(file: IOBase) -> Project:
    doc = parse(file)
    proj = from_dom(doc)
    return proj
