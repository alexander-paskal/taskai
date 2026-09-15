import os
import shutil

from taskai.json_dir_database import JsonDirectoryDatabase, DatabaseError, _is_chain_head


db = None


def _setup_db():
    global db
    db = JsonDirectoryDatabase(
        "_tmp_database_dir",
        "test_user",
        # debug=True
    )
    db.connect()


def _cleanup_db():
    if os.path.exists("_tmp_database_dir"):
        shutil.rmtree("_tmp_database_dir")


def _fresh():
    _cleanup_db()
    _setup_db()


# ---- insert_node_into_chain -------------------------------------------

def test_insert_builds_a_chain_with_exactly_one_head():
    _fresh()
    head = db.create_item(name="head")
    a = db.create_item(name="a")
    b = db.create_item(name="b")

    db.insert_node_into_chain(a, head)
    db.insert_node_into_chain(b, a)

    head_item, a_item, b_item = db.get_item(head), db.get_item(a), db.get_item(b)

    assert head_item.prev_chain_id is None
    assert head_item.next_chain_id == a
    assert a_item.prev_chain_id == head
    assert a_item.next_chain_id == b
    assert b_item.prev_chain_id == a
    assert b_item.next_chain_id is None

    assert _is_chain_head(head_item) is True
    assert _is_chain_head(a_item) is False
    assert _is_chain_head(b_item) is False


def test_insert_detaches_node_from_its_old_chain_first():
    _fresh()
    # two independent chains
    head1, a1, b1 = (db.create_item(name=n) for n in ("head1", "a1", "b1"))
    db.insert_node_into_chain(a1, head1)
    db.insert_node_into_chain(b1, a1)

    head2 = db.create_item(name="head2")

    # splice a1 (mid-chain in chain 1) into chain 2
    db.insert_node_into_chain(a1, head2)

    head1_item = db.get_item(head1)
    b1_item = db.get_item(b1)
    a1_item = db.get_item(a1)
    head2_item = db.get_item(head2)

    # chain 1 re-links around the hole
    assert head1_item.next_chain_id == b1
    assert b1_item.prev_chain_id == head1

    # a1 cleanly joined chain 2, no stale pointers left over
    assert a1_item.prev_chain_id == head2
    assert a1_item.next_chain_id is None
    assert head2_item.next_chain_id == a1
    assert _is_chain_head(head2_item) is True


def test_insert_pops_node_off_its_tree_parent():
    _fresh()
    parent = db.create_item(name="parent")
    child = db.create_item(name="child", parent_id=parent)
    head = db.create_item(name="head")

    assert child in db.get_item(parent).child_ids

    db.insert_node_into_chain(child, head)

    parent_item = db.get_item(parent)
    child_item = db.get_item(child)
    assert child not in parent_item.child_ids
    assert child_item.parent_id is None
    assert child_item.prev_chain_id == head


def test_insert_into_middle_of_existing_chain():
    _fresh()
    head = db.create_item(name="head")
    tail = db.create_item(name="tail")
    db.insert_node_into_chain(tail, head)

    mid = db.create_item(name="mid")
    db.insert_node_into_chain(mid, head)  # insert right after head, before tail

    head_item, mid_item, tail_item = db.get_item(head), db.get_item(mid), db.get_item(tail)
    assert head_item.next_chain_id == mid
    assert mid_item.prev_chain_id == head
    assert mid_item.next_chain_id == tail
    assert tail_item.prev_chain_id == mid


# ---- remove_node_from_chain --------------------------------------------

def test_remove_middle_link_relinks_neighbors():
    _fresh()
    head, a, b, c = (db.create_item(name=n) for n in ("head", "a", "b", "c"))
    db.insert_node_into_chain(a, head)
    db.insert_node_into_chain(b, a)
    db.insert_node_into_chain(c, b)

    db.remove_node_from_chain(b)

    a_item, b_item, c_item = db.get_item(a), db.get_item(b), db.get_item(c)
    assert a_item.next_chain_id == c
    assert c_item.prev_chain_id == a
    assert b_item.prev_chain_id is None
    assert b_item.next_chain_id is None


def test_remove_tail_shortens_chain():
    _fresh()
    head, a, b = (db.create_item(name=n) for n in ("head", "a", "b"))
    db.insert_node_into_chain(a, head)
    db.insert_node_into_chain(b, a)

    db.remove_node_from_chain(b)

    a_item = db.get_item(a)
    assert a_item.next_chain_id is None
    assert a_item.prev_chain_id == head  # untouched


def test_remove_node_from_chain_on_head_promotes_next_as_a_new_sibling():
    """remove_node_from_chain alone doesn't delete `node` - that's
    delete_item's job (it calls remove_child_from_parent first). Called
    standalone (what `unchain` does), the old head legitimately stays put;
    the promoted next link becomes a *new* sibling under the same parent,
    since the chain it heads was reachable through the old head before."""
    _fresh()
    parent = db.create_item(name="parent")
    head = db.create_item(name="head", parent_id=parent)
    a = db.create_item(name="a")
    b = db.create_item(name="b")
    db.insert_node_into_chain(a, head)
    db.insert_node_into_chain(b, a)

    db.remove_node_from_chain(head)

    a_item = db.get_item(a)
    parent_item = db.get_item(parent)

    assert a_item.prev_chain_id is None
    assert a_item.next_chain_id == b
    assert _is_chain_head(a_item) is True
    assert a_item.parent_id == parent
    assert a in parent_item.child_ids
    assert head in parent_item.child_ids  # unchanged - remove_node_from_chain never touches it


def test_delete_chain_head_reattaches_next_and_detaches_old_head():
    """Regression test for the actual bug: deleting a chain's head (via
    delete_item, not a raw remove_node_from_chain call) used to leave the
    rest of the chain unreachable - the parent's child_ids still pointed at
    the deleted head's id, and the promoted node's parent_id alone didn't
    fix that (see PHASE_1_RELEASE.md's "Deleting a chain head orphans the
    rest of the chain"). delete_item removes the old head from child_ids
    itself (before remove_node_from_chain runs), so this is where the "is
    the old head really gone, and is the new head really there instead"
    check belongs."""
    _fresh()
    parent = db.create_item(name="parent")
    head = db.create_item(name="head", parent_id=parent)
    a = db.create_item(name="a")
    b = db.create_item(name="b")
    db.insert_node_into_chain(a, head)
    db.insert_node_into_chain(b, a)

    db.delete_item(head)

    a_item = db.get_item(a)
    parent_item = db.get_item(parent)

    assert a_item.prev_chain_id is None
    assert a_item.next_chain_id == b
    assert _is_chain_head(a_item) is True
    assert a_item.parent_id == parent
    assert a in parent_item.child_ids
    assert head not in parent_item.child_ids  # the critical part of the regression


def test_remove_head_of_length_two_chain_collapses_cleanly():
    _fresh()
    parent = db.create_item(name="parent")
    head = db.create_item(name="head", parent_id=parent)
    tail = db.create_item(name="tail")
    db.insert_node_into_chain(tail, head)

    db.delete_item(head)

    tail_item = db.get_item(tail)
    parent_item = db.get_item(parent)
    # tail is now a solo item - not really "a chain" anymore (no next either)
    assert tail_item.prev_chain_id is None
    assert tail_item.next_chain_id is None
    assert _is_chain_head(tail_item) is False
    assert tail in parent_item.child_ids
    assert head not in parent_item.child_ids


# ---- delete_chain / delete_item interplay ------------------------------

def test_delete_chain_removes_every_link_and_detaches_parent():
    _fresh()
    parent = db.create_item(name="parent")
    head = db.create_item(name="head", parent_id=parent)
    a = db.create_item(name="a")
    b = db.create_item(name="b")
    db.insert_node_into_chain(a, head)
    db.insert_node_into_chain(b, a)

    db.delete_chain(head)

    for item_id in (head, a, b):
        try:
            db.get_item(item_id)
            assert False, f"item {item_id} should have been deleted"
        except DatabaseError:
            pass

    assert head not in db.get_item(parent).child_ids


def test_delete_item_on_parent_cascades_through_a_chain_child():
    """A real (child_ids) child that's a chain head takes its whole chain
    with it when the parent is deleted, not just itself."""
    _fresh()
    parent = db.create_item(name="parent")
    plain_child = db.create_item(name="plain_child", parent_id=parent)
    head = db.create_item(name="head", parent_id=parent)
    a = db.create_item(name="a")
    db.insert_node_into_chain(a, head)

    db.delete_item(parent)

    for item_id in (parent, plain_child, head, a):
        try:
            db.get_item(item_id)
            assert False, f"item {item_id} should have been deleted"
        except DatabaseError:
            pass


def test_delete_single_item_in_middle_of_chain_acts_like_a_linked_list():
    """Deleting one link directly (not via delete_chain) should splice it
    out and relink its neighbors, same as remove_node_from_chain alone."""
    _fresh()
    parent = db.create_item(name="parent")
    head = db.create_item(name="head", parent_id=parent)
    a = db.create_item(name="a")
    b = db.create_item(name="b")
    db.insert_node_into_chain(a, head)
    db.insert_node_into_chain(b, a)

    db.delete_item(a)

    try:
        db.get_item(a)
        assert False, "a should have been deleted"
    except DatabaseError:
        pass

    head_item, b_item = db.get_item(head), db.get_item(b)
    assert head_item.next_chain_id == b
    assert b_item.prev_chain_id == head


if __name__ == "__main__":
    tests = [
        test_insert_builds_a_chain_with_exactly_one_head,
        test_insert_detaches_node_from_its_old_chain_first,
        test_insert_pops_node_off_its_tree_parent,
        test_insert_into_middle_of_existing_chain,
        test_remove_middle_link_relinks_neighbors,
        test_remove_tail_shortens_chain,
        test_remove_node_from_chain_on_head_promotes_next_as_a_new_sibling,
        test_delete_chain_head_reattaches_next_and_detaches_old_head,
        test_remove_head_of_length_two_chain_collapses_cleanly,
        test_delete_chain_removes_every_link_and_detaches_parent,
        test_delete_item_on_parent_cascades_through_a_chain_child,
        test_delete_single_item_in_middle_of_chain_acts_like_a_linked_list,
    ]
    try:
        for t in tests:
            t()
            print(f"OK: {t.__name__}")
    finally:
        _cleanup_db()
