#helper functions
from fastai import *
from fastai.vision import *
import numpy as np
# import cv2
import torch
import torch.nn as nn
import torch.nn.functional as F


# def open_image4d(path:PathOrStr)->Image:
#     '''open RGBA image from 4 different 1-channel files.
#     return: numpy array [4, sz, sz]'''
#     path=str(path)
#     flags = cv2.IMREAD_GRAYSCALE
#     red = cv2.imread(path+ '_red.png', flags)
#     blue = cv2.imread(path+ '_blue.png', flags)
#     green = cv2.imread(path+ '_green.png', flags)
#     yellow = cv2.imread(path+ '_yellow.png', flags)
#     im = np.stack(([red, green, blue, yellow]))

#     return Image(Tensor(im/255).float())

# def open_image4d(path:PathOrStr)->Image:
#     '''open RGBA image from a single 4-channel file
#     return: numpy array [4, sz, sz]'''
#     path=str(path)
#     flags = cv2.IMREAD_UNCHANGED
#     im = cv2.imread(path+ '.png', flags)
#     return Image(Tensor(np.rollaxis(im, 2, 0)/255).float())

def f1(y_pred, y_true, thresh:float=0.5, beta:float=1, eps:float=1e-9, sigmoid:bool=True):
    beta2 = beta**2
    if sigmoid: y_pred = y_pred.sigmoid()
    y_pred = (y_pred>thresh).float()
    y_true = y_true.float()
    TP = (y_pred*y_true).sum(dim=0)
    prec = TP/(y_pred.sum(dim=0)+eps)
    rec = TP/(y_true.sum(dim=0)+eps)
    res = (prec*rec)/(prec*beta2+rec+eps)*(1+beta2)
    return res.mean()

def f1_np(y_pred, y_true, thresh=0.5):
    y_pred = (y_pred>thresh).astype(int)
    TP = (y_pred*y_true).sum(0)
    prec = TP/(y_pred.sum(0)+1e-9)
    rec = TP/(y_true.sum(0)+1e-9)
    res = 2*prec*rec/(prec+rec+1e-9)
    return res.mean()

def f1_n(y_pred, y_true, thresh, n, default=0.5):
    i_th = default * np.ones(y_pred.shape[1])
    i_th[n]=thresh
    return f1_np(y_pred, y_true, i_th)

def find_thresh(y_pred, y_true):
    print(f'initial f1 = {f1(y_pred, y_true, 0.4)}' )
    return find_thresh_np(to_np(y_pred.sigmoid()), to_np(y_true))

def find_thresh_np(y_pred, y_true):
    ths = []
    for i in range(y_pred.shape[1]):
        aux = []
        for th in np.linspace(0,1,200):
            aux += [f1_n(y_pred, y_true, th, i)]
        value = np.array(aux).argmax()/200
        print(f'class: {i} --> {value}')
        ths += [value]
    final_score = f1_np(y_pred, y_true, np.array(ths))
    print(f'final f1 = {final_score}')
    return np.array(ths), final_score

####################################################
##### This is focal loss class for multi class #####
####################################################

# import torch
# import torch.nn as nn
# import torch.nn.functional as F
# from torch.autograd import Variable
# # I refered https://github.com/c0nn3r/RetinaNet/blob/master/focal_loss.py

# class FocalLoss2d(nn.modules.loss._WeightedLoss):

#     def __init__(self, gamma=2, weight=None, size_average=None, ignore_index=-100,
#                  reduce=None, reduction='mean', balance_param=0.25):
#         super(FocalLoss2d, self).__init__(weight, size_average, reduce, reduction)
#         self.gamma = gamma
#         self.weight = weight
#         self.size_average = size_average
#         self.ignore_index = ignore_index
#         self.balance_param = balance_param

#     def forward(self, input, target):
        
#         # inputs and targets are assumed to be BatchxClasses
#         assert len(input.shape) == len(target.shape)
#         assert input.size(0) == target.size(0)
#         assert input.size(1) == target.size(1)
#         weight = Variable(self.weight)
#         # compute the negative likelyhood
#         logpt = - F.binary_cross_entropy_with_logits(input, target, pos_weight=weight, reduction=self.reduction)
#         pt = torch.exp(logpt)

#         # compute the loss
#         focal_loss = -( (1-pt)**self.gamma ) * logpt
#         balanced_focal_loss = self.balance_param * focal_loss
#         return balanced_focal_loss

class FocalLoss(nn.Module):
    def __init__(self, gamma=2):
        super().__init__()
        self.gamma = gamma
        
    def forward(self, input, target):
        if not (target.size() == input.size()):
            raise ValueError("Target size ({}) must be the same as input size ({})"
                             .format(target.size(), input.size()))

        max_val = (-input).clamp(min=0)
        loss = input - input * target + max_val + \
            ((-max_val).exp() + (-input - max_val).exp()).log()

        invprobs = F.logsigmoid(-input * (target * 2.0 - 1.0))
        loss = (invprobs * self.gamma).exp() * loss
        
        return loss.sum(dim=1).mean()
    