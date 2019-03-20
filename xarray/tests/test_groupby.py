import numpy as np
import pandas as pd
import pytest

import xarray as xr
from xarray.core.groupby import _consolidate_slices

from . import assert_identical


def test_consolidate_slices():

    assert _consolidate_slices([slice(3), slice(3, 5)]) == [slice(5)]
    assert _consolidate_slices([slice(2, 3), slice(3, 6)]) == [slice(2, 6)]
    assert (_consolidate_slices([slice(2, 3, 1), slice(3, 6, 1)]) ==
            [slice(2, 6, 1)])

    slices = [slice(2, 3), slice(5, 6)]
    assert _consolidate_slices(slices) == slices

    with pytest.raises(ValueError):
        _consolidate_slices([slice(3), 4])


def test_multi_index_groupby_apply():
    # regression test for GH873
    ds = xr.Dataset({'foo': (('x', 'y'), np.random.randn(3, 4))},
                    {'x': ['a', 'b', 'c'], 'y': [1, 2, 3, 4]})
    doubled = 2 * ds
    group_doubled = (ds.stack(space=['x', 'y'])
                     .groupby('space')
                     .apply(lambda x: 2 * x)
                     .unstack('space'))
    assert doubled.equals(group_doubled)


def test_multi_index_groupby_sum():
    # regression test for GH873
    ds = xr.Dataset({'foo': (('x', 'y', 'z'), np.ones((3, 4, 2)))},
                    {'x': ['a', 'b', 'c'], 'y': [1, 2, 3, 4]})
    expected = ds.sum('z')
    actual = (ds.stack(space=['x', 'y'])
              .groupby('space')
              .sum('z')
              .unstack('space'))
    assert expected.equals(actual)


def test_groupby_da_datetime():
    # test groupby with a DataArray of dtype datetime for GH1132
    # create test data
    times = pd.date_range('2000-01-01', periods=4)
    foo = xr.DataArray([1, 2, 3, 4], coords=dict(time=times), dims='time')
    # create test index
    dd = times.to_pydatetime()
    reference_dates = [dd[0], dd[2]]
    labels = reference_dates[0:1] * 2 + reference_dates[1:2] * 2
    ind = xr.DataArray(labels, coords=dict(time=times), dims='time',
                       name='reference_date')
    g = foo.groupby(ind)
    actual = g.sum(dim='time')
    expected = xr.DataArray([3, 7],
                            coords=dict(reference_date=reference_dates),
                            dims='reference_date')
    assert actual.equals(expected)


def test_groupby_duplicate_coordinate_labels():
    # fix for http://stackoverflow.com/questions/38065129
    array = xr.DataArray([1, 2, 3], [('x', [1, 1, 2])])
    expected = xr.DataArray([3, 3], [('x', [1, 2])])
    actual = array.groupby('x').sum()
    assert expected.equals(actual)


def test_groupby_input_mutation():
    # regression test for GH2153
    array = xr.DataArray([1, 2, 3], [('x', [2, 2, 1])])
    array_copy = array.copy()
    expected = xr.DataArray([3, 3], [('x', [1, 2])])
    actual = array.groupby('x').sum()
    assert_identical(expected, actual)
    assert_identical(array, array_copy)  # should not modify inputs


def test_da_groupby_apply_func_args():

    def func(arg1, arg2, arg3=0):
        return arg1 + arg2 + arg3

    array = xr.DataArray([1, 1, 1], [('x', [1, 2, 3])])
    expected = xr.DataArray([3, 3, 3], [('x', [1, 2, 3])])
    actual = array.groupby('x').apply(func, args=(1,), arg3=1)
    assert_identical(expected, actual)


@pytest.mark.xfail
def test_da_groupby_single_value_per_dim():

    array = xr.DataArray([[1, 1, 1], [2, 2, 2]],
                         [('x', [1, 2]), ('y', [0, 1, 2])])

    # This raises an error.
    # I think the issue is that gr._group_indices is [0, 1]
    # instead of [[0,], [1,]]
    array.groupby('x').mean(dim='x')


def test_ds_groupby_apply_func_args():

    def func(arg1, arg2, arg3=0):
        return arg1 + arg2 + arg3

    dataset = xr.Dataset({'foo': ('x', [1, 1, 1])}, {'x': [1, 2, 3]})
    expected = xr.Dataset({'foo': ('x', [3, 3, 3])}, {'x': [1, 2, 3]})
    actual = dataset.groupby('x').apply(func, args=(1,), arg3=1)
    assert_identical(expected, actual)


def test_da_groupby_quantile():

    array = xr.DataArray([1, 2, 3, 4, 5, 6],
                         [('x', [1, 1, 1, 2, 2, 2])])

    # Scalar quantile
    expected = xr.DataArray([2, 5], [('x', [1, 2])])
    actual = array.groupby('x').quantile(.5)
    assert_identical(expected, actual)

    # Vector quantile
    expected = xr.DataArray([[1, 3], [4, 6]],
                            [('x', [1, 2]), ('quantile', [0, 1])])
    actual = array.groupby('x').quantile([0, 1])
    assert_identical(expected, actual)

    # Multiple dimensions
    array = xr.DataArray([[1, 11, 21], [2, 12, 22], [3, 13, 23],
                          [4, 16, 24], [5, 15, 25]],
                         [('x', [1, 1, 1, 2, 2],),
                          ('y', [0, 0, 1])])

    expected = xr.DataArray([[1, 11, 21], [4, 15, 24]],
                            [('x', [1, 2]), ('y', [0, 0, 1])])
    actual = array.groupby('x').quantile(0, dim='x')
    assert_identical(expected, actual)

    expected = xr.DataArray([[1, 21], [2, 22], [3, 23], [4, 24], [5, 25]],
                            [('x', [1, 1, 1, 2, 2]), ('y', [0, 1])])
    actual = array.groupby('y').quantile(0, dim='y')
    assert_identical(expected, actual)


# TODO: move other groupby tests from test_dataset and test_dataarray over here
