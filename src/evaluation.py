# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from src import dataset_loader
from src.math_equivalence import is_equiv

def convert_to_set(item):
    if isinstance(item, list):
        return set(item)
    if isinstance(item, str):
        return {item}
    if item is None:
        return {}
    raise ValueError("Input can't parse:", item)


def evaluate_single_sample(dataset_name, prediction, label):
    if dataset_name in dataset_loader.multi_choice_datasets:
        p = convert_to_set(prediction)
        l = convert_to_set(label)
        return p == l
    elif dataset_name in dataset_loader.math_output_datasets:
        return is_equiv(prediction, label)
    else:
        return prediction == label


