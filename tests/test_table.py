import pytest

from prdtools.table import (
    TableParameters, TableResult, ValidationError,
)

VALID_PARAMETERS = (
    dict(
        prime_num=157,
        prime_root=5,
        ncols=13,
        nrows=12,
        design_freq=500,
    ),
    dict(
        prime_num=241,
        prime_root=7,
        ncols=16,
        nrows=15,
        design_freq=500,
    ),
    dict(
        prime_num=349,
        prime_root=13,
        ncols=29,
        nrows=12,
        design_freq=1500,
    ),
)
INVALID_PARAMETERS = (
    dict(
        prime_num=157,
        prime_root=[2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 14],
        ncols=13,
        nrows=12,
        design_freq=500,
        error_fields=('prime_root',),
        error_msg='is not a primitive root'
    ),
    dict(
        prime_num=153,
        prime_root=3,
        ncols=17,
        nrows=9,
        design_freq=500,
        error_fields=('prime_num',),
        error_msg='Not a prime',
    ),
    dict(
        prime_num=241,
        prime_root=7,
        ncols=24,
        nrows=10,
        design_freq=500,
        error_fields=('ncols', 'nrows'),
        error_msg='must be coprime',
    ),
    dict(
        prime_num=349,
        prime_root=13,
        ncols=29,
        nrows=11,
        design_freq=1500,
        error_fields=('ncols', 'nrows'),
        error_msg='must equal prime_num-1',
    )
)

def test_validation():
    for valid_kw in VALID_PARAMETERS:
        parameters = TableParameters(**valid_kw)
        parameters.validate()

    for data in INVALID_PARAMETERS:
        error_fields = data.pop('error_fields')
        error_msg = data.pop('error_msg')
        if isinstance(data['prime_root'], list):
            invalid_kw_list = []
            for pr in data['prime_root']:
                d = data.copy()
                d['prime_root'] = pr
                invalid_kw_list.append(d)
        else:
            invalid_kw_list = [data]
        for invalid_kw in invalid_kw_list:
            parameters = TableParameters(**invalid_kw)
            with pytest.raises(ValidationError) as exc_info:
                parameters.validate()
            field_str, msg_str = str(exc_info.value).split(':')
            assert error_msg in msg_str
            for field_name in error_fields:
                assert field_name in field_str
