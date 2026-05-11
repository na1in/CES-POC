"""Tests for analytics pure helpers (Phase 3)."""
import pytest

from app.routers.analytics import _BUCKETS, _compute_histogram, _confidence_bucket


class TestConfidenceBucket:
    def test_zero_is_first_bucket(self):
        assert _confidence_bucket(0) == "0-10"

    def test_nine_is_first_bucket(self):
        assert _confidence_bucket(9.9) == "0-10"

    def test_ten_is_second_bucket(self):
        assert _confidence_bucket(10) == "10-20"

    def test_fifty_is_mid_bucket(self):
        assert _confidence_bucket(50) == "50-60"

    def test_ninety_is_last_bucket(self):
        assert _confidence_bucket(90) == "90-100"

    def test_hundred_is_last_bucket(self):
        assert _confidence_bucket(100) == "90-100"

    def test_ninety_nine_is_last_bucket(self):
        assert _confidence_bucket(99.9) == "90-100"

    def test_boundary_values(self):
        for i in range(10):
            score = i * 10
            bucket = _confidence_bucket(score)
            assert bucket == f"{score}-{score + 10}"

    @pytest.mark.parametrize("score,expected", [
        (0,    "0-10"),
        (25,   "20-30"),
        (75,   "70-80"),
        (89.9, "80-90"),
        (90,   "90-100"),
        (100,  "90-100"),
    ])
    def test_parametrized_buckets(self, score, expected):
        assert _confidence_bucket(score) == expected


class TestComputeHistogram:
    def test_empty_returns_all_zeros(self):
        histogram = _compute_histogram([])
        assert all(v == 0 for v in histogram.values())
        assert len(histogram) == 10

    def test_all_buckets_present(self):
        histogram = _compute_histogram([])
        assert set(histogram.keys()) == set(_BUCKETS)

    def test_single_score_counted(self):
        histogram = _compute_histogram([55.0])
        assert histogram["50-60"] == 1
        assert sum(histogram.values()) == 1

    def test_none_values_ignored(self):
        histogram = _compute_histogram([None, 50.0, None])
        assert sum(histogram.values()) == 1

    def test_multiple_scores_in_same_bucket(self):
        histogram = _compute_histogram([10.0, 15.0, 19.9])
        assert histogram["10-20"] == 3

    def test_scores_spread_across_buckets(self):
        scores = [i * 10.0 for i in range(10)]  # 0, 10, 20, ..., 90
        histogram = _compute_histogram(scores)
        assert sum(histogram.values()) == 10
        for b in _BUCKETS:
            assert histogram[b] == 1

    def test_total_count_matches_input(self):
        scores = [10.0, 20.0, 30.0, 40.0, 50.0]
        histogram = _compute_histogram(scores)
        assert sum(histogram.values()) == 5

    def test_hundred_goes_to_last_bucket(self):
        histogram = _compute_histogram([100.0])
        assert histogram["90-100"] == 1

    def test_buckets_are_ordered(self):
        keys = list(_compute_histogram([]).keys())
        assert keys == _BUCKETS
