import random
from histogram import StreamingHistogram


def add_values_to_histogram(count, max_buckets):
    n = count
    histogram = StreamingHistogram(max_buckets=max_buckets)
    for _ in range(n):
        histogram.push_value(random.uniform(-32767.0, 32768.0))

    assert histogram.count() == n
    return histogram


def test_basic_histogram():
    histogram = add_values_to_histogram(100000, 15)
    histogram.print()
    print(histogram.mean())


def test_merge_histogram():
    histogram1 = add_values_to_histogram(1000, 10)
    histogram2 = add_values_to_histogram(10000, 10)
    histogram1.merge(histogram2)
    histogram1.print()
    assert histogram1.count() == 11000


def test_list_histogram():
    values = [random.uniform(-32767.0, 32768.0) for _ in range(1000)]
    stream_histogram = StreamingHistogram(max_buckets=10)
    for val in values:
        stream_histogram.push_value(val)
    list_histogram = StreamingHistogram(max_buckets=10)
    list_histogram.push_list(values)

    stream_histogram.print()
    list_histogram.print()

    assert stream_histogram == list_histogram


def test_same_value():
    values = [random.uniform(-32767.0, 32768.0) for _ in range(1000)]
    stream_histogram = StreamingHistogram(max_buckets=10)
    stream_histogram.push_list(values)
    stream_histogram.push_list(values)
    stream_histogram.print()
    assert stream_histogram.count() == 2000
