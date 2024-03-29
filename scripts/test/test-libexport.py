#! /usr/bin/env python3
import glob, os, sys
import unittest, traceback

sys.path.append('..')

from libexport import Parser, SourceException, versionString

TESTDATA_DIR = "../../testdata"

_API_VERSIONS = [
  ("example_rpc.bp", -6803416483160598136),
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
      glob.glob(os.path.join(TESTDATA_DIR, "Demo*.bp"))
    )

  def test_testCoverage(self):
    for cl, data in self.all_data.items():
      if not data.is_enum:
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

if __name__ == '__main__':
    unittest.main()
