from datetime import datetime

import pytest

from app.seed import NonexistentLocalTimeError, to_berlin


def test_local_time_skipped_by_the_spring_clock_change_is_rejected():
    with pytest.raises(NonexistentLocalTimeError):
        to_berlin(datetime(2027, 3, 28, 2, 30), second_occurrence=False)
