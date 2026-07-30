"""Orchestration that spans several pipeline stages.

Services sit between the HTTP layer (``backend.routes``) and the domain layer
(``pipeline``). A service may import from ``backend.jobs``, ``backend.tasks``
and ``pipeline``; it must never import from ``backend.routes``.
"""
