import datetime
import numpy as np
from utils.utils_H36M.visualise import Drawer


from sample.base.base_trainer import BaseTrainer
from tqdm import tqdm
import torch
import numpy.random as random
import matplotlib.pyplot as plt
from sample.config.encoder_decoder import ENCODER_DECODER_PARAMS
from dataset_def.trans_numpy_torch import NumpyToTensor




if ENCODER_DECODER_PARAMS.encoder_decoder.device_type == 'cpu':
    no_cuda=True
else:
    no_cuda=False
device = ENCODER_DECODER_PARAMS['encoder_decoder']['device']

class Trainer_Enc_Dec_Pose(BaseTrainer):
    """
    Trainer class, inherited from BaseTrainer
    """

    def __init__(self,
                 model,
                 loss,
                 metrics,
                 optimizer,
                 data_loader,
                 args,
                 data_test=None,
                 no_cuda = no_cuda,
                 eval_epoch = False
                 ):

        name=args.name
        output = args.output
        epochs = args.epochs
        save_freq = args.save_freq
        verbosity = args.verbosity
        verbosity_iter = args.verbosity_iter
        train_log_step = args.train_log_step


        super().__init__(model, loss, metrics, optimizer, epochs,
                 name, output, save_freq, no_cuda, verbosity,
                 train_log_step, verbosity_iter,eval_epoch)

        self.model.fix_encoder_decoder()


        self.data_loader = data_loader
        self.data_test = data_test

        #test while training
        self.test_log_step = None
        self.img_log_step = args.img_log_step
        if data_test is not None:
            self.test_log_step = self.train_log_step

        self.parameters_show = self.train_log_step * 300
        self.length_test_set = len(self.data_test)
        self.len_trainset = len(self.data_loader)
        self.drawer = Drawer()
        mean= self.data_loader.get_mean_pose()
        self.mean_pose = NumpyToTensor()(mean.reshape(1,17,3))
        std = self.data_loader.get_std_pose(mean).reshape(1,17,3)
        self.std_pose = NumpyToTensor()(std)
        # load model
        #self._resume_checkpoint(args.resume)



    def _summary_info(self):
        """Summary file to differentiate
         between all the different trainings
        """
        info = dict()
        info['creation'] = str(datetime.datetime.now())
        info['size_dataset'] = len(self.data_loader)
        string=""
        for number,contents in enumerate(self.data_loader.index_file_list):
            string += "\n content :" + self.data_loader.index_file_content[number]
            for elements in contents:
                string += "\n numbers: "
                string += " %s," % elements
        info['details'] = string
        info['optimiser']=str(self.optimizer)
        info['loss']=str(self.loss.__class__.__name__)
        return info


    def log_images(self,image_in, pose_out, ground_truth, string):

        for i in range(5):
            idx=np.random.randint(self.model.batch_size)
            pt=pose_out[idx]
            gt=ground_truth[idx]
            pt_cpu=pt.cpu().data.numpy()
            gt_cpu=gt.cpu().data.numpy()
            fig=plt.figure()
            fig = self.drawer.poses_3d(pt_cpu,gt_cpu,plot=True, fig=fig)
            if False:
                if string=='train':

                    img= image_in[idx].data.cpu().numpy().transpose(1,2,0)
                    plt.figure()
                    plt.imshow(img)
                    plt.show()
            self.model_logger.train.add_image(str(string)+str(i) + "Image", image_in[idx], self.global_step)
            self.model_logger.train.add_figure(str(string)+str(i) + "GT", fig, self.global_step)


    def log_gradients(self):

        gradients= np.sum(np.array([np.sum(np.absolute(x.grad.cpu().data.numpy())) for x in self.model.parameters()]))
        self.model_logger.train.add_scalar('Gradients', gradients,
                                           self.global_step)


    def log_metrics(self):
        pass

        # for metric in self.metrics:
        #    y_output = p3d.data.cpu().numpy()
        #    y_target = p3d_gt.data.cpu().numpy()
        #   metric.log(pred=y_output,
        #              gt=y_target,
        #              logger=self.model_logger.train,
        #              iteration=self.global_step)

    def log_3D_pose(self):
        pass

        # if (bid % self.img_log_step) == 0 and self.img_log_step > -1:
        #    y_output = p3d.data.cpu().numpy()
        #    y_target = p3d_gt.data.cpu().numpy()

        #    img_poses = self.drawer.poses_3d(y_output[0], y_target[0])
        #    img_poses = img_poses.transpose([2, 0, 1])
        #    self.model_logger.train.add_image('3d_poses',
        #                                      img_poses,
        #                                      self.global_step)


    def world_pose_to_camera(self,dic_in,dic_out):
        mean= torch.bmm( self.mean_pose.repeat(self.model.batch_size,1,1), dic_in['R_world_im'].transpose(1,2))
        gt = torch.bmm( dic_out['joints_im'], dic_in['R_world_im'].transpose(1,2))
        return gt, mean


    def train_step(self, bid, dic_in, dic_out, pbar, epoch):

        self.optimizer.zero_grad()
        out_pose_norm = self.model(dic_in)
        gt, mean = self.world_pose_to_camera(dic_in, dic_out)
        gt_norm = torch.div(gt-mean,self.std_pose)
        loss = self.loss( out_pose_norm, gt_norm)
        loss.backward()
        self.optimizer.step()
        self.model.eval()
        out_pose_norm = self.model(dic_in)
        self.model.train()
        if (bid % self.verbosity_iter == 0) and (self.verbosity == 2):
            pbar.set_description(' Epoch {} Loss {:.3f}'.format(
                epoch, loss.item()
            ))
        if bid % self.train_log_step == 0:
            val = loss.item()
            self.model_logger.train.add_scalar('loss/iterations', val,
                                               self.global_step)
            if bid % self.img_log_step:
                out_pose = torch.mul(out_pose_norm, self.std_pose) + mean
                self.log_images(dic_in['im_in'], out_pose, gt, 'train')
        return loss, pbar


    def test_step_on_random(self,bid):
        self.model.eval()
        idx = random.randint(self.length_test_set)
        in_test_dic, out_test_dic = self.data_test[idx]
        gt,mean = self.world_pose_to_camera(in_test_dic,  out_test_dic)
        out_pose_norm = self.model(in_test_dic)
        self.model.train()
        gt_norm = torch.div(gt - mean, self.std_pose)
        loss_test = self.loss(out_pose_norm, gt_norm)
        self.model_logger.val.add_scalar('loss/iterations', loss_test.item(),
                                         self.global_step)
        out_pose = torch.mul(out_pose_norm, self.std_pose) + mean
        self.log_images(in_test_dic['im_in'], out_pose, gt, 'test')


    def _train_epoch(self, epoch):
        """Train model for one epoch

        Arguments:
            epoch {int} -- epoch number

        Returns:
            float -- epoch error
        """

        self.model.train()
        if self.with_cuda:
            self.model.cuda()
        total_loss = 0
        pbar = tqdm(self.data_loader)

        for bid, (dic_in,dic_out) in enumerate(pbar):
            loss, pbar = self.train_step(bid, dic_in, dic_out, pbar, epoch)
            if self.test_log_step is not None and (bid % self.test_log_step == 0):
                self.test_step_on_random(bid)
            #if bid % self.parameters_show == 0:
                #self.log_gradients()
            if bid % self.save_freq == 0:
                if total_loss:
                    self._save_checkpoint(epoch, self.global_step,
                                          total_loss / bid)
                    self._update_summary(self.global_step,total_loss/bid,metrics=self.metrics)
            self.global_step += 1
            total_loss += loss.item()
        avg_loss = total_loss / len(self.data_loader)
        self.model_logger.train.add_scalar('loss/epochs', avg_loss, epoch)

        return avg_loss

    def _valid_epoch(self):
        """
        Validate after training an epoch

        :return: loss and metrics
        """
        pass



