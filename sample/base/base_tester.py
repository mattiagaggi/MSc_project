# -*- coding: utf-8 -*-
"""
Base tester class to be extended

@author: Denis Tome'

"""
import os
import collections
import torch
from torch.autograd import Variable
import numpy as np
import utils.io as io
from utils import is_model_parallel
from base.template import FrameworkClass


class BaseTester(FrameworkClass):
    """
    Base class for all dataset testers
    """

    def __init__(self, model_op, model_ae, data_loader,
                 batch_size, output, name, no_cuda, **kwargs):

        super().__init__()

        self.model_op = model_op
        self.model_ae = model_ae
        self.data_loader = data_loader
        self.batch_size = batch_size
        self.output_name = name
        self.save_dir = io.abs_path(output)
        self.with_cuda = not no_cuda
        self.min_loss = np.inf
        self.single_gpu = True

        # check that we can run on GPU
        if not torch.cuda.is_available():
            self.with_cuda = False

        if self.with_cuda and (torch.cuda.device_count() > 1):
            self.model_op = torch.nn.DataParallel(self.model_op)
            if self.model_ae:
                self.model_ae = torch.nn.DataParallel(self.model_ae)
            self.single_gpu = False

        io.ensure_dir(os.path.join(self.save_dir,
                                   self.output_name))

    def _get_var(self, var):
        """Generate variable based on CUDA availability

        Arguments:
            var {undefined} -- variable to be converted

        Returns:
            tensor -- pytorch tensor
        """

        var = torch.FloatTensor(var)
        var = Variable(var)

        if self.with_cuda:
            var = var.cuda()

        return var

    def test(self):
        """Run test on the test-set"""
        raise NotImplementedError()

    def _resume_checkpoint(self, path):
        """Resume model specified by the path

        Arguments:
            path {str} -- path to directory containing the model
                                 or the model itself
        """

        if path == 'init':
            return

        # load model
        if not os.path.isfile(path):
            path = io.get_checkpoint(path)

        self._logger.info("Loading checkpoint: %s ...", path)
        if self.with_cuda:
            checkpoint = torch.load(path)
        else:
            checkpoint = torch.load(path, map_location='cpu')

        trained_dict = checkpoint['state_dict']
        if is_model_parallel(checkpoint):
            if self.single_gpu:
                trained_dict = collections.OrderedDict((k.replace('module.', ''), val)
                                                       for k, val in checkpoint['state_dict'].items())
        else:
            if not self.single_gpu:
                trained_dict = collections.OrderedDict(('module.{}'.format(k), val)
                                                       for k, val in checkpoint['state_dict'].items())

        self.model_ae.load_state_dict(trained_dict)
        self._logger.info("Checkpoint '%s' loaded", path)
