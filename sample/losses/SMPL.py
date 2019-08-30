import torch
from sample.base.base_metric import BaseMetric
import torch.nn
import numpy as np
from utils.conversion_SMPL_h36m_torch import Convert_joints
from sample.losses.poses import MPJ
from utils.trans_numpy_torch import numpy_to_tensor_float



class Masks_Loss(BaseMetric):
    def __init__(self, batch_size):
        super().__init__()
        self.batch_size = batch_size

    def create_tensors(self):
        indices = np.zeros((self.batch_size))
        total_loss = np.zeros((self.batch_size))
        indices= numpy_to_tensor_float(indices)
        total_loss = numpy_to_tensor_float(total_loss)
        return indices, total_loss

    def MSE_mask(self, pred, ground):
        squared = torch.pow(pred-ground, exponent=2)
        summed = torch.sum(torch.sum(squared, dim=2), dim=1)
        return summed


    def forward(self, mask_dic_in, mask_dic_out):

        n_masks, total_loss = self.create_tensors()
        for ca in range(1,5):
            index = mask_dic_in[ca]['idx']
            image_in = mask_dic_in[ca]['image']
            image_out = mask_dic_out[ca]['image']
            assert index.size()[0] == image_in.size()[0]
            total_loss[index] = total_loss[index] + self.MSE_mask(image_out, image_in)
            n_masks[index] = n_masks[index] + 1
        total_loss = torch.div(total_loss, n_masks)
        return torch.mean(total_loss)


class Pose_Loss(BaseMetric):
    def __init__(self):
        super().__init__()
        self.conversion = Convert_joints()
        self.pose_loss = MPJ()

    def forward(self, h36m_pose_ground, smpl_pose_pred ):

        smpl_joints, h36m_joints = self.conversion.match_joints(smpl_pose_pred, h36m_pose_ground, batch=True)
        return self.pose_loss( h36m_joints[:,1:,:], smpl_joints[:,1:,:])



class Loss_Pose_Zero(BaseMetric):
    def __init__(self):
        super().__init__()

    def forward(self, params):
        pose_params, shape_params = params
        squared = torch.pow((pose_params), exponent=2)
        squared2 = torch.pow((shape_params), exponent=2)

        return torch.mean(torch.sum(squared, dim=1)+torch.sum(squared2, dim=1))



class SMPL_Loss(BaseMetric):

    def __init__(self, batch_size):

        super().__init__()
        self.batch_size = batch_size
        self.masks_criterium = Masks_Loss(batch_size)
        self.pose_criterium = Pose_Loss()
        self.SMPL_init = Loss_Pose_Zero()

        self.w_p = 1/40. # roughly 2
        self.w_m = 10 # roughly 1
        self._logger.error("for 50 iter loss is 0")


    def forward(self, dic_in, dic_out, global_iter):

        loss_mask = self.masks_criterium(dic_in['masks'], dic_out['masks'])
        if global_iter < 50:
            loss_pose = self.SMPL_init(dic_out["SMPL_params"])
        else:
            loss_pose = self.pose_criterium(dic_in['joints_im'], dic_out['joints_im'])
        if global_iter < 100:
            total_loss = loss_pose * self.w_p
        else:
            total_loss = loss_mask * self.w_m + loss_pose * self.w_p
        return total_loss, loss_pose, loss_mask


        # im_loss 0.03 #pose loss 80