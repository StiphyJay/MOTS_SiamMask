import os
import sys
SiamMaskPath = os.path.join(os.getcwd(), 'SiamMask')
sys.path.append(SiamMaskPath)
MaskRCNNPath = os.path.join(os.getcwd(), 'MaskRCNN')
sys.path.append(MaskRCNNPath)

import cv2
#import skimage.io
import numpy as np

from sklearn.utils.linear_assignment_ import linear_assignment

# Issue: 同时导入时会出bug
import singletracker
#import detector





## Args class for debugging only
class Args(object):
    def __init__(self):
        self.visualize = True
        self.siammask_threshold = 0.3




class Tracklet(object):
    def __init__(self, target_track_id, target_class_id, target_pos, target_sz, target_mask, target_score, examplar_feature, match_feature = None):
        self.target_track_id = target_track_id

        self.target_class_id = target_class_id
        self.target_pos = target_pos
        self.target_sz = target_sz
        self.target_mask = target_mask
        self.target_score = target_score
        self.examplar_feature = examplar_feature
        self.match_feature = match_feature    # To be defined

        self.update_flag = True    # Indicate that the tracklet is updated in current frame

        ## Parameter predicted by Siammask 
        self.predicted_pos = None
        self.predicted_sz = None
        self.predicted_mask = None
        self.predicted_score = None
    
    def update_state(self, target_pos, target_sz, target_mask, target_score, match_feature = None):
        self.target_pos = target_pos
        self.target_sz = target_sz
        self.target_mask = target_mask
        self.target_score = target_score
        self.match_feature = match_feature
        
        self.update_flag = True


    def update_predicted_state(self, predicted_pos, predicted_sz, predicted_mask, predicted_score):
        self.predicted_pos = predicted_pos
        self.predicted_sz = predicted_sz
        self.predicted_mask = predicted_mask
        self.predicted_score = predicted_score    




def mask_iou(det_mask, pred_mask):
    '''
    Computes IoU between two masks
    Input: two 2D array mask
    '''
    Union = (pred_mask + det_mask) != 0
    Intersection =  (pred_mask * det_mask) != 0
    return np.sum(Intersection) / np.sum(Union)




def associate_detection_to_tracklets(det_result, tracklets, iou_threshold = 0.5):
    ## Conduct association between frame_detect_result and tracklets' predicted result
     # Without appearance matching 20190830
    frame_masks = det_result['masks']
    frame_rois = det_result['rois']
    frame_class_ids = det_result['class_ids']
    frame_scores = det_result['scores']

    tracklet_num = len(tracklets)
    det_object_num = frame_masks.shape[2]
    iou_matrix = np.zeros( shape=(det_object_num, tracklet_num), dtype=np.float32 )
    for det_object_index in range(det_object_num):
        for tracklet_index in range(tracklet_num):
            iou_matrix[det_object_index][tracklet_index] = mask_iou( frame_masks[:, :, det_object_index], tracklets[tracklet_index].predicted_mask )
    matched_indices = linear_assignment(-iou_matrix)

    ############## start sort ################
    unmatched_detections = []
    for det_object_index in range(det_object_num):
        if( det_object_index not in matched_indices[:,0] ):
            unmatched_detections.append(det_object_index)
    
    unmatched_tracklets = []
    for tracklet_index in range(tracklet_num):
        if( tracklet_index not in matched_indices[:,1] ):
            unmatched_tracklets.append(tracklet_index)

    #filter out matched with low IOU
    matches = []
    for m in matched_indices:
        if(iou_matrix[m[0],m[1]] < iou_threshold):
            unmatched_detections.append(m[0])
            unmatched_tracklets.append(m[1])
        else:
            matches.append(m.reshape(1,2))
    if(len(matches)==0):
        matches = np.empty((0,2),dtype=int)
    else:
        matches = np.concatenate(matches,axis=0)

    return matches, np.array(unmatched_detections), np.array(unmatched_tracklets)




def visualize_current_frame(frame_image, tracklets):
    for tracklet in tracklets:
        mask = tracklet.target_mask
        frame_image[:, :, 2] = mask * 255 + (1 - mask) * frame_image[:, :, 2]
    cv2.imshow('test', frame_image)
    cv2.waitKey(1)






if __name__ == '__main__':
    
    args = Args()    # Debug args

    
    ## Single object tracker Siammask
    ## Defined in SiamMask/singletracker.py
    vot_model_path = 'SiamMask/pretrained/SiamMask_VOT.pth'
    vot_config_path = 'SiamMask/config/config_vot.json'
    mytracker = singletracker.SingleTracker(vot_config_path, vot_model_path)
    

    '''
    ## Bbox and mask Detecter
    ## Defined in MaskRCNN/detector
    coco_model_path = 'MaskRCNN/pretrained/mask_rcnn_coco.h5'
    model_dir = 'MaskRCNN/logs'
    mydetector = detector.Detector(coco_model_path, model_dir)
    '''

    ## Mian process pipeline
    dataset_path = 'Dataset/MOTSChallenge'
    det_result_path = os.path.join(dataset_path, 'maskrcnn')
    track_result_path = 'Result'
    if not os.path.exists(track_result_path):
        os.mkdir(track_result_path)
    
    videos = os.listdir(det_result_path)    #['0002', '0005', ...]
    for video in videos:
        video_path = os.path.join(det_result_path, video)
        video_track_result_path = os.path.join(track_result_path, video)
        if not os.path.exists(video_track_result_path):
            os.mkdir(video_track_result_path)
        
        frames = os.listdir(video_path)    #['000001.npz', '000002.npz',...]
        frames.sort()    # To make the frame in order

        #### Tracking for a video start
        tracklets = []    # List to store tracklets for a video
        track_id_to_assign = 0    # The unused track_id to be assigned

        for frame in frames:
            raw_image_path = os.path.join(video_path, frame).replace('maskrcnn', 'images').replace('npz', 'jpg')
            frame_image = cv2.imread(raw_image_path)

            det_result = np.load( os.path.join(video_path, frame) )

            for tracklet in tracklets:
                tracklet.update_flag = False

            if len(tracklets) == 0:
                ## Init trackldet_object_numets with current frame
                frame_masks = det_result['masks']
                frame_rois = det_result['rois']
                frame_class_ids = det_result['class_ids']
                frame_scores = det_result['scores']
                det_object_num = frame_masks.shape[2]

                for obj_index in range(det_object_num):
                    
                    obj_class_id = frame_class_ids[obj_index]

                    obj_roi = frame_rois[obj_index]

                    obj_pos = np.array( [np.mean(obj_roi[0::2]), np.mean(obj_roi[1::2])] )
                    obj_sz = np.array( [obj_roi[2]-obj_roi[0], obj_roi[3]-obj_roi[1]] )
                    
                    obj_mask = frame_masks[:, :, obj_index]
                    obj_score = frame_scores[obj_index]
                    examplar_feature = mytracker.get_examplar_feature(frame_image, obj_pos, obj_sz)
                    tracklet = Tracklet(track_id_to_assign, obj_class_id, obj_pos, obj_sz, obj_mask, obj_score, examplar_feature)
                    track_id_to_assign += 1    # Increase the unused track id 
                    tracklets.append(tracklet)
            
            else:
                for tracklet in tracklets:
                    predicted_result = mytracker.siamese_track( frame_image,
                                                                tracklet.target_pos,
                                                                tracklet.target_sz,
                                                                tracklet.examplar_feature)
                    predicted_pos, predicted_sz, predicted_score, predicted_mask = predicted_result
                    predicted_mask = predicted_mask > args.siammask_threshold    # To get a binary mask

                    tracklet.update_predicted_state(predicted_pos, predicted_sz, predicted_mask, predicted_score)
                
                matched, unmatched_det_result, unmatched_tracklets = associate_detection_to_tracklets(det_result, tracklets)
                
                ## Update matched tracklets with assigned det result
                for tracklet_index, tracklet in enumerate(tracklets):
                    if (tracklet_index not in unmatched_tracklets):
                        det_result_index = int( matched[np.where(matched[:, 1]==tracklet_index)[0], 0] )    # det_result_index have to be a value not an array

                        obj_roi = det_result['rois'][det_result_index]

                        obj_pos = np.array( [np.mean(obj_roi[0::2]), np.mean(obj_roi[1::2])] )
                        obj_sz = np.array( [obj_roi[2]-obj_roi[0], obj_roi[3]-obj_roi[1]] )

                        obj_mask = det_result['masks'][:, :, det_result_index]
                        obj_score = det_result['scores'][det_result_index]

                        tracklet.update_state(obj_pos, obj_sz, obj_mask, obj_score)

                ## Create and initialise new tracklets for unmatched det result
                for det_result_index in unmatched_det_result:
                    obj_class_id = det_result['class_ids'][det_result_index]

                    obj_roi = det_result['rois'][det_result_index]
                    obj_pos = np.array( [np.mean(obj_roi[0::2]), np.mean(obj_roi[1::2])] )
                    obj_sz = np.array( [obj_roi[2]-obj_roi[0], obj_roi[3]-obj_roi[1]] )

                    obj_mask = det_result['masks'][:, :, det_result_index]
                    obj_score = det_result['scores'][det_result_index]
                    examplar_feature = mytracker.get_examplar_feature(frame_image, obj_pos, obj_sz)
                    
                    tracklet = Tracklet(track_id_to_assign, obj_class_id, obj_pos, obj_sz, obj_mask, obj_score, examplar_feature)
                    track_id_to_assign += 1    # Increase the unused track id 
                    tracklets.append(tracklet)
                
                ## Remove untracked tracklets
                tracklet_index = len(tracklets)
                for tracklet in reversed(tracklets):
                    tracklet_index -= 1
                    if tracklet.update_flag == False:
                        tracklets.pop(tracklet_index)

            if args.visualize == True:
                visualize_current_frame(frame_image, tracklets)




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