# Copyright 2017 Google Inc.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for filter_variants module."""

from __future__ import absolute_import

import unittest

from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that
from apache_beam.transforms import Create

from gcp_variant_transforms.beam_io import vcfio
from gcp_variant_transforms.testing import asserts
from gcp_variant_transforms.testing.testdata_util import hash_name
from gcp_variant_transforms.transforms import filter_variants


# A sample MalformedVcfRecord.
MALFORMED_RECORD = vcfio.MalformedVcfRecord('FILE', 'LINE', 'ERROR')


class FilterVariantsTest(unittest.TestCase):
  """Test cases for ``FilterVariants`` transform."""

  def setUp(self):
    self.variants = self._get_sample_variants()
    self.pipeline = TestPipeline()

  def _get_sample_variants(self):
    variant_1 = vcfio.Variant(
        reference_name='19', start=11, end=12, reference_bases='C',
        alternate_bases=['A', 'TT'], names=['rs1'], quality=2,
        filters=['PASS'],
        info={'A1': 'some data', 'A2': ['data1', 'data2']},
        calls=[
            vcfio.VariantCall(
                sample_id=hash_name('Sample1'), genotype=[0, 1], phaseset='*',
                info={'GQ': 20, 'HQ': [10, 20]}),
            vcfio.VariantCall(
                sample_id=hash_name('Sample2'), genotype=[1, 0],
                info={'GQ': 10, 'FLAG1': True}),
        ]
    )
    variant_2 = vcfio.Variant(
        reference_name='20', start=11, end=12, reference_bases='C',
        alternate_bases=['A', 'TT'], names=['rs1'], quality=20,
        filters=['q10'],
        info={'A1': 'some data2', 'A3': ['data3', 'data4']},
        calls=[
            vcfio.VariantCall(sample_id=hash_name('Sample3'), genotype=[1, 1]),
            vcfio.VariantCall(
                sample_id=hash_name('Sample4'), genotype=[1, 0],
                info={'GQ': 20}),
        ]
    )
    return [variant_1, variant_2]

  def _run_filter_pipeline(self, variants, expected, reference_names=None):
    filtered_variants = (
        self.pipeline
        | Create(variants)
        | 'FilterVariants' >> filter_variants.FilterVariants(
            reference_names=reference_names))
    assert_that(filtered_variants,
                asserts.variants_equal_to_ignore_order(expected))
    self.pipeline.run()

  def test_filter_all_valid(self):
    self._run_filter_pipeline(self.variants, self.variants)

  def test_filter_all_invalid(self):
    self._run_filter_pipeline([MALFORMED_RECORD, MALFORMED_RECORD], [])

  def test_filter_some_invalid(self):
    self._run_filter_pipeline(
        [MALFORMED_RECORD,
         self.variants[0],
         MALFORMED_RECORD,
         self.variants[1]],
        self.variants)

  def test_keep_reference_names(self):
    self._run_filter_pipeline(self.variants, [self.variants[0]], ['19'])

  def test_keep_all_if_empty_reference_names(self):
    self._run_filter_pipeline(self.variants, self.variants, [])

  def test_raises_error_for_unknown_type(self):
    with self.assertRaises(ValueError):
      self._run_filter_pipeline([None], [])
