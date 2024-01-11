import csv
import os
import pickle
import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from src.video_finger_clawer.get_finger import process_pcap, request_chunk


def getDictdata(host_ip, analysis_path, pcap_path, dictdata_path):
    with open(analysis_path, 'r') as f:
        reader = csv.reader(f)
        txt = list(reader)
    key = {}
    for i in txt:
        pcap = i[0].split('/')[-1]
        fingerprint = i[6].split('/')[1:]
        key[pcap] = [int(j) for j in fingerprint if int(j) > 600 * 1024]

    pcaplist = os.listdir(pcap_path)
    videodict = {}
    fingerdict = {}
    for pcap in pcaplist:
        pcap = pcap.split('.')[0]
        P, videoflows, P_all = process_pcap(pcap_path + pcap + '.pcap', host_ip)
        video = request_chunk(P_all, host_ip)
        if pcap in key.keys():
            finger = key[pcap]
            videodict[pcap] = video
            fingerdict[pcap] = finger

    with open(dictdata_path + 'videodict.data', 'wb') as f:
        pickle.dump(videodict, f)
    with open(dictdata_path + 'fingerdict.data', 'wb') as f:
        pickle.dump(fingerdict, f)


def getFitlist(dictdata_path, dt):
    with open(dictdata_path + 'videodict.data', 'rb') as f:
        videodict = pickle.load(f)
    with open(dictdata_path + 'fingerdict.data', 'rb') as f:
        fingerdict = pickle.load(f)

    videodict_align = {}
    fingerdict_align = {}
    pcaplist = list(videodict.keys())
    all_finger = []
    # fit_num = [2, 3, 4, 7, 8, 11, 14, 19, 21, 26, 27, 30, 31, 33, 34, 43, 53, 55, 56, 58, 60, 65, 68, 71, 72, 81, 83, 90, 91]

    for pcap in pcaplist:
        all_finger = all_finger + fingerdict[pcap]
        length = min(len(videodict[pcap]), len(fingerdict[pcap]))
        video = videodict[pcap]
        finger = fingerdict[pcap]
        # fig_output(video, finger, 'C:/Shrink/data/fig/all/' + pcap)
        video = videodict[pcap][:length]
        finger = fingerdict[pcap][:length]
        # if int(pcap.split('_')[0]) in fit_num:
        video_align, finger_align = align(video, finger, 3)
        videodict_align[pcap] = video_align
        fingerdict_align[pcap] = finger_align
        # fig_output(video_align, finger_align, 'C:/Shrink/data/fig/align/' + pcap)

    maxchunk = max(all_finger)
    minchunk = min(all_finger)
    videolist = list(videodict_align.values())
    fingerlist = list(fingerdict_align.values())
    fit_list = []
    for i in range(len(videolist)):
        for j in range(min(len(videolist[i]), len(fingerlist[i]))):
            fit_list.append([videolist[i][j], fingerlist[i][j]])
    print('fit list len: ' + str(len(fit_list)))
    tmp = []
    for i in fit_list:
        if abs(i[0] - i[1]) < dt:
            tmp.append(i)

    return tmp, maxchunk, minchunk


def fit(X, y):
    reg = LinearRegression().fit(X, y)
    y_pred = reg.predict(X)

    plt.scatter(X, y, color='black')
    plt.plot(X, y_pred, color='blue', linewidth=3)
    plt.xlabel('$chunk_{divide}$')
    plt.ylabel('$chunk_{real}$')
    plt.grid()
    plt.draw()
    plt.savefig('C:/Shrink/data/fig/result/Scatter plot of video chunk.png')

    return reg.coef_, reg.intercept_


def align(array1, array2, distance):
    S = []
    Larr = len(array1)
    for i in range(distance):
        tmp = [abs(array1[i:][j] - array2[:Larr - i][j]) for j in range(Larr - i)]
        s = sum(tmp)
        S.append(s / (Larr - i))
    ind = S.index(min(S))
    return array1[ind:], array2[:Larr - ind]


def fig_output(y1, y2, path):
    y = y1
    x = [i for i in range(len(y))]
    plt.plot(x, y, marker='o', color='black', label='$chunk_{divide}$')
    plt.legend()

    y = y2
    x = [i for i in range(len(y))]
    plt.plot(x, y, marker='v', color='red', label='$chunk_{real}$')
    plt.legend()

    plt.ylim(600 * 1024, 2097152)
    plt.xlabel('$chunk\_num$')
    plt.ylabel('$chunk\_size$')
    plt.grid()
    plt.draw()
    plt.savefig(path + '.png')
    plt.close()


if __name__ == '__main__':
    analysis_path = 'C:/Shrink/data/temp/tmp_finger.csv'
    pcap_path = 'C:/Shrink/data/record/test/pcap/'
    dictdata_path = 'C:/Shrink/data/temp/'
    host_ip = '192.168.32.38'
    getDictdata(host_ip, analysis_path, pcap_path, dictdata_path)

    fit_list, maxchunk, minchunk = getFitlist(dictdata_path, 100000)
    X = np.array([[i[0]] for i in fit_list])
    y = np.array([[i[1]] for i in fit_list])
    coef, intercept = fit(X, y)

    for i in range(len(fit_list)):
        fit_list[i].append(int(fit_list[i][0] * coef[0][0] + intercept[0]))
        fit_list[i].append(fit_list[i][1] - fit_list[i][2])
