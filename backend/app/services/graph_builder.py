"""Build the catalog graph from parsed courses and their prerequisite trees."""

from collections.abc import Iterator

from app.models import Course, CourseGraph, Edge, Node, PrereqGroup


def _prerequisite_codes(group: PrereqGroup) -> Iterator[str]:
    for item in group.items:
        if isinstance(item, PrereqGroup):
            yield from _prerequisite_codes(item)
        else:
            yield item


def build_course_graph(courses: list[Course]) -> CourseGraph:
    nodes: dict[str, Node] = {}
    for course in courses:
        # A bulletin can repeat a course under several headings. Keep its
        # first listing in source order.
        if course.code not in nodes:
            nodes[course.code] = Node(code=course.code, data=course)

    links: set[tuple[str, str]] = set()
    for node in list(nodes.values()):
        if node.data is None or node.data.pre_req is None:
            continue

        for code in _prerequisite_codes(node.data.pre_req):
            if code not in nodes:
                nodes[code] = Node(code=code, is_external=True)
            links.add((code, node.code))

    return CourseGraph(
        nodes=[nodes[code] for code in sorted(nodes)],
        edges=[
            Edge(source=source, target=target, line_style="solid")
            for source, target in sorted(links)
        ],
    )
