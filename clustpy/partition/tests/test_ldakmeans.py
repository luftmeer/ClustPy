import numpy as np
from clustpy.partition import LDAKmeans
from clustpy.data import load_wine

"""
Tests regarding the LDAKmeans object
"""


def test_simple_LDAKmeans_with_wine():
    X, labels = load_wine()
    ldakm = LDAKmeans(3, random_state=1)
    assert not hasattr(ldakm, "labels_")
    ldakm.fit(X)
    assert ldakm.labels_.dtype == np.int32
    assert ldakm.labels_.shape == labels.shape
    assert ldakm.cluster_centers_.shape == (ldakm.n_clusters, 2)
    # Test if random state is working
    ldakm2 = LDAKmeans(3, random_state=1)
    ldakm2.fit(X)
    assert np.array_equal(ldakm.labels_, ldakm2.labels_)
    assert np.array_equal(ldakm.cluster_centers_, ldakm2.cluster_centers_)
    assert np.array_equal(ldakm.rotation_, ldakm2.rotation_)
    # Test with parameters
    ldakm = LDAKmeans(3, n_dims=5, max_iter=10, kmeans_repetitions=5, random_state=1)
    ldakm.fit(X)
    assert ldakm.labels_.dtype == np.int32
    assert ldakm.labels_.shape == labels.shape
    assert ldakm.cluster_centers_.shape == (ldakm.n_clusters, 5)


def test_transform_subspace():
    X, labels = load_wine()
    X = X[:, :4]
    ldakm = LDAKmeans(3, n_dims=3, max_iter=10, kmeans_repetitions=1)
    ldakm.fit(X)
    # Overwrite rotation
    ldakm.rotation_ = np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0], [0, 0, 1]])
    X_transformed = ldakm.transform_subspace(X)
    assert np.array_equal(X_transformed, np.c_[X[:, 1], X[:, 0], X[:, 3]])
