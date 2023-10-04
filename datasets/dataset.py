import glob
import torch
import os
from torch.utils.data import Dataset
from imgaug import augmenters as iaa
import cv2
import pandas as pd
import random
import json
from torchvision.transforms import Normalize


class ImageDataset(Dataset):
    def __len__(self) -> int:
        return len(self.pair_list)

    def train_augmentors(self):
        sometimes = lambda aug: iaa.Sometimes(0.2, aug)
        input_augs = iaa.Sequential(
            [
                # apply the following augmenters to most images
                iaa.Fliplr(0.5),  # horizontally flip 50% of all images
                iaa.Flipud(0.5),  # vertically flip 50% of all images
                sometimes(iaa.Affine(
                    rotate=(-45, 45),  # rotate by -45 to +45 degrees
                    shear=(-16, 16),  # shear by -16 to +16 degrees
                    order=[0, 1],  # use nearest neighbour or bilinear interpolation (fast)
                    cval=(0, 255),  # if mode is constant, use a cval between 0 and 255
                    mode='symmetric'
                    # use any of scikit-image's warping modes (see 2nd image from the top for examples)
                )),
                # execute 0 to 5 of the following (less important) augmenters per image
                # don't execute all of them, as that would often be way too strong
                iaa.SomeOf((0, 5),
                           [
                               iaa.OneOf([
                                   iaa.GaussianBlur((0, 3.0)),  # blur images with a sigma between 0 and 3.0
                                   iaa.AverageBlur(k=(2, 7)),
                                   # blur image using local means with kernel sizes between 2 and 7
                                   iaa.MedianBlur(k=(3, 11)),
                                   # blur image using local medians with kernel sizes between 2 and 7
                               ]),
                               iaa.AdditiveGaussianNoise(loc=0, scale=(0.0, 0.05 * 255), per_channel=0.5),
                               # add gaussian noise to images
                               iaa.Dropout((0.01, 0.1), per_channel=0.5),  # randomly remove up to 10% of the pixels
                               # change brightness of images (by -10 to 10 of original value)
                               iaa.AddToHueAndSaturation((-20, 20)),  # change hue and saturation
                               iaa.LinearContrast((0.5, 2.0), per_channel=0.5),  # improve or worsen the contrast
                           ],
                           random_order=True
                           )
            ],
            random_order=True
        )
        return input_augs

    def __getitem__(self, index):
        img_path, label = self.pair_list[index]
        if self.args.type != 'single_encoder':
            caption = combine_hard_prompt_with_label(self.hard_text_prompt, label)
        image = cv2.imread(img_path)
        image = cv2.resize(image, (self.resize,self.resize))
        if self.train == True:
            train_augmentors = self.train_augmentors()
            image = train_augmentors.augment_image(image)
        img_tensor = torch.tensor(image.copy(), dtype=torch.float32).permute(2,0,1) # C,H,W
        img_tensor = Normalize(mean=self.mean, std=self.std)(img_tensor)

        if self.args.type == 'single_encoder':
            return img_path, img_tensor, 'no_hard_prompt', label
        else:
            return img_path, img_tensor, self.hard_text_prompt, caption

    def __init__(self, pair_list, args, train=True):
        self.args = args
        self.pair_list = pair_list
        self.resize = args.encoder_resize
        self.hard_text_prompt = get_hard_prompt(args.dataset)
        self.mean = args.encoder_mean
        self.std = args.encoder_std
        self.train = train

def prepare_panda_512_data():
    def map_label_caption(path):
        mapping_dict = {
            '2': 'benign.',
            '3': 'cancer 3.',
            '4': 'cancer 4.',
            '5': 'cancer 5.',
        }
        label = path.split('_')[-3]

        return mapping_dict[label]


    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        label_list = [map_label_caption(file_path) for file_path in file_list]

        return list(zip(file_list, label_list))

    # 1000 ~ 6158
    data_root_dir = '/home/compu/anhnguyen/dataset/PANDA/PANDA_512'
    train_set_1 = load_data_info('%s/1*/*.png' % data_root_dir)
    train_set_2 = load_data_info('%s/2*/*.png' % data_root_dir)
    train_set_3 = load_data_info('%s/3*/*.png' % data_root_dir)
    train_set_4 = load_data_info('%s/4*/*.png' % data_root_dir)
    train_set_5 = load_data_info('%s/5*/*.png' % data_root_dir)
    train_set_6 = load_data_info('%s/6*/*.png' % data_root_dir)

    train_set = train_set_1 + train_set_2 + train_set_4 + train_set_6
    valid_set = train_set_3
    test_set = train_set_5

    return train_set, valid_set, test_set

def prepare_colon(label_type='caption'):
    def map_label_caption(path):
        mapping_dict = {
            '0': 'benign.',
            '1': 'well differentiated cancer.',
            '2': 'moderately differentiated cancer.',
            '3': 'poorly differentiated cancer.',
        }
        label = path.split('_')[-1].split('.')[0]
        if label_type == 'caption':
            return mapping_dict[label]
        else:
            return int(path.split('_')[-1].split('.')[0])
    
    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        label_list = [map_label_caption(file_path) for file_path in file_list]

        return list(zip(file_list, label_list))

    data_root_dir = '/home/compu/anhnguyen/dataset/KBSMC_512'
    set_tma01 = load_data_info('%s/tma_01/*.jpg' % data_root_dir)
    set_tma02 = load_data_info('%s/tma_02/*.jpg' % data_root_dir)
    set_tma03 = load_data_info('%s/tma_03/*.jpg' % data_root_dir)
    set_tma04 = load_data_info('%s/tma_04/*.jpg' % data_root_dir)
    set_tma05 = load_data_info('%s/tma_05/*.jpg' % data_root_dir)
    set_tma06 = load_data_info('%s/tma_06/*.jpg' % data_root_dir)
    set_wsi01 = load_data_info('%s/wsi_01/*.jpg' % data_root_dir)  # benign exclusively
    set_wsi02 = load_data_info('%s/wsi_02/*.jpg' % data_root_dir)  # benign exclusively
    set_wsi03 = load_data_info('%s/wsi_03/*.jpg' % data_root_dir)  # benign exclusively

    train_set = set_tma01 + set_tma02 + set_tma03 + set_tma05 + set_wsi01
    valid_set = set_tma06 + set_wsi03
    test_set = set_tma04 + set_wsi02

    return train_set, valid_set, test_set

def prepare_colon_test_2(label_type='caption'):
    def map_label_caption(path):
        mapping_dict = {
            '1': 'benign.',
            '2': 'well differentiated cancer.',
            '3': 'moderately differentiated cancer.',
            '4': 'poorly differentiated cancer.',
        }
        label = path.split('_')[-1].split('.')[0]

        if label_type == 'caption':
            return mapping_dict[label]
        else:
            return int(label)-1

    def load_data_info_from_list(data_dir, path_list):
        file_list = []
        for WSI_name in path_list:
            pathname = glob.glob(f'{data_dir}/{WSI_name}/*/*.png')
            file_list.extend(pathname)
            label_list = [map_label_caption(file_path) for file_path in file_list]
        list_out = list(zip(file_list, label_list))

        return list_out

    data_root_dir = '/home/compu/anhnguyen/dataset/KBSMC_512_test2/KBSMC_test_2'
    wsi_list = ['wsi_001', 'wsi_002', 'wsi_003', 'wsi_004', 'wsi_005', 'wsi_006', 'wsi_007', 'wsi_008', 'wsi_009',
                'wsi_010', 'wsi_011', 'wsi_012', 'wsi_013', 'wsi_014', 'wsi_015', 'wsi_016', 'wsi_017', 'wsi_018',
                'wsi_019', 'wsi_020', 'wsi_021', 'wsi_022', 'wsi_023', 'wsi_024', 'wsi_025', 'wsi_026', 'wsi_027',
                'wsi_028', 'wsi_029', 'wsi_030', 'wsi_031', 'wsi_032', 'wsi_033', 'wsi_034', 'wsi_035', 'wsi_090',
                'wsi_092', 'wsi_093', 'wsi_094', 'wsi_095', 'wsi_096', 'wsi_097', 'wsi_098', 'wsi_099', 'wsi_100']

    test_set = load_data_info_from_list(data_root_dir, wsi_list)

    return test_set

def prepare_prostate_uhu_data(label_type='caption'):
    def map_label_caption(path):
        mapping_dict = {
            '0': 'benign.',
            '1': 'grade 3 cancer.',
            '2': 'grade 4 cancer.',
            '3': 'grade 5 cancer.',
        }
        mapping_dict_2 = {
            0:0,
            1:4,
            2:5,
            3:6
        }
        label = path.split('_')[-1].split('.')[0]
        if label_type == 'caption':
            return mapping_dict[label]
        elif label_type == 'combine_dataset':
            temp = int(path.split('_')[-1].split('.')[0])
            return mapping_dict_2[temp]
        else:
            return int(label)

    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        label_list = [map_label_caption(file_path) for file_path in file_list]
        return list(zip(file_list, label_list))

    data_root_dir = '/home/compu/doanhbc/datasets/prostate_harvard'
    data_root_dir_train = f'{data_root_dir}/patches_train_750_v0'
    data_root_dir_valid = f'{data_root_dir}/patches_validation_750_v0'
    data_root_dir_test = f'{data_root_dir}/patches_test_750_v0'

    train_set_111 = load_data_info('%s/ZT111*/*.jpg' % data_root_dir_train)
    train_set_199 = load_data_info('%s/ZT199*/*.jpg' % data_root_dir_train)
    train_set_204 = load_data_info('%s/ZT204*/*.jpg' % data_root_dir_train)
    valid_set = load_data_info('%s/ZT76*/*.jpg' % data_root_dir_valid)
    test_set = load_data_info('%s/patho_1/*/*.jpg' % data_root_dir_test)

    train_set = train_set_111 + train_set_199 + train_set_204
    return train_set, valid_set, test_set

def prepare_prostate_ubc_data(label_type='caption'):
    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        label_list = [int(file_path.split('_')[-1].split('.')[0]) for file_path in file_list]
        label_dict = {
            0: 'benign.', 
            2: 'grade 3 cancer.', 
            3: 'grade 4 cancer.', 
            4: 'grade 5 cancer.'
        }
        mapping_dict_2 = {
            0:0,
            2:4,
            3:5,
            4:6
        }
        if label_type == 'caption':
            label_list = [label_dict[k] for k in label_list]
        elif label_type == 'combine_dataset':
            for i in range(len(label_list)):
                label_list[i] = mapping_dict_2[label_list[i]]
        else:
            for i in range(len(label_list)):
                if label_list[i] != 0:
                    label_list[i] = label_list[i] - 1

        return list(zip(file_list, label_list))
    
    data_root_dir = '/home/compu/doanhbc/datasets'
    data_root_dir_train_ubc = f'{data_root_dir}/prostate_miccai_2019_patches_690_80_step05_test/'
    test_set_ubc = load_data_info('%s/*/*.jpg' % data_root_dir_train_ubc)
    return test_set_ubc

def prepare_gastric(nr_classes=4, label_type='caption'):
    def load_data_info_from_list(path_list, gt_list, data_root_dir, label_type='caption'):
        mapping_dict = {
            0: 'benign.',
            1: 'tubular well differentiated cancer.',
            2: 'tubular moderately differentiated cancer.',
            3: 'tubular poorly differentiated cancer.',
            4: 'other'
        }

        mapping_dict_2 = {
            0:0,
            1:7,
            2:8,
            3:9,
            4:2
        }

        file_list = []
        for tma_name in path_list:
            pathname = glob.glob(f'{data_root_dir}/{tma_name}/*.jpg')
            file_list.extend(pathname)
        
        label_list = [int(file_path.split('_')[-1].split('.')[0]) for file_path in file_list]
        if label_type == 'caption':
            label_list = [mapping_dict[gt_list[i]] for i in label_list]
        elif label_type == 'combine_dataset':
            label_list = [mapping_dict_2[gt_list[i]] for i in label_list]
        else:
            label_list = [gt_list[i] for i in label_list]
        list_out = list(zip(file_list, label_list))
        if label_type == 'caption':
            list_out = [list_out[i] for i in range(len(list_out)) if list_out[i][1] != 'other']
        elif label_type == 'combine_dataset':
            list_out = [list_out[i] for i in range(len(list_out)) if list_out[i][1] != 2]
        else:
            list_out = [list_out[i] for i in range(len(list_out)) if list_out[i][1] < 4]

        return list_out

    def load_a_dataset(csv_path, gt_list, data_root_dir, data_root_dir_2, down_sample=True, label_type='caption'):
        df = pd.read_csv(csv_path).iloc[:, :3]
        train_list = list(df.query('Task == "train"')['WSI'])
        valid_list = list(df.query('Task == "val"')['WSI'])
        test_list = list(df.query('Task == "test"')['WSI'])
        train_set = load_data_info_from_list(train_list, gt_list, data_root_dir, label_type)

        if down_sample:
            train_normal = [train_set[i] for i in range(len(train_set)) if train_set[i][1] == 0]
            train_tumor = [train_set[i] for i in range(len(train_set)) if train_set[i][1] != 0]

            random.shuffle(train_normal)
            train_normal = train_normal[: len(train_tumor) // 3]
            train_set = train_normal + train_tumor

        valid_set = load_data_info_from_list(valid_list, gt_list, data_root_dir_2, label_type)
        test_set = load_data_info_from_list(test_list, gt_list, data_root_dir_2, label_type)
        return train_set, valid_set, test_set

    if nr_classes == 3:
        gt_train_local = {1: 4,  # "BN", #0
                          2: 4,  # "BN", #0
                          3: 0,  # "TW", #2
                          4: 1,  # "TM", #3
                          5: 2,  # "TP", #4
                          6: 4,  # "TLS", #1
                          7: 4,  # "papillary", #5
                          8: 4,  # "Mucinous", #6
                          9: 4,  # "signet", #7
                          10: 4,  # "poorly", #7
                          11: 4  # "LVI", #ignore
                          }
    elif nr_classes == 4:
        gt_train_local = {1: 0,  # "BN", #0
                          2: 0,  # "BN", #0
                          3: 1,  # "TW", #2
                          4: 2,  # "TM", #3
                          5: 3,  # "TP", #4
                          6: 4,  # "TLS", #1
                          7: 4,  # "papillary", #5
                          8: 4,  # "Mucinous", #6
                          9: 4,  # "signet", #7
                          10: 4,  # "poorly", #7
                          11: 4  # "LVI", #ignore
                          }
    elif nr_classes == 5:
        gt_train_local = {1: 0,  # "BN", #0
                          2: 0,  # "BN", #0
                          3: 1,  # "TW", #2
                          4: 2,  # "TM", #3
                          5: 3,  # "TP", #4
                          6: 8,  # "TLS", #1
                          7: 8,  # "papillary", #5
                          8: 8,  # "Mucinous", #6
                          9: 4,  # "signet", #7
                          10: 4,  # "poorly", #7
                          11: 8  # "LVI", #ignore
                          }
    elif nr_classes == 6:
        gt_train_local = {1: 0,  # "BN", #0
                          2: 0,  # "BN", #0
                          3: 2,  # "TW", #2
                          4: 2,  # "TM", #3
                          5: 2,  # "TP", #4
                          6: 1,  # "TLS", #1
                          7: 3,  # "papillary", #5
                          8: 4,  # "Mucinous", #6
                          9: 5,  # "signet", #7
                          10: 5,  # "poorly", #7
                          11: 6  # "LVI", #ignore
                          }
    elif nr_classes == 8:
        gt_train_local = {1: 0,  # "BN", #0
                          2: 0,  # "BN", #0
                          3: 2,  # "TW", #2
                          4: 3,  # "TM", #3
                          5: 4,  # "TP", #4
                          6: 1,  # "TLS", #1
                          7: 5,  # "papillary", #5
                          8: 6,  # "Mucinous", #6
                          9: 7,  # "signet", #7
                          10: 7,  # "poorly", #7
                          11: 8  # "LVI", #ignore
                          }
    elif nr_classes == 10:
        gt_train_local = {1: 0,  # "BN", #0
                          2: 0,  # "BN", #0
                          3: 1,  # "TW", #2
                          4: 2,  # "TM", #3
                          5: 3,  # "TP", #4
                          6: 4,  # "TLS", #1
                          7: 5,  # "papillary", #5
                          8: 6,  # "Mucinous", #6
                          9: 7,  # "signet", #7
                          10: 8,  # "poorly", #7
                          11: 9  # "LVI", #ignore
                          }
    else:
        gt_train_local = {1: 0,  # "BN", #0
                          2: 0,  # "BN", #0
                          3: 1,  # "TW", #2
                          4: 2,  # "TM", #3
                          5: 3,  # "TP", #4
                          6: 8,  # "TLS", #1
                          7: 8,  # "papillary", #5
                          8: 5,  # "Mucinous", #6
                          9: 4,  # "signet", #7
                          10: 4,  # "poorly", #7
                          11: 8  # "LVI", #ignore
                          }

    csv_her02 = '/home/compu/anhnguyen/dataset/data2/lju/gastric/gastric_cancer_wsi_1024_80_her01_split.csv'
    csv_addition = '/home/compu/anhnguyen/dataset/data2/lju/gastric/gastric_wsi_addition_PS1024_ano08_split.csv'

    data_her_root_dir = f'/home/compu/anhnguyen/dataset/data2/lju/gastric/gastric_wsi/gastric_cancer_wsi_1024_80_her01_step05_bright230_resize05'
    data_her_root_dir_2 = f'/home/compu/anhnguyen/dataset/data2/lju/gastric/gastric_wsi/gastric_cancer_wsi_1024_80_her01_step10_bright230_resize05'
    data_add_root_dir = f'/home/compu/anhnguyen/dataset/data2/lju/gastric/gastric_wsi_addition/gastric_wsi_addition_PS1024_ano08_step05_bright230_resize05'
    data_add_root_dir_2 = f'/home/compu/anhnguyen/dataset/data2/lju/gastric/gastric_wsi_addition/gastric_wsi_addition_PS1024_ano08_step10_bright230_resize05'

    train_set, valid_set, test_set = load_a_dataset(csv_her02, gt_train_local,data_her_root_dir, data_her_root_dir_2, label_type=label_type)
    train_set_add, valid_set_add, test_set_add = load_a_dataset(csv_addition, gt_train_local, data_add_root_dir, data_add_root_dir_2, down_sample=False, label_type=label_type)
    
    train_set += train_set_add
    valid_set += valid_set_add
    test_set += test_set_add

    return train_set, valid_set, test_set

def prepare_k19(label_type='caption'):
    data_root_dir = '/data1/trinh/data/raw_data/Domain_Invariance/colon_class/NCT-CRC-HE-100K/'
    json_dir = '/data1/trinh/code/DoIn/pycontrast/datasets/K19_9class_split.json'
    with open(json_dir) as json_file:
        data = json.load(json_file)

    train_set = data['train_set']
    valid_set = data['valid_set']
    test_set = data['test_set']
    train_set = [[data_root_dir + train_set[i][0], train_set[i][1]] for i in range(len(train_set))]
    valid_set = [[data_root_dir + valid_set[i][0], valid_set[i][1]] for i in range(len(valid_set))]
    test_set = [[data_root_dir + test_set[i][0], test_set[i][1]] for i in range(len(test_set))]

    # mapping_dict = {
    #     0: 'tissue adipole.',
    #     1: 'tissue background.',
    #     2: 'tissue debris.',
    #     3: 'tissue lymphocyte.',
    #     4: 'tissue mucus.',
    #     5: 'tissue muscle.',
    #     6: 'tissue normal.',
    #     7: 'tissue stroma.',
    #     8: 'tissue tumor.'
    # }
    mapping_dict = {
        0: 'adipole.',
        1: 'background.',
        2: 'debris.',
        3: 'lymphocyte.',
        4: 'debris.',   # mucus -> debris (MUC->DEB)
        5: 'stroma.',   # muscle -> stroma (MUS->STR)
        6: 'normal.',
        7: 'stroma.',
        8: 'tumor.'
    }
    if label_type == 'caption':
        for i in range(len(train_set)):
            train_set[i][1] = mapping_dict[train_set[i][1]]
        
        for i in range(len(valid_set)):
            valid_set[i][1] = mapping_dict[valid_set[i][1]]
        
        for i in range(len(test_set)):
            test_set[i][1] = mapping_dict[test_set[i][1]]
    elif label_type == 'combine_dataset':
        for i in range(len(train_set)):
            train_set[i][1] += 10
        
        for i in range(len(valid_set)):
            valid_set[i][1] += 10
        
        for i in range(len(test_set)):
            test_set[i][1] += 10

    return train_set, valid_set, test_set

def prepare_k16(label_type='caption'):
    def load_data_info(covert_dict):
        data_root_dir_k16 = '/data1/trinh/data/raw_data/Domain_Invariance/colon_class/Kather_texture_2016_image_tiles_5000'
        pathname = f'{data_root_dir_k16}/*/*.tif'
        file_list = glob.glob(pathname)
        COMPLEX_list = glob.glob(f'{data_root_dir_k16}/03_COMPLEX/*.tif')
        file_list = [elem for elem in file_list if elem not in COMPLEX_list]
        label_list = [covert_dict[file_path.split('/')[-2]] for file_path in file_list]
        return list(zip(file_list, label_list))

    # const_kather16 = {
    #         '07_ADIPOSE': 'tissue adipole.', 
    #         '08_EMPTY': 'tissue background.', 
    #         '05_DEBRIS': 'tissue debris.',
    #         '04_LYMPHO': 'tissue lymphocyte.', 
    #         '06_MUCOSA': 'tissue normal.', 
    #         '02_STROMA': 'tissue stroma.',
    #         '01_TUMOR': 'tissue tumor.'
    #     }
    const_kather16 = {
        '07_ADIPOSE': 'adipole tissue.', 
        '08_EMPTY': 'background tissue.', 
        '05_DEBRIS': 'debris tissue.',
        '04_LYMPHO': 'lymphocyte tissue.', 
        '06_MUCOSA': 'normal tissue.', 
        '02_STROMA': 'stroma tissue.',
        '01_TUMOR': 'tumor tissue.'
    }

    const_kather16_2 = {
            '07_ADIPOSE': 6, 
            '08_EMPTY': 7, 
            '05_DEBRIS': 4,
            '04_LYMPHO': 3, 
            '06_MUCOSA': 5, 
            '02_STROMA': 2,
            '01_TUMOR': 1
        }
    if label_type == 'caption':
        k16_set = load_data_info(covert_dict=const_kather16)
    else:
        k16_set = load_data_info(covert_dict=const_kather16_2)

    random.Random(5).shuffle(k16_set)
    val_ratio = 0.3

    train_set = k16_set[int(val_ratio * len(k16_set)):]
    valid_set = k16_set[:int(val_ratio/2 * len(k16_set))]
    test_set = k16_set[int(val_ratio/2 * len(k16_set)):int(val_ratio * len(k16_set))]

    return train_set, valid_set, test_set

def prepare_aggc2022_data(label_type='caption'):
    mapping_dict = {
        '2': 'benign.',
        '3': 'grade 3 cancer.',
        '4': 'grade 4 cancer.',
        '5': 'grade 5 cancer.',
    }
    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        file_list = [file_path for file_path in file_list if int(file_path.split('_')[-1][0]) > 1]
        if label_type != 'caption':
            label_list = [int(file_path.split('_')[-1][0]) - 2 for file_path in file_list if int(file_path.split('_')[-1][0]) > 1]
        else:
            label_list = [mapping_dict[file_path.split('_')[-1][0]] for file_path in file_list if int(file_path.split('_')[-1][0]) > 1]
        return list(zip(file_list, label_list))

    data_root_dir = '/home/compu/doanhbc/datasets/AGGC22_patch_512_c08'
    train_set_1 = load_data_info('%s/Subset1_Train_image/*/*' % data_root_dir)
    train_set_2 = load_data_info('%s/Subset2_Train_image/*/*' % data_root_dir)
    train_set_3 = load_data_info('%s/Subset3_Train_image/*/*/*' % data_root_dir)

    return train_set_1 + train_set_2 + train_set_3

def prepare_kidney(label_type='caption'):
    mapping_dict = {
        '0': 'normal.',
        '1': 'grade 1 cancer.',
        '2': 'grade 2 cancer.',
        '3': 'grade 3 cancer.',
        '4': 'grade 4 cancer.',
    }
    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        if label_type != 'caption':
            label_list = [int(file_path.split('/')[-2][-1]) for file_path in file_list]
        else:
            label_list = [mapping_dict[file_path.split('/')[-2][-1]] for file_path in file_list]
        return list(zip(file_list, label_list))
    data_root_dir = '/data4/anhnguyen/kidney_grading'
    train_set = load_data_info('%s/Training/*/*' % data_root_dir)
    valid_set = load_data_info('%s/Validation/*/*' % data_root_dir)
    test_set = load_data_info('%s/Test/*/*' % data_root_dir)

    return train_set, valid_set, test_set

def prepare_liver(label_type='caption'):
    mapping_dict = {
        '0': 'normal.',
        '1': 'grade 1 cancer.',
        '2': 'grade 2 cancer.',
        '3': 'grade 3 cancer.'
    }
    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        if label_type != 'caption':
            label_list = [int(file_path.split('/')[-2][-1]) for file_path in file_list]
        else:
            label_list = [mapping_dict[file_path.split('/')[-2][-1]] for file_path in file_list]
        return list(zip(file_list, label_list))
    data_root_dir = '/data4/anhnguyen/liver_grading'
    train_set = load_data_info('%s/Training/*/*' % data_root_dir)
    valid_set = load_data_info('%s/Validation/*/*' % data_root_dir)
    test_set = load_data_info('%s/Test/*/*' % data_root_dir)

    return train_set, valid_set, test_set

def prepare_breakhis(label_type='caption', fold_idx=1):
    mapping_dict = {
        'A': 'benign - adenosis.',
        'F': 'benign - fibroadenoma.',
        'PT': 'benign - phyllodes tumor.',
        'TA': 'benign - tubular adenoma.',
        'DC': 'malignant - ductal carcinoma.',
        'LC': 'malignant - lobular carcinoma.',
        'MC': 'malignant - mucinous carcinoma.',
        'PC': 'malignant - papillary carcinoma.'
    }

    mapping_dict_idx = {
        'A': 0,
        'F': 1,
        'PT': 2,
        'TA': 3,
        'DC': 4,
        'LC': 5,
        'MC': 6,
        'PC': 7
    }

    # def load_data_info(pathname):
    #     file_list = glob.glob(pathname)
    #     if label_type != 'caption':
    #         label_list = [int(file_path.split('/')[-4][0]) for file_path in file_list]
    #     else:
    #         label_list = [mapping_dict[file_path.split('/')[-4][0]] for file_path in file_list]
    #     return list(zip(file_list, label_list))
    data_root_dir = '/data3/anhnguyen/breasthis/imgs'
    # txt_file = f'/data3/anhnguyen/breasthis/dsfold{fold_idx}.txt'
    txt_file = f'/data3/anhnguyen/breasthis/fold1_new.txt'
    file1 = open(txt_file, 'r')
    train_set = []
    test_set = []
    while True:
        line = file1.readline()
        if not line:
            break
        file_name = line.split('|')[0] # /data3/anhnguyen/breasthis/imgs/SOB_B_A-14-22549AB-40-001.png
        # if file_name.split('-')[-2] == '40':
        file_path = os.path.join(data_root_dir, file_name)
        sample_type = line.split('|')[-1].replace('\n','')
        if label_type == 'caption':
            label = mapping_dict[file_name.split('-')[0].split('_')[-1]]
        else:
            label = mapping_dict_idx[file_name.split('-')[0].split('_')[-1]]
        if sample_type == 'train':
            train_set.append((file_path, label))
        else:
            test_set.append((file_path, label))
        # train_set.append((file_path, label))
    
    file1.close()
    

    # adenosis = load_data_info('%s/benign/SOB/0_adenosis/*/*/*' % data_root_dir)
    # fibroadenoma = load_data_info('%s/benign/SOB/1_fibroadenoma/*/*/*' % data_root_dir)
    # phyllodes = load_data_info('%s/benign/SOB/2_phyllodes_tumor/*/*/*' % data_root_dir)
    # tubular = load_data_info('%s/benign/SOB/3_tubular_adenoma/*/*/*' % data_root_dir)
    # ductal = load_data_info('%s/malignant/SOB/4_ductal_carcinoma/*/*/*' % data_root_dir)
    # lobular = load_data_info('%s/malignant/SOB/5_lobular_carcinoma/*/*/*' % data_root_dir)
    # mucinous = load_data_info('%s/malignant/SOB/6_mucinous_carcinoma/*/*/*' % data_root_dir)
    # papillary = load_data_info('%s/malignant/SOB/7_papillary_carcinoma/*/*/*' % data_root_dir)

    # import random
    # random.shuffle(train_set)

    # test_set = train_set[:int(len(train_set)*0.2)]
    # train_set = train_set[int(len(train_set)*0.2):]
    # random.shuffle(fibroadenoma)
    # random.shuffle(phyllodes)
    # random.shuffle(tubular)
    # random.shuffle(ductal)
    # random.shuffle(lobular)
    # random.shuffle(mucinous)
    # random.shuffle(papillary)

    # train_set = adenosis[:int((len(adenosis)+1)*.70)] + \
    #             fibroadenoma[:int((len(fibroadenoma)+1)*.70)] + \
    #             phyllodes[:int((len(phyllodes)+1)*.70)] + \
    #             tubular[:int((len(tubular)+1)*.70)] + \
    #             ductal[:int((len(ductal)+1)*.70)] + \
    #             lobular[:int((len(lobular)+1)*.70)] + \
    #             mucinous[:int((len(mucinous)+1)*.70)] + \
    #             papillary[:int((len(papillary)+1)*.70)]
                 
    # valid_set = adenosis[int((len(adenosis)+1)*.70):int((len(adenosis)+1)*.80)] + \
    #             fibroadenoma[int((len(fibroadenoma)+1)*.70):int((len(fibroadenoma)+1)*.80)] + \
    #             phyllodes[int((len(phyllodes)+1)*.70):int((len(phyllodes)+1)*.80)] + \
    #             tubular[int((len(tubular)+1)*.70):int((len(tubular)+1)*.80)] + \
    #             ductal[int((len(ductal)+1)*.70):int((len(ductal)+1)*.80)] + \
    #             lobular[int((len(lobular)+1)*.70):int((len(lobular)+1)*.80)] + \
    #             mucinous[int((len(mucinous)+1)*.70):int((len(mucinous)+1)*.80)] + \
    #             papillary[int((len(papillary)+1)*.70):int((len(papillary)+1)*.80)] 
    
    # test_set = adenosis[int((len(adenosis)+1)*.80):] + \
    #             fibroadenoma[int((len(fibroadenoma)+1)*.80):] + \
    #             phyllodes[int((len(phyllodes)+1)*.80):] + \
    #             tubular[int((len(tubular)+1)*.80):] + \
    #             ductal[int((len(ductal)+1)*.80):] + \
    #             lobular[int((len(lobular)+1)*.80):] + \
    #             mucinous[int((len(mucinous)+1)*.80):] + \
    #             papillary[int((len(papillary)+1)*.80):]

    return train_set, test_set

# prepare_breakhis ()

def prepare_bladder(label_type='caption'):
    mapping_dict = {
        '1': 'low grade cancer.',
        '2': 'high grade cancer.',
        '3': 'non-tumor.',
    }
    def load_data_info(pathname):
        file_list = glob.glob(pathname)
        if label_type != 'caption':
            label_list = []
            for file_path in file_list:
                idx = int(file_path.split('/')[-2][-1]) - 1
                if idx != 3:
                    label_list.append(int(file_path.split('/')[-2][-1]) - 1)
                else:
                    label_list.append(0)
        else:
            label_list = [mapping_dict[file_path.split('/')[-2][-1]] for file_path in file_list]
        return list(zip(file_list, label_list))
    data_root_dir = '/data2/doanhbc/prosessed_bladder_data_1024_2'
    train_set = load_data_info('%s/train/*/*/*' % data_root_dir)
    valid_set = load_data_info('%s/val/*/*/*' % data_root_dir)
    test_set = load_data_info('%s/test/*/*/*' % data_root_dir)

    return train_set, valid_set, test_set

def prepare_data(args):
    if args.type != 'single_encoder':
        dataset_type = 'caption'
    else:
        dataset_type = 'class_index'
    if args.dataset == 'colon-1':
        return prepare_colon(dataset_type)
    elif args.dataset == 'colon-2':
        return prepare_colon_test_2(dataset_type)
    elif args.dataset == 'prostate-1':
        return prepare_prostate_uhu_data(dataset_type)
    elif args.dataset == 'prostate-2':
        return prepare_prostate_ubc_data(dataset_type)
    elif args.dataset == 'prostate-3':
        return prepare_aggc2022_data(dataset_type)
    elif args.dataset == 'gastric':
        return prepare_gastric(nr_classes=4, label_type=type)
    elif args.dataset == 'k19':
        return prepare_k19(dataset_type)
    elif args.dataset == 'k16':
        return prepare_k16(dataset_type)
    elif args.dataset == 'kidney':
        return prepare_kidney(dataset_type)
    elif args.dataset == 'liver':
        return prepare_liver(dataset_type)
    elif args.dataset == 'bladder':
        return prepare_bladder(dataset_type)
    elif args.dataset == 'breakhis':
        return prepare_breakhis(dataset_type, args.breakhis_fold)
    else:
        raise ValueError(f'Not support {args.dataset}')

# get the hint aka hard prompt text
def get_hard_prompt(dataset_name):
    if dataset_name in ['colon-1', 'colon-2']:
        return "the cancer grading of this colorectal patch is"
    elif dataset_name in ['kidney']:
        return "the cancer grading of this kidney patch is"
    elif dataset_name in ['breakhis']:
        return "the tumor type of this breast patch is"
    elif dataset_name in ['liver']:
        return "the cancer grading of this liver patch is"
    elif dataset_name in ['bladder']:
        return "the tumor type of this bladder patch is"
    elif dataset_name in ['prostate-1', 'prostate-2', 'prostate-3']:
        return "the cancer grading of this prostate patch is"
    elif dataset_name in ['gastric']:
        return "the cancer grading of this gastric patch is"
    elif dataset_name in ['k19','k16']:
        return "the tissue type of this colorectal patch is"
    else:
        raise ValueError(f'Not support dataset {dataset_name}')

# prepend hard prompt to label
def combine_hard_prompt_with_label(hard_prompt_text, label):
    try:
        if label.split(' ')[-1] == 'cancer.':               # eliminate "duplicated" cancer word at the end
            label = " ".join(label.split(' ')[:-1]) + '.'
    except:
        print(label)
    if hard_prompt_text[-1] == ' ':                     # make sure to seperate by a space
        hard_prompt_text += label
    else:
        hard_prompt_text += " " + label
    return hard_prompt_text

# get caption list of dataset, with other
def get_caption(dataset_name, type='caption'):
    if dataset_name in ['colon-1', 'colon-2']:
        label = ['benign.',
                 'well differentiated cancer.',
                 'moderately differentiated cancer.',
                 'poorly differentiated cancer.'
        ]
        if type != 'caption':
            label = [0,1,2,3]
    elif dataset_name == 'liver':
        label = ['normal.',
                 'grade 1 cancer.',
                 'grade 2 cancer.',
                 'grade 3 cancer.'
        ]
        if type != 'caption':
            label = [0,1,2,3]
    elif dataset_name == 'kidney':
        label = ['normal.',
                 'grade 1 cancer.',
                 'grade 2 cancer.',
                 'grade 3 cancer.',
                 'grade 4 cancer.',
        ]
        if type != 'caption':
            label = [0,1,2,3,4]
    elif dataset_name == 'bladder':
        label = ['non-tumor.',
                 'low grade cancer.',
                 'high grade cancer.'
        ]
        if type != 'caption':
            label = [0,1,2]
    elif dataset_name == 'breakhis':
        label = ['benign - adenosis.',
                'benign - fibroadenoma.',
                'benign - phyllodes tumor.',
                'benign - tubular adenoma.',
                'malignant - ductal carcinoma.',
                'malignant - lobular carcinoma.',
                'malignant - mucinous carcinoma.',
                'malignant - carcinoma.'
        ]
        if type != 'caption':
            label = [0,1,2,3,4,5,6,7]
    elif dataset_name in ['prostate-1', 'prostate-2', 'prostate-3']:
        label = ['benign.',
                 'grade 3 cancer.',
                 'grade 4 cancer.',
                 'grade 5 cancer.'
        ]
        if type != 'caption':
            label = [0,1,2,3]
    elif dataset_name in ['gastric']:
        label = ['benign.',
                 'tubular well differentiated cancer.',
                 'tubular moderately differentiated cancer.',
                 'tubular poorly differentiated cancer.'
        ]
        if type != 'caption':
            label = [0,1,2,3]
    elif dataset_name in ['k19', 'k16']:
        label = [
            'adipole.',
            'background.',
            'debris.',
            'lymphocyte.',
            'normal.',
            'stroma.',
            'tumor.'
        ]
        if type != 'caption':
            label = [0,1,2,3,4,5,6]
    else:
        raise ValueError(f'Not support dataset {dataset_name}')
    result = []
    if type != 'caption':
        return label
    for l in label:
        hard_prompt = get_hard_prompt(dataset_name)
        result.append(combine_hard_prompt_with_label(hard_prompt, l))
    return result
