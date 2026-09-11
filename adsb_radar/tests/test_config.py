import importlib.util
import io
import json
from pathlib import Path
import tempfile
import sqlite3
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location("radar", Path(__file__).parents[1] / "run.py")
radar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radar)


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.options = dict(device_serial="", gain=-10, ppm=0,
                            vrs_username="admin", vrs_password="test password")

    def test_receiver_serial_and_internal_feed(self):
        radar.validate_options(self.options)
        command = radar.dump1090_command(self.options)
        self.assertEqual(command[command.index("--device") + 1], "0")
        self.assertEqual(command[command.index("--net-bind-address") + 1], "127.0.0.1")
        self.assertNotIn("--lat", command)

    def test_explicit_serial(self):
        self.options["device_serial"] = "example-serial"
        command = radar.dump1090_command(self.options)
        self.assertEqual(command[command.index("--device") + 1], "example-serial")

    def test_existing_user_is_reused_case_insensitively(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            database = folder / "Users.sqb"
            with sqlite3.connect(database) as connection:
                connection.execute('CREATE TABLE "User" (LoginName TEXT COLLATE NOCASE)')
                connection.execute('INSERT INTO "User" VALUES (?)', ('ADMIN',))
            before = database.read_bytes()
            self.assertEqual(radar.vrs_command(self.options, folder),
                             ['mono', '/opt/vrs/VirtualRadar.exe', '-nogui'])
            self.assertEqual(database.read_bytes(), before)
            command = radar.vrs_command(self.options | {"vrs_username": "another-user"}, folder)
            self.assertIn('-createAdmin:another-user', command)

    def test_first_run_and_uninitialised_database_create_user(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.assertIn('-createAdmin:admin', radar.vrs_command(self.options, folder))
            self.assertFalse((folder / 'Users.sqb').exists())
            with sqlite3.connect(folder / 'Users.sqb'):
                pass
            self.assertIn('-createAdmin:admin', radar.vrs_command(self.options, folder))

    def test_unreadable_database_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            database = folder / 'Users.sqb'
            database.write_bytes(b'not a sqlite database')
            with self.assertRaisesRegex(ValueError, 'Cannot read VRS user database'):
                radar.vrs_command(self.options, folder)
            self.assertEqual(database.read_bytes(), b'not a sqlite database')

    def test_home_assistant_location(self):
        with patch.dict(radar.os.environ, {"SUPERVISOR_TOKEN": "test-token"}), patch.object(
            radar.urllib.request, "urlopen",
            return_value=io.BytesIO(json.dumps({"latitude": 0, "longitude": -79.4}).encode())
        ) as request:
            options = radar.resolve_location(self.options)
        call = request.call_args
        self.assertEqual(call.args[0].full_url, "http://supervisor/core/api/config")
        self.assertEqual(call.args[0].get_header("Authorization"), "Bearer test-token")
        self.assertEqual(options["latitude"], 0)
        self.assertEqual(options["longitude"], -79.4)
        self.assertNotIn("latitude", self.options)
        command = radar.dump1090_command(options)
        self.assertEqual(command[command.index("--lat") + 1], "0")

    def test_manual_location_bypasses_api(self):
        self.options.update(latitude=43.6, longitude=-79.4)
        with patch.object(radar.urllib.request, "urlopen") as request:
            self.assertEqual(radar.resolve_location(self.options), self.options)
        request.assert_not_called()

    def test_location_retries_until_core_is_ready(self):
        with patch.dict(radar.os.environ, {"SUPERVISOR_TOKEN": "test-token"}), patch.object(
            radar.urllib.request, "urlopen", side_effect=[
                OSError("unavailable"), io.BytesIO(b'{"latitude": 42, "longitude": 3}')]
        ) as request, patch.object(radar.time, "sleep"):
            self.assertEqual(radar.resolve_location(self.options)["latitude"], 42)
        self.assertEqual(request.call_count, 2)

    def test_missing_token_and_invalid_location_fail_clearly(self):
        with patch.dict(radar.os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "SUPERVISOR_TOKEN"):
            radar.resolve_location(self.options)
        for payload in (b'{}', b'{"latitude": 100, "longitude": 0}', b'not json'):
            with self.subTest(payload=payload), patch.dict(radar.os.environ, {"SUPERVISOR_TOKEN": "test-token"}), patch.object(
                radar.urllib.request, "urlopen", side_effect=lambda *a, **k: io.BytesIO(payload)
            ) as request, patch.object(radar.time, "sleep"), self.assertRaisesRegex(ValueError, "Could not read"):
                radar.resolve_location(self.options)
            self.assertEqual(request.call_count, 3)

    def test_invalid_options(self):
        for change in ({"vrs_password": ""}, {"latitude": 42}, {"gain": -1},
                       {"gain": float("nan")}, {"ppm": 0.5}, {"ppm": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                radar.validate_options(self.options | change)

    def test_location_update_preserves_custom_settings_and_existing_location(self):
        self.options.update(latitude=43.6, longitude=-79.4)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Configuration.xml"
            path.write_text('''<Configuration><GoogleMapSettings><InitialMapZoom>7</InitialMapZoom>
                </GoogleMapSettings><Receivers><Receiver><UniqueId>1</UniqueId></Receiver></Receivers>
                <ReceiverLocations><ReceiverLocation><UniqueId>1</UniqueId><Name>Other</Name>
                </ReceiverLocation></ReceiverLocations><Custom>keep</Custom></Configuration>''')
            radar.configure_location(path, self.options)
            radar.configure_location(path, self.options)
            root = ET.parse(path).getroot()
            self.assertEqual(root.findtext("Custom"), "keep")
            self.assertEqual(root.findtext("GoogleMapSettings/InitialMapZoom"), "7")
            self.assertEqual(root.findtext("Receivers/Receiver/ReceiverLocationId"), "2")
            self.assertEqual(len(root.findall("ReceiverLocations/ReceiverLocation")), 2)
            self.assertEqual(root.findtext("GoogleMapSettings/InitialMapLatitude"), "43.6")


if __name__ == "__main__":
    unittest.main()
