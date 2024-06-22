# A test on its own
import torch

# A test on its own
import deepcode


def test_cuda():
    assert (torch.cuda.is_available())