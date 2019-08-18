
from data.config import h36m_location
from utils.utils_H36M.common import H36M_CONF
import scipy.io as sio
import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import pickle as pkl





#######################################################################
#test data loadinf
#######################################################################
from dataset_def.h36m_preprocess import Data_Base_class
from utils.io import *
from utils.trans_numpy_torch import tensor_to_numpy,numpy_to_tensor
from data.config import backgrounds_location
#
#
d=Data_Base_class(sampling=1,index_as_dict=True)
d.create_index_file('s',[[1]])
print(d.index_file)
path=d.index_file[1][2][2][2][1]
#
path2=d.index_file[1][2][2][2][2]
sample_metadata=d.load_metadata(get_parent(path))
img=d.extract_image(path)
sample_metadata2=d.load_metadata(get_parent(path2))
img2=d.extract_image(path2)

print(np.sum(sample_metadata['joint_world']-sample_metadata2['joint_world']))
# plt.figure()
# plt.imshow(img)
# plt.figure()
# plt.imshow(img2)
# plt.show()
#print(sample_metadata['R'])
#print(sample_metadata2['R'])












#######################################################################
#test backgrounds
#######################################################################
from utils.utils_H36M.transformations import bounding_box_pixel
from utils.utils_H36M.visualise import Drawer


#m = pkl.load(open(os.path.join(backgrounds_location, "backgrounds.pkl"), "rb"))
#fig1=plt.figure()
#plt.imshow(m[0]-img)
#fig=plt.figure()
#mask=m[1]-img
#mask[mask<10**-1]=1
#mask[mask!=1]=0
#plt.imshow(mask)
#fig1=plt.figure()
#plt.imshow(img)
#print("L2 error",np.sqrt(np.sum((img-m[0])**2)))
#print("L2 error",np.sqrt(np.sum((img-m[1])**2)))

#plt.show()



#######################################################################
#test cropping
#######################################################################
from utils.utils_H36M.transformations import get_patch_image,transform_2d_joints
from utils.utils_H36M.transformations import world_to_pixel,world_to_camera
from utils.utils_H36M.transformations_torch import world_to_camera_batch, camera_to_pixels_batch, transform_2d_joints_batch

joints_world=sample_metadata['joint_world'][0].astype(np.float32)
joint_cam=world_to_camera(joints_world, 17, sample_metadata['R'].astype(np.float32), sample_metadata['T'].astype(np.float32))
joints_world_torch = numpy_to_tensor(joints_world.reshape(1,17,3))
R_torch = numpy_to_tensor(sample_metadata['R'].astype(np.float32).reshape(1,3,3))
T_torch =numpy_to_tensor(sample_metadata['T'].astype(np.float32).reshape(1,1,3))
f_torch = numpy_to_tensor(sample_metadata['f'].astype(np.float32).reshape(1,1,2))
c_torch =numpy_to_tensor(sample_metadata['c'].astype(np.float32).reshape(1,1,2))
joints_cam_torch = world_to_camera_batch(joints_world_torch,17,R_torch,T_torch)
joints_pix_torch = camera_to_pixels_batch(joints_cam_torch,17, f_torch, c_torch)


joint_px=world_to_pixel(
    joints_world,
    H36M_CONF.joints.number,
    sample_metadata['R'],
    sample_metadata['T'],
    sample_metadata['f'],
    sample_metadata['c']
)




bbpx_px=bounding_box_pixel(joints_world, 0, sample_metadata['R'], sample_metadata['T'], sample_metadata['f'], sample_metadata['c'])
imwarped,trans = get_patch_image(img, bbpx_px, (512,512), 0)#np.pi/4) # in degrees rotation around z axis
trans_torch = numpy_to_tensor(trans.reshape(1,2,3))
trsft_joints_torch = transform_2d_joints_batch(joints_pix_torch, trans_torch)
trsf_joints = transform_2d_joints(joint_px, trans)
trsft_joints_torch = tensor_to_numpy(trsft_joints_torch).reshape(17,2)


b=Drawer()
fig=plt.figure()
plt.imshow(imwarped)
plt.scatter(trsft_joints_torch[7,0],trsft_joints_torch[7,1])
#fig=b.pose_2d(imwarped,trsft_joints_torch, True, fig)
plt.show()





#######################################################################
#test rotation
#######################################################################

from utils.utils_H36M.transformations import cam_pointing_root
# new_rot = cam_pointing_root(joints_world,0,17,sample_metadata['R'], sample_metadata['T'])
# new_coords = joint_cam @ new_rot.T
# print("root in new coords",new_coords[0,:])

#######################################################################
#test data class
#######################################################################



# from utils.utils_H36M.preprocess import  Data_Base_class
# data=Data_Base_class()
# data.create_index_file('s',[1])
# data.save_index_file()
# data.load_index_file()
# for i in range(1000):
#     print(next(data))







