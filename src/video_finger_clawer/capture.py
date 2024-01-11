import csv
from batch_video_clawer_mitm import Batch_clawer_mitm
from get_tmp_finger import *


def write_finger(tmpfile, fingerfile):
    with open(tmpfile, 'r') as f:
        reader = csv.reader(f)
        txt = list(reader)

    len_txt = len(txt)
    for i in range(len_txt):
        s_videoflows = ''
        txt[i][7] = s_videoflows
        txt[i][14] = s_videoflows
        txt[i].remove(txt[i][4])
        txt[i].remove(txt[i][4])

    with open(fingerfile, 'w', encoding='utf-8') as f:
        for i in range(len_txt):
            for j in range(len(txt[i])):
                f.write(txt[i][j])
                if j < len(txt[i]) - 1:
                    f.write(',')
            f.write('\n')


if __name__ == '__main__':
    tmpfile = 'C:/Shrink/data/temp/tmp_finger.csv'
    fingerfile = 'C:/Shrink/data/fingerprint/finger.csv'

    conf_path = "C:/Shrink/bin/video_title_clawer.conf"
    clawer = Batch_clawer_mitm(conf_path)
    clawer.clawer_from_csv('test')

    finger = Finger(tmpfile)
    finger.from_path_file_get_finger("C:/Shrink/data/temp/mitm_file_path")
    finger.analysis_record()

    write_finger(tmpfile, fingerfile)
