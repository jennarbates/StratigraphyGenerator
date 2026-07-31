"""Seeded demonstrations of the pipeline, run from a record set on disk.

Two scenarios, because one of them is only meaningful next to the other:

  ``stops``      a trench whose survey record is missing one corner elevation.
                 Everything upstream of the build succeeds; the build refuses,
                 by name, on the wall that corner registers.
  ``complete``   the same trench and the same four wall drawings, with that one
                 number supplied. Merges, registers, converts, and hands off to
                 the model builder.

The pair is the point. They differ by a single value in a single file, and the
difference between them is a model and no model.

Nothing from ``seed`` is re-exported here. Binding its ``seed`` function as
``demo.seed`` would shadow the ``demo.seed`` *module*, so ``from demo import
seed`` would hand a caller the function or the module depending on import
order. Import the modules: ``from demo import seed``, then ``seed.seed(...)``.
"""

from .datasets import DemoDataset, discover

__all__ = ["DemoDataset", "discover"]
