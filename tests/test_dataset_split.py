from scripts.split_dataset import split_items


def _items():
    return [
        {
            "id": f"q{i:03d}",
            "question": f"问题 {i}",
            "answerable": i % 4 != 0,
        }
        for i in range(1, 101)
    ]


def test_split_is_deterministic_and_disjoint():
    first = split_items(_items())
    second = split_items(_items())

    assert [item["id"] for item in first[0]] == [item["id"] for item in second[0]]
    assert [item["id"] for item in first[1]] == [item["id"] for item in second[1]]

    dev_ids = {item["id"] for item in first[0]}
    test_ids = {item["id"] for item in first[1]}
    assert not dev_ids & test_ids
    assert len(dev_ids | test_ids) == 100


def test_split_has_both_answerable_and_unanswerable_in_test():
    _, test = split_items(_items())

    assert any(item["answerable"] for item in test)
    assert any(not item["answerable"] for item in test)


def test_split_test_size_is_about_forty_percent():
    _, test = split_items(_items())

    assert 35 <= len(test) <= 45
