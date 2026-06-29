"""
Patch dependency graph engine.
Handles patch ordering and dependencies.
"""

from collections import defaultdict


class DependencyGraph:

    def __init__(self):

        self.graph = defaultdict(set)

    def add_dependency(
        self,
        source,
        target
    ):

        self.graph[source].add(target)

    def topological_sort(self):
        visited = set()
        stack = []

        def visit(node):
            if node in visited:
                return

            visited.add(node)

            # Use .get() to avoid adding keys to the defaultdict during iteration
            for neighbor in self.graph.get(node, set()):
                visit(neighbor)

            stack.append(node)

        # Iterate over a list of keys to avoid modification errors
        for node in list(self.graph.keys()):
            visit(node)

        stack.reverse()
        return stack

    def build_from_vulnerabilities(
        self,
        vulnerabilities
    ):

        vulnerabilities = sorted(
            vulnerabilities,
            key=lambda v: int(v.get("line", 0))
        )

        for i in range(len(vulnerabilities) - 1):

            current_vuln = vulnerabilities[i]
            next_vuln = vulnerabilities[i + 1]

            self.add_dependency(
                current_vuln["line"],
                next_vuln["line"]
            )

        return self.topological_sort()