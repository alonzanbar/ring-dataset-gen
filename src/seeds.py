"""Deterministic seed generation for reproducible sampling."""

import hashlib


def stable_hash(*args) -> int:
    """
    Generate a stable integer hash from multiple arguments.
    
    Args:
        *args: Variable number of arguments to hash
        
    Returns:
        Integer hash value suitable for seeding RNGs
    """
    combined = "_".join(str(arg) for arg in args)
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    # Use first 8 bytes to create a 64-bit integer
    return int.from_bytes(hash_bytes[:8], byteorder='big')


def get_sample_seed(base_seed: int, split_name: str, sample_idx: int) -> int:
    """
    Compute deterministic sample seed from base seed, split, and index.
    
    Args:
        base_seed: Base seed for the entire dataset
        split_name: Name of the split (train/val/test)
        sample_idx: Index of the sample within the split
        
    Returns:
        Deterministic seed for this specific sample
    """
    return stable_hash(base_seed, split_name, sample_idx)

