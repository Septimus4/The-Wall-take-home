"""Tests for API Gateway profiles app."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.profiles.models import SimulationRun, WallProfile
from apps.profiles.serializers import (
    WallProfileCreateSerializer,
    WallProfileSerializer,
)
from django.test import TestCase

from shared.wall_common.events import ProfileCreated


class WallProfileModelTest(TestCase):
    def test_create_wall_profile(self) -> None:
        profile = WallProfile.objects.create(
            name="Test Wall",
            height=Decimal("100"),
            length=Decimal("200"),
            width=Decimal("5"),
            ice_thickness=Decimal("2.5"),
        )

        self.assertEqual(profile.name, "Test Wall")
        self.assertEqual(profile.height, Decimal("100"))
        self.assertEqual(profile.length, Decimal("200"))
        self.assertEqual(profile.width, Decimal("5"))
        self.assertEqual(profile.ice_thickness, Decimal("2.5"))
        self.assertIsNotNone(profile.id)
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)

    def test_wall_profile_str(self) -> None:
        profile = WallProfile.objects.create(
            name="Great Wall",
            height=Decimal("150"),
            length=Decimal("300"),
            width=Decimal("10"),
            ice_thickness=Decimal("3"),
        )

        expected = "Great Wall (150x300x10ft)"
        self.assertEqual(str(profile), expected)

    def test_to_domain_profile(self) -> None:
        profile = WallProfile.objects.create(
            name="Domain Test",
            height=Decimal("50"),
            length=Decimal("100"),
            width=Decimal("3"),
            ice_thickness=Decimal("1.5"),
        )

        domain_profile = profile.to_domain_profile()

        self.assertEqual(domain_profile.name, "Domain Test")
        self.assertEqual(domain_profile.height, Decimal("50"))
        self.assertEqual(domain_profile.length, Decimal("100"))
        self.assertEqual(domain_profile.width, Decimal("3"))
        self.assertEqual(domain_profile.ice_thickness, Decimal("1.5"))


class SimulationRunModelTest(TestCase):
    def setUp(self) -> None:
        self.profile = WallProfile.objects.create(
            name="Test Wall",
            height=Decimal("100"),
            length=Decimal("200"),
            width=Decimal("5"),
            ice_thickness=Decimal("2"),
        )

    def test_create_simulation_run(self) -> None:
        simulation = SimulationRun.objects.create(profile=self.profile)

        self.assertEqual(simulation.profile, self.profile)
        self.assertEqual(simulation.days_simulated, 0)
        self.assertEqual(simulation.current_cumulative_cost, Decimal("0.00"))
        self.assertEqual(simulation.current_ice_volume, Decimal("0.00"))
        self.assertTrue(simulation.is_active)
        self.assertIsNotNone(simulation.id)
        self.assertIsNotNone(simulation.started_at)

    def test_simulation_run_str(self) -> None:
        simulation = SimulationRun.objects.create(
            profile=self.profile, days_simulated=5
        )

        expected = "Simulation for Test Wall - Day 5"
        self.assertEqual(str(simulation), expected)


class WallProfileSerializerTest(TestCase):
    def test_wall_profile_serializer_valid_data(self) -> None:
        data = {
            "name": "Test Wall",
            "height": "100.50",
            "length": "200.75",
            "width": "5.25",
            "ice_thickness": "2.5",
        }

        serializer = WallProfileSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        profile = serializer.save()
        self.assertEqual(profile.name, "Test Wall")
        self.assertEqual(profile.height, Decimal("100.50"))

    def test_wall_profile_serializer_invalid_data(self) -> None:
        data = {
            "name": "",
            "height": "-1",
            "length": "0",
            "width": "5",
            "ice_thickness": "2",
        }

        serializer = WallProfileSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)
        self.assertIn("height", serializer.errors)
        self.assertIn("length", serializer.errors)

    def test_wall_profile_create_serializer_validation(self) -> None:
        data = {
            "name": "Huge Wall",
            "height": "1000",
            "length": "1000",
            "width": "1000",
            "ice_thickness": "1",
        }
        serializer = WallProfileCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

        data = {
            "name": "Invalid Wall",
            "height": "10",
            "length": "10",
            "width": "1",
            "ice_thickness": "20",
        }
        serializer = WallProfileCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)


class KafkaPublisherTest(TestCase):
    @patch("apps.profiles.kafka_publisher.import_module")
    @patch("confluent_kafka.Producer")
    def test_publish_profile_created_event(
        self, mock_producer, mock_import_module
    ) -> None:
        from apps.profiles.kafka_publisher import KafkaEventPublisher

        # Mock the kafka module import
        mock_kafka_module = MagicMock()
        mock_kafka_module.Producer = mock_producer

        # Mock the schema registry module import
        mock_schema_module = MagicMock()
        mock_schema_registry_class = MagicMock()
        mock_schema_module.SchemaRegistryClient = mock_schema_registry_class

        def import_side_effect(module_name):
            if module_name == "confluent_kafka":
                return mock_kafka_module
            elif module_name == "confluent_kafka.schema_registry":
                return mock_schema_module
            else:
                raise ModuleNotFoundError(f"No module named '{module_name}'")

        mock_import_module.side_effect = import_side_effect

        mock_producer_instance = MagicMock()
        mock_producer.return_value = mock_producer_instance
        mock_schema_registry_instance = MagicMock()
        mock_schema_registry_class.return_value = mock_schema_registry_instance

        publisher = KafkaEventPublisher()

        event = ProfileCreated(
            event_id="test-id",
            timestamp=datetime.now(UTC),
            event_type="ProfileCreated",
            profile_id="profile-123",
            name="Test Wall",
            height=Decimal("100"),
            length=Decimal("200"),
            width=Decimal("5"),
            ice_thickness=Decimal("2"),
        )

        result = publisher.publish_profile_created(event)

        self.assertTrue(result)
        mock_producer_instance.produce.assert_called_once()
        mock_producer_instance.flush.assert_called_once()

    @patch("confluent_kafka.Producer")
    def test_publish_event_failure(self, mock_producer) -> None:
        from apps.profiles.kafka_publisher import KafkaEventPublisher

        mock_producer_instance = MagicMock()
        mock_producer_instance.produce.side_effect = Exception("Kafka error")
        mock_producer.return_value = mock_producer_instance

        publisher = KafkaEventPublisher()
        result = publisher.publish_event("test-topic", {"test": "data"})

        self.assertFalse(result)
