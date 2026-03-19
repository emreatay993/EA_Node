from __future__ import annotations

import unittest

from tests.serializer.round_trip_cases import SerializerRoundTripMixin
from tests.serializer.schema_cases import SerializerSchemaMixin
from tests.serializer.workflow_cases import SerializerWorkflowMixin


class SerializerTests(SerializerRoundTripMixin, SerializerWorkflowMixin, SerializerSchemaMixin, unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
