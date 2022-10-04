#
#   Implementation of Streaming histogram calculation.
#   Ref: https://www.jmlr.org/papers/volume11/ben-haim10a/ben-haim10a.pdf
#
#

import bisect


class HistogramBucket(object):

    def __init__(self, centroid=None, count=None):
        self.centroid = centroid
        self.count = count

    def get_area(self):
        return self.centroid * self.count

    def combine(self, bucket):
        new_count = self.count + bucket.count
        self.centroid = (self.get_area() + bucket.get_area()) / new_count
        self.count = new_count

    def print(self):
        print("Centroid: {:10.4f} Count: {:5}".format(self.centroid, self.count))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.centroid == other.centroid and self.count == other.count


class StreamingHistogram(object):

    def __init__(self, max_buckets):
        if max_buckets <= 0:
            raise ValueError("Invalid number of buckets: {}".format(max_buckets))

        self.max_buckets = max_buckets
        # Sorted list of buckets, sorted based on centroid
        self.buckets = []
        # Because the bisect module does not support insertion based on key, we track the
        # centroids separately
        self._centroids = []

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.buckets == other.buckets

    @classmethod
    def build_from_list(cls, values, max_buckets):
        histogram = StreamingHistogram(max_buckets)
        histogram.push_list(values)
        return histogram

    def push_list(self, values):
        for value in values:
            self.push_value(value)

    def push_value(self, value):
        self.push_bucket(HistogramBucket(value, 1))

    def push_bucket(self, bucket):
        # Push the bucket in our sorted array
        #
        # bisect module does not support key argument in 3.7 yet
        # bisect.insort_left(self.buckets, bucket, key=lambda b: b.centroid)
        # So, lets find the centroid position in centroid list and use same in the buckets list
        pos = bisect.bisect_left(self._centroids, bucket.centroid)
        self._centroids.insert(pos, bucket.centroid)
        self.buckets.insert(pos, bucket)

        if len(self.buckets) > self.max_buckets:
            self.combine()

    def combine(self):
        if len(self.buckets) == 1:
            return
        # Find 2 buckets with the least gap between centroid values
        bucket_1 = self.buckets[0]
        bucket_2 = self.buckets[1]
        min_centroid_diff = bucket_2.centroid - bucket_1.centroid
        pair = (bucket_1, bucket_2)
        index_to_remove = 1
        for index in range(2, len(self.buckets)):
            bucket_1 = bucket_2
            bucket_2 = self.buckets[index]
            # Note buckets are sorted by centroids
            centroid_diff = bucket_2.centroid - bucket_1.centroid
            if centroid_diff < min_centroid_diff:
                pair = (bucket_1, bucket_2)
                index_to_remove = index

        # Now we found our pair, merge the 2nd one into first
        pair[0].combine(pair[1])
        self.buckets.pop(index_to_remove)
        self._centroids.pop(index_to_remove)

    def merge(self, histogram):
        """
        Merge 2 histograms
        :param histogram:
        :return:
        """
        for bucket in histogram.buckets:
            self.push_bucket(bucket)
            self.combine()

    def print(self):
        for bucket in self.buckets:
            bucket.print()

    def count_values(self):
        count = 0
        for bucket in self.buckets:
            count += bucket.count
        return count

