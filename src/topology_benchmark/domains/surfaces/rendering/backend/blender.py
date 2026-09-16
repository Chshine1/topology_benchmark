from typing import override

from attrs import field, frozen

from topology_benchmark.core.errors import GenerationError
from topology_benchmark.core.problem.models import GenerationRequest, QuestionSection
from topology_benchmark.core.validation import nonblank, number_range
from topology_benchmark.domains.surfaces.abstractions import ISurfaceRenderBackend
from topology_benchmark.domains.surfaces.models import SurfacePresentation
from topology_benchmark.domains.surfaces.rendering.diagram_planner import DiagramPlan


class BlenderRenderingError(GenerationError):
    """Blender could not realize a configured surface scene."""


@frozen
class BlenderRuntimeConfig:
    executable: str = field(validator=nonblank("the Blender executable cannot be blank"))
    timeout_seconds: float = field(
        validator=number_range(minimum=0.001, message="the Blender timeout must be positive")
    )


class BlenderSurfaceRenderBackend(ISurfaceRenderBackend):
    def __init__(self, runtime: BlenderRuntimeConfig) -> None:
        self._runtime = runtime

    @override
    def render(
        self,
        surface: SurfacePresentation,
        plan: DiagramPlan,
        request: GenerationRequest,
    ) -> QuestionSection:
        raise NotImplementedError()
        # profile = plan.style.visual.profile
        # if not isinstance(profile, BlenderVisualStyleConfig):
        #     raise ValueError(f"the Blender backend cannot render {profile.backend!r} styles")
        # script = Path(__file__).with_name("blender_scene.py")
        # with tempfile.TemporaryDirectory(prefix="topology-benchmark-blender-") as directory:
        #     working_directory = Path(directory)
        #     scene_path = working_directory / "scene.json"
        #     output_path = working_directory / "render.png"
        #     scene_path.write_text(
        #         json.dumps(_scene_document(obj, plan, request)),
        #         encoding="utf-8",
        #     )
        #     command = (
        #         self._runtime.executable,
        #         "--background",
        #         "--factory-startup",
        #         "--python",
        #         str(script),
        #         "--",
        #         "--scene",
        #         str(scene_path),
        #         "--output",
        #         str(output_path),
        #     )
        #     try:
        #         completed = subprocess.run(
        #             command,
        #             capture_output=True,
        #             check=False,
        #             text=True,
        #             timeout=self._runtime.timeout_seconds,
        #         )
        #     except (OSError, subprocess.TimeoutExpired) as error:
        #         raise BlenderRenderingError(f"could not run Blender: {error}") from error
        #     if completed.returncode != 0 or not output_path.is_file():
        #         details = (completed.stderr or completed.stdout).strip()[-2000:]
        #         raise BlenderRenderingError(
        #             f"Blender exited with code {completed.returncode}: {details}"
        #         )
        #     return QuestionSection(
        #         "image/png",
        #         base64.b64encode(_canonical_png(output_path.read_bytes())).decode("ascii"),
        #     )


# def _scene_document(
#     surface: SurfacePresentation,
#     plan: DiagramPlan,
#     request: GenerationRequest,
# ) -> dict[str, object]:
#     return {
#         "seed": request.seed,
#         "width": plan.width,
#         "height": plan.height,
#         "style": plan.style.visual.profile.model_dump(mode="json"),
#         "palette": plan.style.visual.palette.model_dump(mode="json"),
#         "polygons": [
#             {"name": polygon.name, "vertices": layout.vertices}
#             for polygon, layout in zip(surface.polygons, plan.polygons, strict=True)
#         ],
#         "gluings": [
#             {
#                 "first": (gluing.first.polygon, gluing.first.edge),
#                 "second": (gluing.second.polygon, gluing.second.edge),
#                 "label": "",  # TODO: Missing
#                 "same_direction": gluing.same_direction,
#             }
#             for gluing in surface.gluings
#         ],
#         "paths": [
#             {
#                 "name": surface.paths[curve.segment.path_index].name,
#                 "order": curve.segment.order,
#                 "order_display": curve.style.order_display.value,
#                 "color": curve.style.color,
#                 "points": curve.points,
#                 "tag_position": curve.tag_position,
#                 "name_position": curve.name_position,
#             }
#             for curve in plan.curves
#         ],
#         "edge_labels": [
#             {"edge": (edge.polygon, edge.edge), "label": label}
#             for edge, label in surface.edge_labels
#         ],
#     }
#
#
# def _canonical_png(content: bytes) -> bytes:
#     signature = b"\x89PNG\r\n\x1a\n"
#     if not content.startswith(signature):
#         raise BlenderRenderingError("Blender did not produce a PNG image")
#     result = bytearray(signature)
#     offset = len(signature)
#     found_end = False
#     while offset + 12 <= len(content):
#         length = struct.unpack(">I", content[offset : offset + 4])[0]
#         chunk_end = offset + 12 + length
#         if chunk_end > len(content):
#             raise BlenderRenderingError("Blender produced a truncated PNG image")
#         chunk_type = content[offset + 4 : offset + 8]
#         if chunk_type not in {b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"}:
#             result.extend(content[offset:chunk_end])
#         offset = chunk_end
#         if chunk_type == b"IEND":
#             found_end = True
#             break
#     if not found_end:
#         raise BlenderRenderingError("Blender produced a PNG without an IEND chunk")
#     return bytes(result)
