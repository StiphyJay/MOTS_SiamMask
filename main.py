import os
import sys
SiamMaskPath = os.path.join(os.getcwd(), 'SiamMask')
sys.path.append(SiamMaskPath)
MaskRCNNPath = os.path.join(os.getcwd(), 'MaskRCNN')
sys.path.append(MaskRCNNPath)

import cv2
import skimage.io
import numpy as np


# Issue: 同时导入时会出bug
import singletracker
import detector


class Tracklet(object):
    def __init__(self, target_id, target_pos, target_sz, target_mask, target_score, examplar_feature):
        self.target_id = target_id
        self.examplar_feature = examplar_feature

        self.target_pos = target_pos
        self.target_sz = target_sz
        self.target_mask = target_mask
        self.target_score = target_score
    
    def update_state(self, target_pos, target_sz, target_mask, target_score):
        self.target_pos = target_pos
        self.target_sz = target_sz
        self.target_mask = target_mask
        self.target_score = target_score





if __name__ == '__main__':

    
    ## Single object tracker Siammask
    ## Defined in SiamMask/singletracker.py
    vot_model_path = 'SiamMask/pretrained/SiamMask_VOT.pth'
    vot_config_path = 'SiamMask/config/config_vot.json'
    mytracker = singletracker.SingleTracker(vot_config_path, vot_model_path)
    

    
    ## Bbox and mask Detecter
    ## Defined in MaskRCNN/detector
    coco_model_path = 'MaskRCNN/pretrained/mask_rcnn_coco.h5'
    model_dir = 'MaskRCNN/logs'
    mydetector = detector.Detector(coco_model_path, model_dir)


    ## Mian process pipeline
    dataset_path = 'Dataset/MOTSChallenge'
    det_result_path = os.path.join(dataset_path, 'maskrcnn')
    videos = os.listdir(det_result_path)    #['0002', '0005', ...]

    for video in videos:
        video_path = os.path.join(det_result_path, video)
        frames = os.listdir(video_path)    #['000001.npz', '000002.npz',...]

        #### Tracking for a video start

        tracklets = []    # List to store tracklets for a video
        for frame in frames:
            raw_image_path = os.path.join(video_path, frame).replace('maskrcnn', 'images').replace('npz', 'jpg')
            frame_image = cv2.imread(raw_image_path)

            det_result = np.load( os.path.join(video_path, frame) )
            frame_masks = det_result['masks']
            frame_rois = det_result['rois']
            frame_class_ids = det_result['class_ids']
            frame_scores = det_result['scores']

            if len(tracklets) == 0:
                ## Init tracklets with current frame
                


                




    '''
    img = skimage.io.imread('MaskRCNN/images/9247489789_132c0d534a_z.jpg')
    result = mydetector.detect([img])
    print(result[0]['rois'].shape)
    '''



    '''
    #SiamMask Test Code:
    img1 = cv2.imread('SiamMask/testdata/img/000000.png')
    print(img1.shape)
    target_pos = np.array([813, 281.25])    # target_pos: np.array([cols, rows]) which indicate the center point position
    target_sz = np.array([95, 187.5])       # target_sz:  np.array([target_width, target_height]) which indicate the target size

    examplar_feature = mytracker.get_examplar_feature(img1, target_pos, target_sz)
    
    for index in range(154):
        str_index = "%04d" % index
        img = cv2.imread('SiamMask/testdata/img/00' + str_index + '.png')
        target_pos, target_sz, _, mask = mytracker.siamese_track(img, target_pos, target_sz, examplar_feature)

        mask = mask > 0.3
        img[:, :, 2] = mask * 255 + (1 - mask) * img[:, :, 2]
        print(mask.shape)
        #cv2.imshow("result", img)
        #cv2.waitKey(1)
    '''