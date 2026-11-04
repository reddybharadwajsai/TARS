"""Policy loader — finds and reads policy documents from the policies/ folder."""

import os
from formats import read_document, UnsupportedFormat


def load_policies(desk_root: str) -> list[dict]:
    """
    Load all policy files from the policies/ folder.
    Returns a list of {"filename": str, "content": str} dicts.
    Returns empty list if policies/ folder doesn't exist.
    """
    policy_dir = os.path.join(desk_root, "policies")

    if not os.path.isdir(policy_dir):
        return []

    policies = []
    for filename in sorted(os.listdir(policy_dir)):
        filepath = os.path.join(policy_dir, filename)
        if not os.path.isfile(filepath):
            continue

        try:
            content = read_document(filepath)
            policies.append({"filename": filename, "content": content})
        except UnsupportedFormat:
            continue

    return policies
