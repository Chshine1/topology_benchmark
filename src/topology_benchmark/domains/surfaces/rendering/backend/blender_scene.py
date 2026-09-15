"""Build one deterministic orthographic scene inside Blender.

This module is executed by Blender rather than imported by the application.
"""

import argparse
import json
import math
import sys
from itertools import pairwise
from pathlib import Path

import bpy

UNIT = 0.01


def _arguments():
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(arguments)


def _rgba(value):
    value = value.lstrip("#")
    return *tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)), 1.0


def _mix(first, second, amount):
    return (
        *tuple(first[index] * (1 - amount) + second[index] * amount for index in range(3)),
        1.0,
    )


def _point(point, height, z):
    return point[0] * UNIT, (height - point[1]) * UNIT, z


def _emission_material(name, color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = _rgba(color)
    emission.inputs["Strength"].default_value = 1.0
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def _paper_material(name, base_color, paper):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    texture = nodes.new("ShaderNodeTexNoise")
    texture.noise_dimensions = "3D"
    texture.inputs["Scale"].default_value = paper["scale"]
    texture.inputs["Detail"].default_value = paper["detail"]
    mix = nodes.new("ShaderNodeMixRGB")
    color = _rgba(base_color)
    mix.blend_type = "MIX"
    mix.inputs[1].default_value = _mix(color, (0.15, 0.12, 0.08), paper["strength"])
    mix.inputs[2].default_value = _mix(color, (1.0, 1.0, 1.0), paper["strength"])
    coordinates = nodes.new("ShaderNodeTexCoord")
    material.node_tree.links.new(coordinates.outputs["Generated"], texture.inputs["Vector"])
    material.node_tree.links.new(texture.outputs["Fac"], mix.inputs[0])
    material.node_tree.links.new(mix.outputs["Color"], emission.inputs["Color"])
    material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def _hatched_material(name, fill_color, ink_color, paper, hatching):
    material = _paper_material(name, fill_color, paper)
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    emission = next(node for node in nodes if node.bl_idname == "ShaderNodeEmission")
    paper_color = emission.inputs["Color"].links[0].from_socket
    links.remove(emission.inputs["Color"].links[0])
    coordinates = next(node for node in nodes if node.bl_idname == "ShaderNodeTexCoord")

    factors = []
    for angle in (hatching["angle_degrees"], hatching["cross_angle_degrees"]):
        rotate = nodes.new("ShaderNodeVectorRotate")
        rotate.rotation_type = "AXIS_ANGLE"
        rotate.inputs["Axis"].default_value = (0.0, 0.0, 1.0)
        rotate.inputs["Angle"].default_value = math.radians(angle)
        wave = nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = hatching["scale"]
        threshold = nodes.new("ShaderNodeMath")
        threshold.operation = "LESS_THAN"
        threshold.inputs[1].default_value = hatching["width"]
        links.new(coordinates.outputs["Generated"], rotate.inputs["Vector"])
        links.new(rotate.outputs["Vector"], wave.inputs["Vector"])
        links.new(wave.outputs["Fac"], threshold.inputs[0])
        factors.append(threshold.outputs[0])

    union = nodes.new("ShaderNodeMath")
    union.operation = "MAXIMUM"
    links.new(factors[0], union.inputs[0])
    links.new(factors[1], union.inputs[1])
    strength = nodes.new("ShaderNodeMath")
    strength.operation = "MULTIPLY"
    strength.inputs[1].default_value = hatching["strength"]
    links.new(union.outputs[0], strength.inputs[0])
    mix = nodes.new("ShaderNodeMixRGB")
    mix.inputs[2].default_value = _rgba(ink_color)
    links.new(strength.outputs[0], mix.inputs[0])
    links.new(paper_color, mix.inputs[1])
    links.new(mix.outputs["Color"], emission.inputs["Color"])
    return material


def _plane(name, vertices, material, height, z, collection=None):
    mesh = bpy.data.meshes.new(f"{name}-mesh")
    mesh.from_pydata([_point(point, height, z) for point in vertices], [], [range(len(vertices))])
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def _stroke_displacement(displacement, seed):
    group = bpy.data.node_groups.new("SeededStrokeDisplacement", "GeometryNodeTree")
    group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nodes = group.nodes
    links = group.links
    input_node = nodes.new("NodeGroupInput")
    output_node = nodes.new("NodeGroupOutput")
    resample = nodes.new("GeometryNodeResampleCurve")
    resample.inputs["Count"].default_value = displacement["samples"]
    position = nodes.new("GeometryNodeInputPosition")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value = displacement["scale"]
    noise.inputs["W"].default_value = float(seed % 10000)
    center = nodes.new("ShaderNodeVectorMath")
    center.operation = "SUBTRACT"
    center.inputs[1].default_value = (0.5, 0.5, 0.5)
    flatten = nodes.new("ShaderNodeVectorMath")
    flatten.operation = "MULTIPLY"
    flatten.inputs[1].default_value = (1.0, 1.0, 0.0)
    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs[3].default_value = displacement["amplitude"]
    set_position = nodes.new("GeometryNodeSetPosition")
    links.new(input_node.outputs["Geometry"], resample.inputs["Curve"])
    links.new(resample.outputs["Curve"], set_position.inputs["Geometry"])
    links.new(position.outputs["Position"], noise.inputs["Vector"])
    links.new(noise.outputs["Color"], center.inputs[0])
    links.new(center.outputs["Vector"], flatten.inputs[0])
    links.new(flatten.outputs["Vector"], scale.inputs[0])
    links.new(scale.outputs["Vector"], set_position.inputs["Offset"])
    links.new(set_position.outputs["Geometry"], output_node.inputs["Geometry"])
    return group


def _curve(name, points, material, radius, height, z, displacement_group=None):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for target, point in zip(spline.points, points, strict=True):
        target.co = (*_point(point, height, z), 1.0)
    curve.materials.append(material)
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    if displacement_group is not None:
        modifier = obj.modifiers.new("Seeded displacement", "NODES")
        modifier.node_group = displacement_group
    return obj


def _dashed_curve(name, start, end, pattern, material, radius, height, z, displacement_group):
    length = math.dist(start, end)
    cursor = 0.0
    draw = True
    index = 0
    while cursor < length:
        amount = pattern[index % len(pattern)] * 3.0
        next_cursor = min(length, cursor + amount)
        if draw:
            first = cursor / length
            second = next_cursor / length
            points = [
                (start[0] + (end[0] - start[0]) * first, start[1] + (end[1] - start[1]) * first),
                (
                    start[0] + (end[0] - start[0]) * second,
                    start[1] + (end[1] - start[1]) * second,
                ),
            ]
            _curve(f"{name}-{index}", points, material, radius, height, z, displacement_group)
        cursor = next_cursor
        draw = not draw
        index += 1


def _sample_polyline(points, fraction):
    lengths = [math.dist(first, second) for first, second in pairwise(points)]
    target = sum(lengths) * fraction
    traversed = 0.0
    for index, length in enumerate(lengths):
        if traversed + length >= target:
            local = (target - traversed) / max(length, 1e-9)
            first, second = points[index], points[index + 1]
            point = (
                first[0] + (second[0] - first[0]) * local,
                first[1] + (second[1] - first[1]) * local,
            )
            return point, math.atan2(second[1] - first[1], second[0] - first[0])
        traversed += length
    return points[-1], 0.0


def _arrow(name, points, fraction, material, size, height, z):
    point, angle = _sample_polyline(points, fraction)
    size *= 0.34
    backward = angle + math.pi
    vertices = [
        point,
        (
            point[0] + size * math.cos(backward + 0.48),
            point[1] + size * math.sin(backward + 0.48),
        ),
        (
            point[0] + size * math.cos(backward - 0.48),
            point[1] + size * math.sin(backward - 0.48),
        ),
    ]
    _plane(name, vertices, material, height, z)


def _text(name, value, position, material, size, _family, height, z, italic=False):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = value
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = size * UNIT * 0.72
    curve.shear = 0.18 if italic else 0.0
    curve.extrude = 0.001
    curve.materials.append(material)
    obj = bpy.data.objects.new(name, curve)
    obj.location = _point(position, height, z)
    bpy.context.scene.collection.objects.link(obj)


def _configure_freestyle(scene, style, ink_color, outline_collection):
    freestyle = style["freestyle"]
    if freestyle is None:
        return
    scene.render.use_freestyle = True
    line_set = bpy.context.view_layer.freestyle_settings.linesets[0]
    line_set.select_by_collection = True
    line_set.collection = outline_collection
    line_set.collection_negation = "INCLUSIVE"
    line_style = line_set.linestyle
    line_style.color = _rgba(ink_color)[:3]
    line_style.thickness = freestyle["thickness"]
    line_style.caps = "ROUND"
    line_style.use_chaining = True
    line_style.chaining = "SKETCHY"
    line_style.rounds = freestyle["rounds"]
    modifier = line_style.geometry_modifiers.new("Pencil spatial noise", "SPATIAL_NOISE")
    modifier.amplitude = freestyle["spatial_noise_amplitude"]
    modifier.scale = freestyle["spatial_noise_scale"]
    modifier.octaves = 2
    modifier.use_pure_random = False


def _build(document, output):
    expected_version = tuple(int(part) for part in document["style"]["blender_version"].split("."))
    if bpy.app.version[:2] != expected_version:
        raise RuntimeError(
            f"style requires Blender {document['style']['blender_version']}, "
            f"but this process is Blender {bpy.app.version_string}"
        )
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    width, height = document["width"], document["height"]
    style, palette = document["style"], document["palette"]
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output)
    scene.render.use_file_extension = True
    scene.world.color = _rgba(style["canvas_color"])[:3]
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    camera_data = bpy.data.cameras.new("Orthographic Camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = height * UNIT
    camera = bpy.data.objects.new("Orthographic Camera", camera_data)
    camera.location = (width * UNIT / 2, height * UNIT / 2, 10.0)
    scene.collection.objects.link(camera)
    scene.camera = camera

    paper_material = _paper_material("Procedural paper", style["canvas_color"], style["paper"])
    _plane(
        "Paper",
        [(-4, -4), (width + 4, -4), (width + 4, height + 4), (-4, height + 4)],
        paper_material,
        height,
        -0.1,
    )
    ink = _emission_material("Ink", palette["ink"])
    path_materials = {
        color: _emission_material(f"Path-{index}", color)
        for index, color in enumerate(palette["path_colors"])
    }
    fill = (
        _hatched_material(
            "Hatched polygon fill",
            palette["fill"],
            palette["ink"],
            style["paper"],
            style["hatching"],
        )
        if style["hatching"] is not None
        else _paper_material("Polygon fill", palette["fill"], style["paper"])
    )
    outline_collection = bpy.data.collections.new("Freestyle source")
    scene.collection.children.link(outline_collection)
    displacement_group = (
        _stroke_displacement(style["curve_displacement"], document["seed"])
        if style["curve_displacement"] is not None
        else None
    )

    for index, polygon in enumerate(document["polygons"]):
        _plane(f"Polygon-{index}", polygon["vertices"], fill, height, 0.0, outline_collection)
        center = tuple(
            sum(vertex[axis] for vertex in polygon["vertices"]) / len(polygon["vertices"])
            for axis in (0, 1)
        )
        _text(
            f"Polygon-label-{index}",
            polygon["name"],
            center,
            ink,
            style["labels"]["polygon_size"],
            style["labels"]["font_family"],
            height,
            0.08,
        )

    glued = {}
    for gluing in document["gluings"]:
        glued[tuple(gluing["first"])] = (gluing, True)
        glued[tuple(gluing["second"])] = (gluing, False)
    for polygon_index, polygon in enumerate(document["polygons"]):
        vertices = polygon["vertices"]
        center = tuple(sum(vertex[axis] for vertex in vertices) / len(vertices) for axis in (0, 1))
        for edge_index, start in enumerate(vertices):
            end = vertices[(edge_index + 1) % len(vertices)]
            mark = glued.get((polygon_index, edge_index))
            cross_polygon = mark is not None and mark[0]["first"][0] != mark[0]["second"][0]
            radius = style["stroke"]["bevel_depth"]
            if cross_polygon:
                _dashed_curve(
                    f"Dotted-edge-{polygon_index}-{edge_index}",
                    start,
                    end,
                    style["stroke"]["dotted_pattern"],
                    ink,
                    radius,
                    height,
                    0.04,
                    displacement_group,
                )
            elif style["freestyle"] is None:
                _curve(
                    f"Edge-{polygon_index}-{edge_index}",
                    [start, end],
                    ink,
                    radius,
                    height,
                    0.04,
                    displacement_group,
                )
            if mark is not None:
                gluing, first = mark
                forward = first or gluing["same_direction"]
                directed = [start, end] if forward else [end, start]
                _arrow(
                    f"Gluing-arrow-{polygon_index}-{edge_index}",
                    directed,
                    0.5,
                    ink,
                    style["arrows"]["gluing_size"],
                    height,
                    0.07,
                )
                midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                direction = (midpoint[0] - center[0], midpoint[1] - center[1])
                length = max(math.hypot(*direction), 1e-9)
                offset = style["labels"]["gluing_offset"]
                label_position = (
                    midpoint[0] + offset * direction[0] / length,
                    midpoint[1] + offset * direction[1] / length,
                )
                _text(
                    f"Gluing-label-{polygon_index}-{edge_index}",
                    gluing["label"],
                    label_position,
                    ink,
                    style["labels"]["gluing_size"],
                    style["labels"]["font_family"],
                    height,
                    0.08,
                )

    for index, path in enumerate(document["paths"]):
        material = path_materials.setdefault(
            path["color"], _emission_material(f"Path-extra-{index}", path["color"])
        )
        radius = style["stroke"]["bevel_depth"] * (
            style["stroke"]["path_width"] / style["stroke"]["polygon_width"]
        )
        _curve(
            f"Path-{index}",
            path["points"],
            material,
            radius,
            height,
            0.1,
            displacement_group,
        )
        count = path["order"] if path["order_display"] == "arrow-count" else 1
        for arrow_index in range(count):
            start, end = style["arrows"]["spread_start"], style["arrows"]["spread_end"]
            fraction = (
                (start + end) / 2
                if count == 1
                else start + arrow_index * (end - start) / (count - 1)
            )
            _arrow(
                f"Path-arrow-{index}-{arrow_index}",
                path["points"],
                fraction,
                material,
                style["arrows"]["path_size"],
                height,
                0.13,
            )
        if path["order_display"] == "number-tag" and path["tag_position"] is not None:
            _text(
                f"Path-order-{index}",
                str(path["order"]),
                path["tag_position"],
                material,
                style["labels"]["order_size"],
                style["labels"]["font_family"],
                height,
                0.14,
            )
        if path["order"] == 1 and path["name_position"] is not None:
            _text(
                f"Path-label-{index}",
                path["name"],
                path["name_position"],
                material,
                style["labels"]["path_size"],
                style["labels"]["font_family"],
                height,
                0.14,
                True,
            )

    for index, edge_label in enumerate(document["edge_labels"]):
        polygon_index, edge_index = edge_label["edge"]
        vertices = document["polygons"][polygon_index]["vertices"]
        start, end = vertices[edge_index], vertices[(edge_index + 1) % len(vertices)]
        midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        _text(
            f"Edge-label-{index}",
            edge_label["label"],
            midpoint,
            path_materials[palette["path_colors"][0]],
            style["labels"]["path_size"],
            style["labels"]["font_family"],
            height,
            0.15,
        )

    _configure_freestyle(scene, style, palette["ink"], outline_collection)
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    args = _arguments()
    _build(json.loads(Path(args.scene).read_text(encoding="utf-8")), Path(args.output))
