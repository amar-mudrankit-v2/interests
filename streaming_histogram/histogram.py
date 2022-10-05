#
#   Implementation of Streaming histogram calculation.
#   Ref: https://www.jmlr.org/papers/volume11/ben-haim10a/ben-haim10a.pdf
#
#

import bisect

import numpy as np


class HistogramBucket(object):

    # Saves a lot of memory
    __slots__ = ("centroid", "count")

    def __init__(self, centroid=None, count=0):
        self.centroid = float(centroid)
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
        self._min = float('inf')
        self._max = float('-inf')
        self._count = 0

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.buckets == other.buckets

    @staticmethod
    def build_from_list(values, max_buckets):
        histogram = StreamingHistogram(max_buckets)
        histogram.push_list(values)
        return histogram

    def push_list(self, values):
        for value in values:
            self.push_value(value)

    def push_value(self, value):
        pos = bisect.bisect_left(self._centroids, value)
        if pos < len(self.buckets) and self._centroids[pos] == value:
            self.buckets[pos].count += 1
            self._count += 1
        else:
            self.push_bucket(HistogramBucket(value, 1))
        if value < self._min:
            self._min = value
        if value > self._max:
            self._max = value

    def push_bucket(self, bucket):
        # Push the bucket in our sorted array
        #
        # bisect module does not support key argument in 3.7 yet
        # bisect.insort_left(self.buckets, bucket, key=lambda b: b.centroid)
        # So, lets find the centroid position in centroid list and use same in the buckets list
        self._count += bucket.count
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
        self._centroids[index_to_remove - 1] = pair[0].centroid

    def is_sorted(self):
        return all(self.buckets[i].centroid <= self.buckets[i + 1].centroid for i in range(len(self.buckets) - 1))

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

    def get_frequencies(self):
        return [bucket.count for bucket in self.buckets]

    def plot(self):
        import matplotlib.pyplot as plt
        plt.hist(x=self._centroids, weights=self.get_frequencies())
        plt.show()

    def count(self):
        return self._count

    def mean(self):
        area = 0
        items = 0
        for bucket in self.buckets:
            area += bucket.get_area()
            items += bucket.count
        return float(area/items)

    def reshape(self, input_histogram):
        """
        Reshape "this" histogram with the shape same as input histogram.  Essentially, ensure that the bins / centroids
        of this are same as the input histogram and reshuffle the counts so that they fit in the new bin structure

        Why? Basically to be able to compare 2 histograms using PSI or other metric.  If 2 histograms don't have same
        bin structure we can't compare them.

        How?
        1. Copy the buckets / centroids of the input histogram with counts = 0
        2. The algorithm assumes that for a (centroid, count) bin, there are "count" points surroundiing "centroid", of
           which "count / 2" points are to the left of the centroid and "count / 2" points to the right.  Imagine 2
           consecutive bins (centroid1, count1) and (centroid2, count2).  The number of points between centroid1 and
           centroid2 = (count1/2 + count2/2) = (count1 + count2) / 2.
        3. Eventually the actual bins become [-inf, centroid1, centroid2, centroid3, +inf].  Suppose we want to place
           the bucket (centroid_x, count_x) into this [-inf, centroid1, centroid2, centroid3, +inf] bin structure.
           We find out pair such that centroid1 <= centroid_x <= centroid2.  Once we find such pair, we add count_x
           to centroid1 if (centroid_x - centroid1) < (centroid2 - centroid_x), otherwise into centroid2.
        :param histogram:
        :return:
        """
        # These are going to be new buckets for "this" histogram
        new_buckets = list()
        # First entry in bucket range will be negative infinity
        bucket_ranges = [float('-inf')]
        for bucket in input_histogram.buckets:
            # For all new buckets, the centroids are going to be of those of input histogram, with count = 0
            new_buckets.append(HistogramBucket(bucket.centroid, 0))
            # Then all intermediate entries in the bucket range will be the centroids of input histogram
            bucket_ranges.append(bucket.centroid)

        # And final entry will be positive infinity
        bucket_ranges.append(float('inf'))

        # Now start scanning the buckets of "this" histogram
        for this_histogram_bucket in self.buckets:
            # Find out, in which bucket range, current bucket of "this" histogram falls into.  bisect_right will give
            # us the next index
            # -1 because bucket_ranges has extra boundaries with +/- infinity
            bucket_index = bisect.bisect_right(bucket_ranges, this_histogram_bucket.centroid) - 1
            if bucket_index == 0:
                # If it falls between negative infinity and the first centroid, then we copy all the counts
                # to the bucket at 0th index
                new_buckets[0].count += this_histogram_bucket.count
            elif bucket_index == len(new_buckets):
                # If it falls between the last bucket and positive infinity, then we copy all the counts to the
                # last bucket
                new_buckets[-1].count += this_histogram_bucket.count
            else:
                # Find out which bucket this centroid is closer to and add counts to that bucket
                diff_prev = abs(this_histogram_bucket.centroid - new_buckets[bucket_index - 1].centroid)
                diff_next = abs(new_buckets[bucket_index].centroid - this_histogram_bucket.centroid)
                if diff_prev < diff_next:
                    new_buckets[bucket_index - 1].count += this_histogram_bucket.count
                else:
                    new_buckets[bucket_index].count += this_histogram_bucket.count

        # Set new buckets for "this" histogram
        self.buckets = new_buckets
        # and centroids
        self._centroids = [bucket.centroid for bucket in self.buckets]

    def clone(self):
        """
        Clone "this" histogram and return
        :return:
        """
        clone = StreamingHistogram(len(self.buckets))
        for bucket in self.buckets:
            clone.push_bucket(bucket)

        return clone

    def centroids_matching(self, input_histogram):
        for index, bucket in enumerate(self.buckets):
            if bucket.centroid != input_histogram.buckets[index].centroid:
                return False
        return True

    def get_total_count(self):
        return self._count

    def compare_using_psi(self, input_histogram):
        reshape_required = False
        if len(self.buckets) != len(input_histogram.buckets):
            reshape_required = True
        elif not self.centroids_matching(input_histogram):
            reshape_required = True

        if reshape_required:
            compare = input_histogram.clone()
            compare.reshape(self)
        else:
            compare = input_histogram

        psi_sum = 0
        total_reference_count = self.get_total_count()
        total_compare_count = compare.get_total_count()
        for reference_bucket, compare_bucket in zip(self.buckets, compare.buckets):
            reference_pct = reference_bucket.count / float(total_reference_count)
            compare_pct = compare_bucket.count / float(total_compare_count)
            if reference_pct == 0 or compare_pct == 0:
                continue
            psi = (compare_pct - reference_pct) * np.log(compare_pct/reference_pct)
            psi_sum += psi

        return psi_sum




