#! /usr/bin/env python3
import glob, os, sys
import unittest

sys.path.append('..')

from libexport import Parser, SourceException, versionString

TESTDATA_DIR = "../../testdata"


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

  def test_versionString(self):
    self.maxDiff = None
    for cl, expected in self.versions.items():
      data = self.all_data[cl]
      vs = versionString(data, self.all_data, {}, {}, set())
      self.assertEqual(expected, vs)

  def test_intermediate_representation(self):
    self.maxDiff = None
    for cl, data in self.all_data.items():
        self.assertTrue(any(data.fields[0]), f"{cl} fields have empty leading data: {data.fields}")
        self.assertTrue(any(data.fields[-1]), f"{cl} fields have empty trailing data: {data.fields}")
        for inner, inner_data in data.inner.items():
            self.assertTrue(any(inner_data.fields[0]), f"{cl}.{inner} fields have empty leading data: {inner_data.fields}")
            self.assertTrue(any(inner_data.fields[-1]), f"{cl}.{inner} fields have empty trailing data: {inner_data.fields}")
        expected = self.intermediateRepresentation[data.name]
        self.assertEqual(expected, repr(data))

  def test_negatives(self):
    path = os.path.join(TESTDATA_DIR, "Negative*.bp")
    for filepath in glob.glob(path):
      with self.subTest(filename=filepath):
        p = Parser()
        annotations = {}
        with self.assertRaises(SourceException) as cm:
          data = p.parse([filepath], annotations=annotations)
        self.assertEqual(annotations['@what'], cm.exception.what)


if __name__ == '__main__':
    unittest.main()
