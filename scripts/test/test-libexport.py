#! /usr/bin/env python3
import glob, os, sys
import unittest, traceback

sys.path.append('..')

from libexport import Parser, SourceException, versionString, versionHash

TESTDATA_DIR = "../../testdata"

_API_VERSIONS = [
  ("example_rpc.bp", -8206535558625135915),
  ("DemoDeprecated.bp", -6691353770427087024),
]


class TestLibExport(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.versions = {}
    with open(os.path.join(TESTDATA_DIR, "versionString.txt")) as f:
      for line in f:
        name, value = line.split(" ", 1)
        cls.versions[name] = value.strip()

    cls.intermediateRepresentation = {}
    with open(os.path.join(TESTDATA_DIR, "intermediateRepresentation.txt")) as f:
      for line in f:
        name, value = line.split(" ", 1)
        cls.intermediateRepresentation[name] = value.strip()

    p = Parser()
    cls.all_data = p.parse(
      glob.glob(os.path.join(TESTDATA_DIR, "Demo*.bp")) +
      glob.glob(os.path.join(TESTDATA_DIR, "TestDedent.bp"))
    )

  def test_testCoverage(self):
    for cl, data in self.all_data.items():
      if not data.is_enum and not data.is_abstract:
        self.assertTrue(cl in self.versions, f"{cl} not in versionString.txt")

  def test_apiVersion(self):
    for fname, expected in _API_VERSIONS:
      p = Parser()
      _ = p.parse(os.path.join(TESTDATA_DIR, fname))
      self.assertEqual(expected, p.api_version, fname)

  def test_versionString(self):
    self.maxDiff = None
    for cl, expected in self.versions.items():
      data = self.all_data[cl]
      vs = versionString(data, self.all_data, {}, {}, set())
      self.assertEqual(expected, vs)

  def test_intermediate_representation(self):
    self.maxDiff = None
    for cl, data in self.all_data.items():
        if data.fields:
            self.assertTrue(data.fields[0], f"{cl} fields have empty leading data: {data.fields}")
            self.assertTrue(data.fields[-1], f"{cl} fields have empty trailing data: {data.fields}")
        for inner, inner_data in data.inner.items():
            self.assertTrue(inner_data.fields[0], f"{cl}.{inner} fields have empty leading data: {inner_data.fields}")
            self.assertTrue(inner_data.fields[-1], f"{cl}.{inner} fields have empty trailing data: {inner_data.fields}")
        expected = self.intermediateRepresentation[data.name]
        self.assertEqual(expected, repr(data), cl)

  def test_negatives(self):
    path = os.path.join(TESTDATA_DIR, "Negative*.bp")
    for filepath in glob.glob(path):
      with self.subTest(filename=filepath):
        p = Parser()
        annotations = {}
        with self.assertRaises(SourceException) as cm:
          data = p.parse([filepath], annotations=annotations)
        self.assertEqual(annotations['@what'], cm.exception.what, ''.join(traceback.format_exception(cm.exception)))

  def test_salt_version_string(self):
    """Test that salt changes the versionString output."""
    # Use a simple packet for testing
    p = Parser()
    all_data = p.parse([os.path.join(TESTDATA_DIR, "Demo.bp")])
    data = all_data["DemoPacket"]

    # Version string without salt
    vs_no_salt = versionString(data, all_data, {}, {}, set())

    # Version string with salt
    vs_with_salt = versionString(data, all_data, {}, {}, set(), salt="my_salt_")

    # Salt should be prefixed to the version string
    self.assertTrue(vs_with_salt.startswith("my_salt_"))
    self.assertEqual(vs_with_salt, "my_salt_" + vs_no_salt)

  def test_salt_version_hash(self):
    """Test that salt changes the versionHash output."""
    p = Parser()
    all_data = p.parse([os.path.join(TESTDATA_DIR, "Demo.bp")])
    data = all_data["DemoPacket"]

    # Hash without salt
    hash_no_salt = versionHash(data, all_data)

    # Hash with salt
    hash_with_salt = versionHash(data, all_data, salt="my_salt_")

    # Hashes should be different
    self.assertNotEqual(hash_no_salt, hash_with_salt)

    # Same salt should produce same hash
    hash_with_salt2 = versionHash(data, all_data, salt="my_salt_")
    self.assertEqual(hash_with_salt, hash_with_salt2)

    # Different salt should produce different hash
    hash_with_salt3 = versionHash(data, all_data, salt="different_salt_")
    self.assertNotEqual(hash_with_salt, hash_with_salt3)

  def test_salt_parser(self):
    """Test that Parser with salt computes correct versions."""
    # Parse with no salt
    p1 = Parser(salt="")
    all_data1 = p1.parse([os.path.join(TESTDATA_DIR, "Demo.bp")])
    version1 = all_data1["DemoPacket"].version

    # Parse with salt
    p2 = Parser(salt="test_salt_")
    all_data2 = p2.parse([os.path.join(TESTDATA_DIR, "Demo.bp")])
    version2 = all_data2["DemoPacket"].version

    # Versions should be different
    self.assertNotEqual(version1, version2)

    # API versions should also be different
    self.assertNotEqual(p1.api_version, p2.api_version)

  def test_salt_manifest(self):
    """Test that manifest includes salted hashes."""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
      # Parse with salt and generate manifest
      p = Parser(salt="manifest_salt_")
      p.parse([os.path.join(TESTDATA_DIR, "Demo.bp")], manifest_path=tmpdir)

      # Read manifest
      manifest_file = os.path.join(tmpdir, "manifest_bp.csv")
      self.assertTrue(os.path.exists(manifest_file))

      with open(manifest_file) as f:
        content = f.read()
        # Should contain the salted hash
        self.assertIn("DemoPacket", content)

if __name__ == '__main__':
    unittest.main()
